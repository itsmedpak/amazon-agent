import random
import re
import time

import requests
from bs4 import BeautifulSoup

from collector import HEADERS, clean, looks_blocked
from config import CATEGORIES, REQUEST_TIMEOUT, DELAY_RANGE

BEST = re.compile(r"/gp/bestsellers/[^?\"']*?/(\d{8,})")

for i, (label, url) in enumerate(CATEGORIES.items()):
    if i:
        time.sleep(random.uniform(*DELAY_RANGE))
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    print(f"\n=== config label: {label}  (HTTP {resp.status_code})")
    if resp.status_code != 200 or looks_blocked(resp.text):
        print("   blocked or failed, stopping"); break

    soup = BeautifulSoup(resp.text, "lxml")
    heading = next(
        (clean(h.get_text()) for h in soup.select("h1, h2, h3")
         if "best sellers in" in h.get_text().lower()), "NOT FOUND")
    print("   ACTUAL PAGE:", heading)

    # sidebar category links (name -> URL), no CSS class dependence
    seen = set()
    for a in soup.select('a[href*="/gp/bestsellers/"]'):
        name, href = clean(a.get_text()), a.get("href", "")
        m = BEST.search(href)
        if name and m and (name, m.group(1)) not in seen and len(seen) < 40:
            seen.add((name, m.group(1)))
    print("   links:", sorted(seen)[:40])