"""
Cash Converters Scraper - Production Ready
Uses Selectolax with proven extraction logic from extract_clean_cc.py
"""
import subprocess
import re
from typing import Optional, Dict

try:
    from selectolax.parser import HTMLParser
except ImportError:
    HTMLParser = None

# ========== HELPERS FROM extract_clean_cc.py ==========

def norm_ws(s: str) -> str:
    """Normalize whitespace."""
    return re.sub(r"\s+", " ", (s or "").strip())

def norm(text: str) -> str:
    """Normalize text."""
    if not text:
        return ""
    return " ".join(str(text).split())

def parse_money(s: Optional[str]) -> Optional[float]:
    """Parse money string to float."""
    if not s:
        return None
    _MONEY_RE = re.compile(r"[-+]?\s*[$NZD]*\s*([0-9][0-9,]*)(?:\.(\d{1,2}))?", re.I)
    m = _MONEY_RE.search(str(s))
    if not m:
        return None
    whole = m.group(1).replace(",", "")
    frac = (m.group(2) or "0")
    try:
        return float(f"{int(whole)}.{frac}")
    except Exception:
        return None

def find_label_value(tree: HTMLParser, label_candidates):
    """Look for 'Label: Value' lines in content tags."""
    for label in label_candidates:
        pat = re.compile(rf"\b{re.escape(label)}\b\s*:?[\s ]*([^\n\r|<>]{{1,80}})", re.IGNORECASE)
        for n in tree.css("p,li,dd,dt,span,div"):
            txt = norm(n.text())
            if not txt or len(txt) > 200:
                continue
            m = pat.search(txt)
            if m:
                return norm(m.group(1))
    return ""

def parse_images(tree: HTMLParser, max_images: int = 8):
    """Extract image URLs from Azure blob storage."""
    urls = []
    for img in tree.css("img"):
        src = (img.attributes.get("src") or "").strip()
        data_src = (img.attributes.get("data-src") or "").strip()
        u = data_src or src
        if not u:
            continue
        if "auctionworxstoragelive1.blob.core.windows.net" not in u:
            continue
        lu = u.lower()
        if any(bad in lu for bad in ["thumb", "sprite", "favicon", "logo"]):
            continue
        if not lu.endswith("_fullsize.jpg"):
            continue
        urls.append(u)
    
    # De-duplicate
    seen = set()
    clean = []
    for u in urls:
        if u in seen:
            continue
        clean.append(u)
        seen.add(u)
        if len(clean) >= max_images:
            break
    return clean

def extract_title(doc: HTMLParser) -> str:
    """Extract title from various sources."""
    # Try h1 first
    node = doc.css_first("h1, .listing-title, #MainContentContainer h1")
    if node:
        return norm_ws(node.text())
    
    # Try og:title meta tag
    meta = doc.css_first('meta[property="og:title"], meta[name="og:title"]')
    if meta:
        c = meta.attributes.get("content") or ""
        if c:
            return norm_ws(c)
    
    # Fallback to title tag
    headt = doc.css_first("title")
    if headt:
        title = norm_ws(headt.text())
        # Remove "Cash Converters - " prefix
        title = re.sub(r"^Cash Converters\s*-\s*", "", title, flags=re.I)
        return title
    
    return ""

def extract_prices(doc: HTMLParser):
    """Extract current and buy now prices."""
    current = None
    buy_now = None
    
    # Try widget selectors
    parts = [n.text() for n in doc.css(".awe-rt-BuyNowPrice span.NumberPart, .BuyNowPrice span.NumberPart")]
    if parts:
        buy_now = parse_money("".join(parts))
    
    cur_parts = [n.text() for n in doc.css(".awe-rt-Price span.NumberPart, .CurrentPrice span.NumberPart, .current-bid .NumberPart")]
    if cur_parts:
        current = parse_money("".join(cur_parts))
    
    # Fallback: label-based search
    if buy_now is None:
        bn_txt = find_label_value(doc, ["Buy Now Price", "Buy Now"])
        buy_now = parse_money(bn_txt)
    
    if current is None:
        cur_txt = find_label_value(doc, ["Current Price", "Starting Bid", "Start Price"])
        current = parse_money(cur_txt)
    
    return current, buy_now

# ========== CURL FETCHER ==========

def get_html_via_curl(url: str) -> str:
    """Fetch HTML using curl with exact User-Agent from extract_clean_cc.py."""
    try:
        result = subprocess.run(
            [
                'curl',
                '-s',
                '-L',
                '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
                url
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        print(f"CURL Error: {e}")
        return None

# ========== MAIN SCRAPER ==========

def scrape_cash_converters(query: str = "laptop", limit: int = 5) -> list:
    """DEPRECATED: Use scrape_single_item() with real URLs."""
    print("ERROR: scrape_cash_converters() is deprecated. Use scrape_single_item() with real URLs.")
    return []

def scrape_single_item(url: str) -> Optional[Dict]:
    """
    Scrapes a SINGLE item URL using Selectolax.
    Returns dict with data OR None if scraping fails.
    NO MOCKS. NO PLACEHOLDERS.
    """
    print(f"Scraper: Single Fetch '{url}'...")
    
    # Extract ID from URL
    item_id = "UNKNOWN"
    match = re.search(r'/Details/(\d+)', url)  # Made slug optional
    if match:
        item_id = match.group(1)
    
    # Fetch HTML
    html = get_html_via_curl(url)
    
    if not html:
        print(f"ERROR: Failed to fetch HTML from {url}")
        return None
    
    if not HTMLParser:
        print("ERROR: Selectolax not available")
        return None
    
    # Parse with Selectolax
    doc = HTMLParser(html)
    
    # Extract title
    title = extract_title(doc)
    
    # Extract prices
    current_price, buy_now_price = extract_prices(doc)
    
    # Extract images
    images = parse_images(doc, max_images=4)
    primary_image = images[0] if images else None
    
    # Extract description
    description = ""
    desc_node = doc.css_first("#description, .description, .listing-description, .tab-pane .description, [id*='description'], [class*='description']")
    if desc_node:
        description = norm_ws(desc_node.text())
    
    # Extract condition
    condition = find_label_value(doc, ["Condition"])
    
    # Extract model number (from description or specs)
    model = ""
    if description:
        model_match = re.search(r'Model:\s*([A-Z0-9\-\s]+?)(?=\n|Condition|Brand|Type|$)', description, re.IGNORECASE)
        if model_match:
            model = model_match.group(1).strip()
    
    # Build specs dict
    specs = {}
    if model:
        specs["Model"] = model
    if condition:
        specs["Condition"] = condition
    
    # Use buy_now_price if available, otherwise current_price
    price = buy_now_price if buy_now_price else current_price
    
    return {
        "source_id": f"CC-{item_id}",
        "source_url": url,
        "title": title,
        "description": description,
        "buy_now_price": price or 0.0,
        "stock_level": 1,
        "photo1": primary_image,  # Real Azure blob URL or None
        "source_status": "Available",
        "specs": specs
    }
