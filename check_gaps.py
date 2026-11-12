# check_gaps.py
from collector import parse_page
from config import DEBUG_DIR

for page in (1, 2):
    html = (DEBUG_DIR / f"diag_p{page}.html").read_text(encoding="utf-8")
    for p in parse_page(html):
        if p["price_aed"] is None or p["rating"] is None:
            print(p["rank"], p["asin"], "price" if p["price_aed"] is None else "", "rating" if p["rating"] is None else "", p["title"][:50])