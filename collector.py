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
PRICE_RE = re.compile(r"AED\s*([\d,]+(?:\.\d+)?)", re.I)
RATING_RE = re.compile(
    r"(\d(?:\.\d)?)\s*out of 5 stars?(?:,\s*([\d,]+)\s*ratings?)?", re.I
)

class CollectionError(Exception):
    pass

def get_heading(html):
    soup = BeautifulSoup(html, "lxml")
    for h in soup.select("h1, h2, h3"):
        text = clean(h.get_text())
        if text.lower().startswith("best sellers in"):
            return text
    return ""

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
        card_text = clean(card.get_text(" ", strip=True))

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

        titles = [clean(a.get_text(" ", strip=True))
                  for a in card.select(f'a[href*="/dp/{asin}"]')]
        title = max((t for t in titles if t), key=len, default="")
        if not title:
            img = card.select_one("img[alt]")
            title = clean(img.get("alt", "")) if img else ""
        if not title:
            continue
        seen.add(asin)

        # Rank: badge first, flagged text fallback
        rank, rank_source = None, None
        badge = card.select_one("span.zg-bdg-text")
        if badge:
            rank = parse_int(badge.get_text())
            rank_source = "badge" if rank else None
        if rank is None:
            m = re.search(r"^\s*#\s*(\d+)", card_text)
            if m:
                rank, rank_source = int(m.group(1)), "text"

        # Price: None when the card shows no AED amount. Never guessed.
        price_text = first_text(card, [
            "span.a-color-price",
            '[class*="p13n-sc-price"]',
            ".a-price .a-offscreen",
        ])
        m = PRICE_RE.search(price_text)
        price_aed = float(m.group(1).replace(",", "")) if m else None
        if price_aed is None:
            price_text = ""

        # Rating and ratings count from the aria-label
        rating, reviews = None, None
        label_el = card.select_one('[aria-label*="out of 5"]')
        m = RATING_RE.search(label_el.get("aria-label", "")) if label_el else None
        if m:
            rating = float(m.group(1))
            reviews = parse_int(m.group(2)) if m.group(2) else None

        img = card.select_one("img")
        image_url = (img.get("src") or img.get("data-src") or "") if img else ""

        out.append({
            "asin": asin,
            "title": title,
            "rank": rank,
            "rank_source": rank_source,
            "price_aed": price_aed,
            "price_text": price_text,
            "rating": rating,
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


def fetch_category(category, url, expected_heading):
    """Returns (products, pages_ok, warnings, heading). Raises CollectionError on
    a failed fetch OR if the page is not the category we asked for."""
    products, seen = [], set()
    pages_ok, warnings, heading = 0, [], ""

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
            break

        if not heading:
            heading = get_heading(resp.text)
            if heading != expected_heading:
                path = save_debug(category, page, resp.text)
                raise CollectionError(
                    f"category mismatch: expected '{expected_heading}', "
                    f"got '{heading or 'NO HEADING'}' (saved {path.name})"
                )

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
    return products, pages_ok, warnings, heading
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