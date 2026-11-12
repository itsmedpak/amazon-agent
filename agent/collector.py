import random
import re
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import (AMAZON_BASE_URL, DEBUG_DIR, DELAY_RANGE,
                    PAGES_PER_CATEGORY, REQUEST_TIMEOUT)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept-Language": "en-AE,en;q=0.9",
}

ASIN_RE = re.compile(r"/dp/([A-Z0-9]{10})")


class CollectionError(Exception):
    pass


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def parse_price(text):
    """'AED 1,299.00' -> 1299.0. Returns None if no number is present."""
    m = re.search(r"([\d,]+(?:\.\d+)?)", text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_rating(text):
    m = re.search(r"(\d(?:\.\d)?)\s*out of 5", text or "")
    return float(m.group(1)) if m else None


def parse_int(text):
    m = re.search(r"[\d,]+", text or "")
    return int(m.group(0).replace(",", "")) if m else None


def first_text(card, selectors):
    for sel in selectors:
        el = card.select_one(sel)
        if el:
            val = clean(el.get_text(" ", strip=True))
            if val:
                return val
    return ""


def parse_page(html):
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("#gridItemRoot") or soup.select("[data-asin]")
    out, seen = [], set()

    for card in cards:
        link = card.select_one('a[href*="/dp/"]')
        asin = (card.get("data-asin") or "").strip()
        if not asin and link:
            m = ASIN_RE.search(link.get("href", ""))
            asin = m.group(1) if m else ""
        if not asin:
            inner = card.select_one("[data-asin]")
            asin = (inner.get("data-asin") or "").strip() if inner else ""
        if not asin or asin in seen:
            continue

        # Title: longest text among product links, else image alt
        titles = [clean(a.get_text(" ", strip=True))
                  for a in card.select(f'a[href*="/dp/{asin}"]')]
        title = max((t for t in titles if t), key=len, default="")
        if not title:
            img = card.select_one("img[alt]")
            title = clean(img.get("alt", "")) if img else ""
        if not title:
            continue
        seen.add(asin)

        # Rank: dedicated badge first, text regex only as a flagged fallback
        rank, rank_source = None, None
        badge = card.select_one("span.zg-bdg-text")
        if badge:
            rank = parse_int(badge.get_text())
            rank_source = "badge" if rank else None
        if rank is None:
            m = re.search(r"^\s*#\s*(\d+)", clean(card.get_text(" ", strip=True)))
            if m:
                rank, rank_source = int(m.group(1)), "text"

        price_text = first_text(card, [".a-price .a-offscreen", ".p13n-sc-price", ".a-price"])
        rating_text = first_text(card, ["span.a-icon-alt"])

        reviews = None
        m = re.search(r"out of 5 stars\s*([\d,]+)", clean(card.get_text(" ", strip=True)), re.I)
        if m:
            reviews = parse_int(m.group(1))
        else:
            rv = first_text(card, ['a[href*="product-reviews"] span', 'a[href*="customerReviews"] span'])
            reviews = parse_int(rv)

        img = card.select_one("img")
        image_url = ""
        if img:
            image_url = img.get("src") or img.get("data-src") or ""

        out.append({
            "asin": asin,
            "title": title,
            "rank": rank,
            "rank_source": rank_source,
            "price_aed": parse_price(price_text),
            "price_text": price_text,
            "rating": parse_rating(rating_text),
            "reviews": reviews,
            "product_url": urljoin(AMAZON_BASE_URL, f"/dp/{asin}"),
            "image_url": image_url,
        })
    return out


def looks_blocked(html):
    soup = BeautifulSoup(html, "lxml")
    title = clean(soup.title.get_text()) if soup.title else ""
    return (
        "robot check" in title.lower()
        or soup.select_one('form[action*="validateCaptcha"]') is not None
        or "enter the characters you see below" in html.lower()
    )


def save_debug(category, page, html):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9]+", "_", category)
    path = DEBUG_DIR / f"{stamp}_{safe}_p{page}.html"
    path.write_text(html, encoding="utf-8")
    return path


def fetch_category(category, url):
    """Returns (products, pages_ok, warnings). Raises CollectionError if nothing usable."""
    products, seen = [], set()
    pages_ok, warnings = 0, []

    for page in range(1, PAGES_PER_CATEGORY + 1):
        page_url = url if page == 1 else f"{url}?pg={page}"
        if page > 1:
            time.sleep(random.uniform(*DELAY_RANGE))
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            warnings.append(f"p{page}: connection error: {e}")
            continue

        if resp.status_code != 200:
            path = save_debug(category, page, resp.text)
            warnings.append(f"p{page}: HTTP {resp.status_code} (saved {path.name})")
            continue
        if looks_blocked(resp.text):
            path = save_debug(category, page, resp.text)
            warnings.append(f"p{page}: CAPTCHA/robot check (saved {path.name})")
            break  # do not keep hitting a blocking site

        items = parse_page(resp.text)
        if not items:
            path = save_debug(category, page, resp.text)
            warnings.append(f"p{page}: 0 products parsed (saved {path.name})")
            continue

        pages_ok += 1
        for item in items:
            if item["asin"] not in seen:
                seen.add(item["asin"])
                products.append(item)

    if not products:
        raise CollectionError("; ".join(warnings) or "No products collected")
    return products, pages_ok, warnings