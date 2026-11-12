import requests
from collections import Counter
from bs4 import BeautifulSoup

from collector import HEADERS, parse_page
from config import CATEGORIES, DEBUG_DIR, REQUEST_TIMEOUT

url = CATEGORIES["Furniture"]

for page in (1, 2):
    page_url = url if page == 1 else f"{url}?pg={page}"
    html = requests.get(page_url, headers=HEADERS, timeout=REQUEST_TIMEOUT).text
    (DEBUG_DIR / f"diag_p{page}.html").write_text(html, encoding="utf-8")

    items = parse_page(html)
    ranks = sorted(i["rank"] for i in items if i["rank"])
    print(f"\n--- page {page}: {len(items)} items, ranks {ranks[:1]}..{ranks[-1:]}")
    print("ranks:", ranks)
    print("rank_source:", Counter(i["rank_source"] for i in items))

    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("#gridItemRoot")
    print("gridItemRoot cards:", len(cards), "| 'AED' occurrences in page:", html.count("AED"))
    if cards:
        c = cards[0]
        print("\nFIRST CARD HTML (first 3500 chars):\n")
        print(str(c)[:3500])