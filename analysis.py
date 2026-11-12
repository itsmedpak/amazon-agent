from datetime import datetime, timedelta, timezone

import pandas as pd

from database import connect

DUBAI = timezone(timedelta(hours=4))  # UAE has no DST


def to_dubai(ts):
    return datetime.fromisoformat(ts).astimezone(DUBAI)


def fmt_ts(ts):
    return to_dubai(ts).strftime("%d %b %Y, %H:%M") + " GST"


def all_runs(category, limit=200):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM runs WHERE category = ? ORDER BY started_at DESC LIMIT ?",
            (category, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def daily_runs(category):
    """Latest COMPLETED run per Dubai calendar day, newest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM runs WHERE category = ? AND status = 'COMPLETED' "
            "ORDER BY started_at DESC",
            (category,),
        ).fetchall()
    seen, out = set(), []
    for r in rows:
        day = to_dubai(r["started_at"]).date()
        if day in seen:
            continue
        seen.add(day)
        out.append(dict(r))
    return out


def get_snapshot(run_id):
    with connect() as conn:
        return pd.read_sql_query(
            """SELECT s.asin, p.title, p.image_url, p.product_url,
                      s.rank, s.price_aed, s.rating, s.reviews
               FROM snapshots s JOIN products p ON p.asin = s.asin
               WHERE s.run_id = ? ORDER BY s.rank""",
            conn, params=(run_id,),
        )


def add_movement(cur, prev):
    """Positive rank_change = moved up. Only valid where the ASIN has a rank
    in BOTH snapshots; anything else is labelled, never guessed."""
    df = cur.copy()
    if prev is None or prev.empty:
        df["prev_rank"] = None
        df["prev_price"] = None
        df["rank_change"] = None
        df["price_change_pct"] = None
        df["status"] = "Baseline"
        return df

    p = prev[["asin", "rank", "price_aed"]].rename(
        columns={"rank": "prev_rank", "price_aed": "prev_price"})
    df = df.merge(p, on="asin", how="left", indicator=True)
    df["rank_change"] = df["prev_rank"] - df["rank"]
    pct = (df["price_aed"] - df["prev_price"]) / df["prev_price"] * 100
    df["price_change_pct"] = pct.replace([float("inf"), float("-inf")], pd.NA)

    def label(row):
        if row["_merge"] == "left_only":
            return "New to observed range"
        if pd.isna(row["rank_change"]):
            return "Rank unavailable"
        if row["rank_change"] > 0:
            return "Improved"
        if row["rank_change"] < 0:
            return "Declined"
        return "Unchanged"

    df["status"] = df.apply(label, axis=1)
    return df.drop(columns=["_merge"])


def load_view(category):
    runs = daily_runs(category)
    if not runs:
        return None
    cur_run = runs[0]
    prev_run = runs[1] if len(runs) > 1 else None
    cur = get_snapshot(cur_run["id"])
    prev = get_snapshot(prev_run["id"]) if prev_run else None
    return {
        "run": cur_run,
        "prev_run": prev_run,
        "df": add_movement(cur, prev),
        "snapshots": len(runs),
    }


def rank_gaps(ranks):
    """Rank ranges missing between 1 and the highest observed rank."""
    seen = {int(x) for x in ranks if pd.notna(x)}
    if not seen:
        return []
    ranges = []
    for n in range(1, max(seen) + 1):
        if n in seen:
            continue
        if ranges and n == ranges[-1][1] + 1:
            ranges[-1][1] = n
        else:
            ranges.append([n, n])
    return [str(a) if a == b else f"{a}–{b}" for a, b in ranges]


def summarize(df, has_prev):
    priced = df["price_aed"].dropna()
    rated = df["rating"].dropna()
    ranks = df["rank"].dropna()
    s = {
        "products": len(df),
        "min_rank": int(ranks.min()) if len(ranks) else None,
        "max_rank": int(ranks.max()) if len(ranks) else None,
        "gaps": rank_gaps(df["rank"]),
        "priced": len(priced),
        "median_price": priced.median() if len(priced) else None,
        "mean_price": priced.mean() if len(priced) else None,
        "min_price": priced.min() if len(priced) else None,
        "max_price": priced.max() if len(priced) else None,
        "rated": len(rated),
        "avg_rating": rated.mean() if len(rated) else None,
        "has_prev": has_prev,
    }
    if has_prev:
        vc = df["status"].value_counts()
        s["improved"] = int(vc.get("Improved", 0))
        s["declined"] = int(vc.get("Declined", 0))
        s["unchanged"] = int(vc.get("Unchanged", 0))
        s["new"] = int(vc.get("New to observed range", 0))
    return s


def product_history(asin, category):
    ids = [r["id"] for r in daily_runs(category)]
    if not ids:
        return pd.DataFrame()
    marks = ",".join("?" * len(ids))
    with connect() as conn:
        df = pd.read_sql_query(
            f"""SELECT r.started_at, s.rank, s.price_aed, s.rating, s.reviews
                FROM snapshots s JOIN runs r ON r.id = s.run_id
                WHERE s.asin = ? AND s.run_id IN ({marks})
                ORDER BY r.started_at""",
            conn, params=[asin, *ids],
        )
    df["date"] = df["started_at"].map(lambda t: to_dubai(t).date())
    return df