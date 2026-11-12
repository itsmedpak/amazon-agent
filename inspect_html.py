
from pathlib import Path
from bs4 import BeautifulSoup

html = Path("data/amazon_debug.html").read_text(encoding="utf-8")
soup = BeautifulSoup(html, "lxml")

print("HTML length:", len(html))
print("data-asin elements:", len(soup.select("[data-asin]")))
print("Product links:", len(soup.select('a[href*="/dp/"]')))
print("Card metrics:", len(soup.select("[data-card-metrics-id]")))

print("\n--- ASIN ELEMENTS ---")
for el in soup.select("[data-asin]")[:8]:
    print("ASIN:", el.get("data-asin"))
    print("TEXT:", el.get_text(" ", strip=True)[:250])

print("\n--- PRODUCT LINKS ---")
for el in soup.select('a[href*="/dp/"]')[:8]:
    print("URL:", el.get("href"))
    print("TEXT:", el.get_text(" ", strip=True)[:200])

print("\n--- CARD METRICS ---")
for el in soup.select("[data-card-metrics-id]")[:12]:
    print("ID:", el.get("data-card-metrics-id"))
    print("TEXT:", el.get_text(" ", strip=True)[:250])
