import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    asin TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    image_url TEXT,
    product_url TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    source_url TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,            -- RUNNING / COMPLETED / PARTIAL / FAILED
    pages_ok INTEGER DEFAULT 0,
    pages_requested INTEGER DEFAULT 0,
    product_count INTEGER DEFAULT 0,
    message TEXT,
    page_heading TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id),
    asin TEXT NOT NULL REFERENCES products(asin),
    rank INTEGER,                    -- NULL if not found; never guessed
    rank_source TEXT,                -- 'badge' / 'text' / NULL
    price_aed REAL,
    price_text TEXT,
    rating REAL,
    reviews INTEGER,
    UNIQUE (run_id, asin)
);

CREATE INDEX IF NOT EXISTS idx_snap_asin ON snapshots(asin);
CREATE INDEX IF NOT EXISTS idx_snap_run ON snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_cat ON runs(category, started_at);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def start_run(category, source_url, pages_requested):
    run_id = str(uuid.uuid4())
    with connect() as conn:
        conn.execute(
            "INSERT INTO runs (id, category, source_url, started_at, status, pages_requested) "
            "VALUES (?, ?, ?, ?, 'RUNNING', ?)",
            (run_id, category, source_url, now(), pages_requested),
        )
    return run_id


def finish_run(run_id, status, pages_ok, products, message="", heading=""):
    ts = now()
    with connect() as conn:
        for p in products:
            conn.execute(
                """INSERT INTO products (asin, title, image_url, product_url, first_seen, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(asin) DO UPDATE SET
                     title = excluded.title,
                     image_url = COALESCE(NULLIF(excluded.image_url, ''), products.image_url),
                     product_url = COALESCE(NULLIF(excluded.product_url, ''), products.product_url),
                     last_seen = excluded.last_seen""",
                (p["asin"], p["title"], p["image_url"], p["product_url"], ts, ts),
            )
            conn.execute(
                """INSERT OR IGNORE INTO snapshots
                   (run_id, asin, rank, rank_source, price_aed, price_text, rating, reviews)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, p["asin"], p["rank"], p["rank_source"],
                 p["price_aed"], p["price_text"], p["rating"], p["reviews"]),
            )
        conn.execute(
            "UPDATE runs SET finished_at=?, status=?, pages_ok=?, product_count=?, "
            "message=?, page_heading=? WHERE id=?",
            (ts, status, pages_ok, len(products), message, heading, run_id),
        )

def fail_run(run_id, message):
    finish_run(run_id, "FAILED", 0, [], message)
    


def run_stats():
    with connect() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT r.category, r.started_at, r.status, r.pages_ok, r.product_count,
                   SUM(s.rank IS NULL)      AS null_rank,
                   SUM(s.price_aed IS NULL) AS null_price,
                   SUM(s.rating IS NULL)    AS null_rating,
                   SUM(s.reviews IS NULL)   AS null_reviews,
                   MIN(s.rank) AS min_rank, MAX(s.rank) AS max_rank
            FROM runs r LEFT JOIN snapshots s ON s.run_id = r.id
            GROUP BY r.id ORDER BY r.started_at DESC LIMIT 30
        """)]