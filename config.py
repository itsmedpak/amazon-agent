from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEBUG_DIR = DATA_DIR / "debug"
DB_PATH = DATA_DIR / "market.db"

AMAZON_BASE_URL = "https://www.amazon.ae"
REQUEST_TIMEOUT = 25
PAGES_PER_CATEGORY = 2          # Amazon serves 50 per page via ?pg=N
DELAY_RANGE = (3.0, 6.0)        # seconds between requests

# "All Best Sellers" intentionally removed: it's a multi-category landing page.
# Category IDs carried over from the old config; verify each opens correctly.
CATEGORIES = {
    "Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148100031",
    "Bathroom Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148116031",
    "Bedroom Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148117031",
    "Dining Room Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148119031",
    "Game & Recreation Room Furniture": "https://www.amazon.ae/gp/bestsellers/home/15300123031",
    "Patio Furniture & Accessories": "https://www.amazon.ae/gp/bestsellers/home/12421795031",
    "Entryway Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148121031",
    "Home Bar Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148122031",
    "Home Office Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148124031",
    "Kids' Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148118031",
    "Kitchen Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148125031",
    "Living Room Furniture": "https://www.amazon.ae/gp/bestsellers/home/12148126031",
}

# The page heading Amazon must return for each label. A mismatch aborts the run.
EXPECTED_HEADINGS = {name: f"Best Sellers in {name}" for name in CATEGORIES}
EXPECTED_HEADINGS["Patio Furniture & Accessories"] = "Best Sellers in Patio Furniture & Accessories"
EXPECTED_HEADINGS["Entryway Furniture"] = "Best Sellers in Entryway Furniture"

DATA_DIR.mkdir(exist_ok=True)
DEBUG_DIR.mkdir(exist_ok=True)