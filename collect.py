import argparse
import random
import time

from collector import CollectionError, fetch_category
from database import fail_run, finish_run, init_db, run_stats, start_run
from config import CATEGORIES, DELAY_RANGE, EXPECTED_HEADINGS, PAGES_PER_CATEGORY


def collect(category):
    url = CATEGORIES[category]
    run_id = start_run(category, url, PAGES_PER_CATEGORY)
    try:
        products, pages_ok, warnings, heading = fetch_category(
            category, url, EXPECTED_HEADINGS[category])
    except CollectionError as e:
        fail_run(run_id, str(e))
        print(f"[FAILED]  {category}: {e}")
        return
    status = "COMPLETED" if pages_ok == PAGES_PER_CATEGORY else "PARTIAL"
    finish_run(run_id, status, pages_ok, products, "; ".join(warnings), heading)
    print(f"[{status}] {category}: {len(products)} products, {pages_ok}/{PAGES_PER_CATEGORY} pages")
    for w in warnings:
        print(f"    warning: {w}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", help="Exact category name")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--stats", action="store_true", help="Show data-quality stats for recent runs")
    args = ap.parse_args()
    init_db()

    if args.stats:
        for r in run_stats():
            print(r)
        return

    names = list(CATEGORIES) if args.all else [args.category] if args.category else []
    if not names:
        ap.error("use --category NAME, --all or --stats")
    for i, name in enumerate(names):
        if name not in CATEGORIES:
            ap.error(f"unknown category: {name}")
        if i:
            time.sleep(random.uniform(*DELAY_RANGE))
        collect(name)


if __name__ == "__main__":
    main()