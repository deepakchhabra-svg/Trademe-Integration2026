"""
Noel Leeming Scraper
Extracts product data including high-res images using Selenium.
"""
import time
import json
import re
import sys
import os
import shutil
import threading
import queue
from pathlib import Path
from urllib.parse import urljoin
from typing import List, Dict, Optional
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party imports
from selectolax.parser import HTMLParser
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import httpx

# Try to use webdriver-manager
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

BASE_URL = "https://www.noelleeming.co.nz"
DEFAULT_CATEGORY_URL = f"{BASE_URL}/search?cgid=computersofficetech-computers"

def _save_media_bytes(filename: str, data: bytes) -> str:
    media_dir = Path("data") / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    p = media_dir / filename
    p.write_bytes(data)
    return str(p)


def _fetch_bytes_via_selenium(driver, url: str) -> bytes | None:
    """
    Fetch binary bytes using the browser session (cookies/anti-bot compatible).
    Returns bytes or None.
    """
    try:
        # Must run on the same origin (Noel Leeming) for credentials to work.
        js = """
        const url = arguments[0];
        const cb = arguments[1];
        fetch(url, { credentials: 'include' })
          .then(r => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.blob();
          })
          .then(b => {
            const reader = new FileReader();
            reader.onloadend = () => cb(reader.result);
            reader.readAsDataURL(b);
          })
          .catch(e => cb('ERROR:' + (e && e.message ? e.message : String(e))));
        """
        out = driver.execute_async_script(js, url)
        if not out or not isinstance(out, str):
            return None
        if out.startswith("ERROR:"):
            return None
        if not out.startswith("data:"):
            return None
        # data:<mime>;base64,<...>
        if ";base64," not in out:
            return None
        b64 = out.split(";base64,", 1)[1]
        return base64.b64decode(b64)
    except Exception:
        return None

def scrape_product_detail(driver, url: str) -> Dict[str, any]:
    """
    Scrape individual product page for full details and images using Selenium.
    Returns dict with 'images' list, 'description' text, and 'specs' dict.
    
    Specs includes sellable fields:
    - product_id: NL numeric ID
    - sku: NL Product ID (e.g., N228404)
    - model: Manufacturer model number
    - features: List of feature strings
    - warranty_months: Integer or None
    - stock_status: IN_STOCK, LOW_STOCK, OUT_OF_STOCK, UNKNOWN
    - offer_end_date: ISO date string or None
    - condition_raw: Raw condition text
    - condition_normalized: NEW, REFURBISHED, USED
    """
    try:
        print(f"      [DETAIL] Starting scrape for: {url[:80]}")
        
        print(f"      [DETAIL] Calling driver.get()...")
        try:
            driver.get(url)
            print(f"      [DETAIL] Page loaded from driver.get()")
        except Exception as get_error:
            print(f"      [DETAIL] ERROR in driver.get(): {type(get_error).__name__}: {get_error}")
            return {"images": [], "description": "", "specs": {}}
        
        print(f"      [DETAIL] Waiting for page load...")
        # Wait for meaningful content
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-name, h1"))
            )
            print(f"      [DETAIL] Page loaded successfully")
        except Exception as wait_err:
            print(f"      [DETAIL] Wait timeout or element not found: {wait_err}")
            # Continue anyway - page might have loaded
        
        time.sleep(1) # Extra settling
        
        print(f"      [DETAIL] Getting page source...")
        # Get Source
        html = driver.page_source
        
        print(f"      [DETAIL] Parsing HTML (length: {len(html)})...")
        tree = HTMLParser(html)
        
        print(f"      [DETAIL] Extracting images from JSON-LD...")
        # Extract images from JSON-LD (Most Reliable)
        json_ld_nodes = tree.css('script[type="application/ld+json"]')
        images = []
        
        for node in json_ld_nodes:
            try:
                print(f"      [DETAIL] Processing JSON-LD node...")
                data = json.loads(node.text(strip=True))
                print(f"      [DETAIL] JSON parsed, checking for Product type...")
                # Check directly or in @graph
                candidates = []
                if isinstance(data, dict):
                    if data.get("@type") == "Product":
                        candidates.append(data)
                    elif "@graph" in data:
                        candidates.extend([item for item in data["@graph"] if item.get("@type") == "Product"])
                elif isinstance(data, list):
                    candidates.extend([item for item in data if item.get("@type") == "Product"])
                
                print(f"      [DETAIL] Found {len(candidates)} product candidates...")
                for product in candidates:
                    img_data = product.get("image")
                    if img_data:
                        if isinstance(img_data, list):
                            for img in img_data:
                                if isinstance(img, str):
                                    images.append(img)
                                elif isinstance(img, dict) and "url" in img: # schema.org ImageObject
                                    images.append(img.get("url"))
                        elif isinstance(img_data, str):
                            images.append(img_data)
                        elif isinstance(img_data, dict) and "url" in img_data:
                             images.append(img_data.get("url"))
            except Exception as json_err:
                print(f"      [DETAIL] Error parsing JSON-LD node: {type(json_err).__name__}: {json_err}")
                continue
        
        # Fallback to CSS selectors if JSON-LD failed
        if not images:
            img_nodes = tree.css("""
                img.primary-image, 
                div.primary-images img, 
                div.s7-static-image img,
                li.hero-image-slider-item img,
                img.slider-image
            """)
            for img in img_nodes:
                src = img.attributes.get("src") or img.attributes.get("data-src") or ""
                if src and "noelleeming" in src and not "icon" in src:
                    images.append(src)

        # Clean URLs (remove query params AND size parameters for full res)
        clean_images = []
        for img in images:
            # Remove query parameters
            clean = img.split("?")[0]
            
            # Remove common thumbnail size patterns (e.g., _400x400, -thumb, _small)
            # Remove common thumbnail size patterns (e.g., _400x400, -thumb, _small)
            clean = re.sub(r'_\d+x\d+', '', clean)  # Remove _400x400, _800x800, etc.
            clean = re.sub(r'-thumb|-small|-medium', '', clean)  # Remove size suffixes
            
            # Ensure absolute URL
            if not clean.startswith("http"):
                clean = urljoin(BASE_URL, clean)
                
            # Deduplicate
            if clean not in clean_images:
                clean_images.append(clean)
                    
        # ========================================
        # SELLABLE SPECS EXTRACTION
        # ========================================
        specs = {}
        
        # --- Product ID / SKU ---
        # Try to extract NL Product ID from URL (e.g., /N233790.html -> N233790)
        sku_match = re.search(r'/([A-Z]?\d{5,10})\.html', url)
        if sku_match:
            specs["sku"] = sku_match.group(1)
            # product_id is numeric part
            numeric_match = re.search(r'(\d+)', sku_match.group(1))
            if numeric_match:
                specs["product_id"] = numeric_match.group(1)
        
        # Also try from manufacturer SKU on page
        sku_node = tree.css_first(".product-manufacturer-sku .value, .product-id .value")
        if sku_node:
            sku_text = sku_node.text(strip=True)
            specs["model"] = sku_text
            # If we didn't get product_id from URL, try here
            if "product_id" not in specs:
                numeric = re.search(r'(\d+)', sku_text)
                if numeric:
                    specs["product_id"] = numeric.group(1)
        
        # --- Features List ---
        features = []
        # 2026 structure: Look for "Features & Benefits" section or similar
        # Try multiple selectors in order of specificity
        feature_sections = [
            # Direct features list
            ".product-features-benefits ul li",
            ".features-benefits ul li",
            # Features section after heading
            "h3:contains('Features') + ul li",
            "h2:contains('Features') + ul li",
            # Generic product features
            ".product-features li",
            ".features-list li",
        ]
        
        for selector in feature_sections:
            if not features:  # Only try next selector if we haven't found features yet
                feature_nodes = tree.css(selector)
                for li in feature_nodes:
                    text = li.text(strip=True)
                    if text and len(text) > 3 and len(text) < 500:
                        # Skip if it looks like a navigation item or generic text
                        if not any(skip in text.lower() for skip in ['click here', 'learn more', 'view details']):
                            features.append(text)
        
        # Fallback: Look for any <ul> after "Features" heading in page text
        if not features:
            # Find Features & Benefits section in raw HTML
            page_html = html if 'html' in locals() else str(tree.html)
            if 'Features' in page_html or 'features' in page_html:
                # Try to extract from structured content
                for node in tree.css('ul li'):
                    text = node.text(strip=True)
                    if text and 10 < len(text) < 500:
                        # Heuristic: features usually have specific patterns
                        if any(indicator in text.lower() for indicator in ['hour', 'year', 'month', 'warranty', 'certified', 'compatible', 'support', 'included', 'feature', 'design', 'performance']):
                            if text not in features:
                                features.append(text)
                if len(features) > 20:  # Too many, probably grabbed wrong content
                    features = features[:10]
        
        specs["features"] = features
        
        # --- Warranty Months ---
        warranty_months = None
        # Match patterns like "12 month warranty", "2 year warranty", "2 year manufacturer warranty"
        warranty_pattern = re.compile(r'(\d+)\s*(?:month|year)s?(?:\s+\w+)?\s*(?:warranty|guarantee)', re.IGNORECASE)
        # Search in features first
        for f in features:
            match = warranty_pattern.search(f)
            if match:
                val = int(match.group(1))
                # If "year" is in the match, convert to months
                if "year" in f.lower():
                    val = val * 12
                warranty_months = val
                break
        # Fallback: search entire page text
        if warranty_months is None:
            page_text = tree.body.text() if tree.body else ""
            match = warranty_pattern.search(page_text)
            if match:
                val = int(match.group(1))
                if "year" in page_text[max(0, match.start()-20):match.end()+20].lower():
                    val = val * 12
                warranty_months = val
        specs["warranty_months"] = warranty_months
        
        # --- Stock Status ---
        stock_status = "IN_STOCK"  # Default to IN_STOCK (Noel Leeming typically shows only available items)
        
        # Look for explicit out-of-stock indicators
        stock_indicators = tree.css(".availability-status, .stock-status, .product-availability, .availability-msg")
        for stock_node in stock_indicators:
            stock_text = stock_node.text(strip=True).lower()
            if "out of stock" in stock_text or "unavailable" in stock_text or "sold out" in stock_text:
                stock_status = "OUT_OF_STOCK"
                break
            elif "low stock" in stock_text or "limited" in stock_text or "few left" in stock_text or "hurry" in stock_text:
                stock_status = "LOW_STOCK"
                break
            elif "in stock" in stock_text or "available" in stock_text:
                stock_status = "IN_STOCK"
                break
        
        # Check for "X+ people bought this" indicator (suggests in stock)
        if stock_status == "IN_STOCK":
            popularity_text = tree.body.text() if tree.body else ""
            if "people bought this" in popularity_text.lower():
                stock_status = "IN_STOCK"
        
        # Fallback: check if Add to Cart button exists and is enabled
        if stock_status == "IN_STOCK":  # Only check button if we haven't determined status yet
            add_btn = tree.css_first("button.add-to-cart, button.add-to-basket, .add-to-cart-button, button[data-pid]")
            if add_btn:
                btn_disabled = add_btn.attributes.get("disabled")
                btn_class = add_btn.attributes.get("class", "")
                if btn_disabled or "disabled" in btn_class:
                    stock_status = "OUT_OF_STOCK"
        
        specs["stock_status"] = stock_status
        
        # --- Offer End Date ---
        offer_end_date = None
        promo_node = tree.css_first(".promo-end-date, .offer-ends, .sale-ends, .promotion-end")
        if promo_node:
            promo_text = promo_node.text(strip=True)
            # Try to parse date (common formats: "Ends 15 Jan", "Offer ends 2024-01-15")
            date_match = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})', promo_text)
            if date_match:
                d, m, y = date_match.groups()
                y = int(y) if len(y) == 4 else 2000 + int(y)
                offer_end_date = f"{y:04d}-{int(m):02d}-{int(d):02d}"
        specs["offer_end_date"] = offer_end_date
        
        # --- Condition ---
        condition_raw = None
        condition_normalized = "NEW"  # Default for NL (they sell new items)
        condition_node = tree.css_first(".product-condition, .condition-badge, .refurbished-badge")
        if condition_node:
            condition_raw = condition_node.text(strip=True)
            condition_lower = condition_raw.lower()
            if "refurb" in condition_lower or "renewed" in condition_lower:
                condition_normalized = "REFURBISHED"
            elif "used" in condition_lower or "pre-owned" in condition_lower:
                condition_normalized = "USED"
        # Also check title/page for refurb markers
        page_text_lower = (tree.body.text() if tree.body else "").lower()
        if "refurbished" in page_text_lower or "renewed" in page_text_lower:
            condition_normalized = "REFURBISHED"
            if not condition_raw:
                condition_raw = "Refurbished"
        specs["condition_raw"] = condition_raw
        specs["condition_normalized"] = condition_normalized
        
        # --- Legacy Spec Extraction (key:value pairs from tables) ---
        for li in tree.css(".product-specifications li, .tech-specs li, .specifications li"):
            text = li.text(strip=True)
            if ":" in text:
                parts = text.split(":", 1)
                k = parts[0].strip()
                v = parts[1].strip()
                if k and v and len(k) < 50:
                    specs[k] = v
                    
        # Also look for tables
        for row in tree.css(".product-specifications tr, .spec-table tr, table.specs tr"):
            cells = row.css("td, th")
            if len(cells) >= 2:
                k = cells[0].text(strip=True).rstrip(":")
                v = cells[1].text(strip=True)
                if k and v and len(k) < 50:
                    specs[k] = v
        
        # Prioritize body content over thin metadata
        desc_node = tree.css_first(".product-description, #collapsible-details-1, .description-text, div.content-asset")
        description = desc_node.text(strip=True) if desc_node else ""
        
        return {
            "images": clean_images[:4],
            "description": description,
            "specs": specs
        }
    except Exception as e:
        print(f"  [DETAIL] ERROR scraping {url}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {"images": [], "description": "", "specs": {}}

# --- Selenium Setup (Copied from original) ---

def clear_webdriver_cache():
    """Clear webdriver-manager cache to fix corrupted downloads."""
    try:
        cache_path = Path.home() / ".wdm"
        if cache_path.exists():
            shutil.rmtree(cache_path)
    except Exception:
        pass

def setup_driver(headless: bool = True, timeout: int = 30):
    """Setup Chrome WebDriver."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Optional proxy support (required in some environments where Noel Leeming blocks datacenter IPs).
    proxy = os.getenv("NOEL_LEEMING_PROXY")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
    
    # Driver initialization logic 
    service = None
    if WEBDRIVER_MANAGER_AVAILABLE:
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            path = ChromeDriverManager(driver_version="143.0.7499.169").install()
            service = Service(path)
        except Exception:
            clear_webdriver_cache()
            try:
                path = ChromeDriverManager(driver_version="143.0.7499.169").install()
                service = Service(path)
            except Exception:
                pass
                
    if service:
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
        
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(10)
    return driver

class WebDriverPool:
    """Pool of WebDriver instances for concurrent scraping."""
    
    def __init__(self, max_drivers: int = 2, headless: bool = True):  # Reduced from 4 to 2
        self.max_drivers = max_drivers
        self.headless = headless
        self.pool = queue.Queue(maxsize=max_drivers)
        self.active_drivers = []
        self.lock = threading.Lock()
        
        # PRE-CREATE all drivers to avoid race conditions
        print(f"  Initializing WebDriver pool with {max_drivers} drivers...")
        for i in range(max_drivers):
            try:
                driver = setup_driver(headless=self.headless)
                self.active_drivers.append(driver)
                self.pool.put(driver)
                print(f"  Driver {i+1}/{max_drivers} initialized")
            except Exception as e:
                print(f"  Failed to initialize driver {i+1}: {e}")
                # Continue with fewer drivers if some fail
                break
    
    def get(self):
        """Get a driver from the pool (blocks until one is available)."""
        # This will block until a driver is available
        driver = self.pool.get()
        return driver
    
    def release(self, driver):
        """Return a driver to the pool."""
        if driver:
            self.pool.put(driver)
    
    def shutdown(self):
        """Quit all drivers in the pool."""
        with self.lock:
            for driver in self.active_drivers:
                try:
                    driver.quit()
                except Exception:
                    pass
            self.active_drivers.clear()
            # Clear the queue
            while not self.pool.empty():
                try:
                    self.pool.get_nowait()
                except queue.Empty:
                    break

def wait_for_products(driver, timeout: int = 30):
    """Wait for product tiles to load."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-tile"))
        )
        return True
    except TimeoutException:
        print(f"  Timeout waiting for products after {timeout}s")
        return False

def get_pagination_info(driver):
    """Get total number of pages from pagination."""
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "gep-search-pagination"))
        )
        pagination_elem = driver.find_element(By.CSS_SELECTOR, "gep-search-pagination")
        pages_attr = pagination_elem.get_attribute("pages")
        
        if pages_attr:
            import html
            pages_json = html.unescape(pages_attr)
            pages_data = json.loads(pages_json)
            max_page = max(page["page"] for page in pages_data)
            return max_page
    except Exception:
        pass
    return 1

def extract_products_from_html(html: str, page_num: int = 1, overall_rank_start: int = 1) -> list[dict]:
    """Extract product data using selectolax."""
    tree = HTMLParser(html)
    products = []
    tiles = tree.css("div.product-tile")
    
    for idx, tile in enumerate(tiles):
        try:
            gtm_data_str = tile.attributes.get("data-gtm-product")
            if not gtm_data_str:
                continue
            
            gtm_data = json.loads(gtm_data_str)
            
            # Basic info from Tile
            product_id = gtm_data.get("id", "")
            title = gtm_data.get("name", "")
            price = gtm_data.get("price", "")
            brand = gtm_data.get("brand", "")
            category = gtm_data.get("category", "")
            ean = gtm_data.get("productEAN", "")
            
            # URL
            link_elem = tile.css_first("a.link")
            url = ""
            if link_elem:
                url = link_elem.attributes.get("href", "")
                if url and not url.startswith("http"):
                    url = urljoin(BASE_URL, url)
            
            # Fallback Image (Thumbnail)
            image_url = ""
            for img in tile.css("img"):
                img_class = img.attributes.get("class", "")
                src = img.attributes.get("src", "")
                if "tile-image" in img_class and "/images/" in src:
                    image_url = src
                    if not image_url.startswith("http"):
                        image_url = urljoin(BASE_URL, image_url)
                    break

            if product_id and title:
                products.append({
                    "source_listing_id": product_id,
                    "title": title,
                    "price": price,
                    "brand": brand,
                    "category": category,
                    "ean": ean,
                    "url": url,
                    "image_url": image_url, # Helper for scrape logic
                    "photo1": image_url,    # Default photo1
                    
                    # Ranking
                    "noel_leeming_rank": overall_rank_start + idx,
                    "page_number": page_num,
                    "page_position": idx + 1
                })
        except Exception:
            continue
            
    return products

def scrape_category(
    headless: bool = True,
    max_pages: int = None,
    category_url: str = None,
    deep_scrape: bool = False,
    cmd_id: str | None = None,
    progress_hook=None,
    should_abort=None,
):
    """
    Scrape a category using Selenium.
    deep_scrape: If True, visits every product URL to get more images (SLOW).
    """
    if not category_url:
        category_url = DEFAULT_CATEGORY_URL

    # Fast preflight: if the site is returning 403 from this environment, Selenium will just spin and time out.
    # This is NOT a mock — it's a real network check to fail fast with a clear diagnosis.
    try:
        proxy = os.getenv("NOEL_LEEMING_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        proxies = None
        if proxy:
            # httpx expects a dict mapping scheme->proxy URL
            proxies = {"http://": proxy, "https://": proxy}
        r = httpx.get(
            BASE_URL,
            follow_redirects=True,
            timeout=10.0,
            headers={"User-Agent": "Mozilla/5.0"},
            proxies=proxies,
        )
        if r.status_code == 403:
            raise RuntimeError(
                "Noel Leeming blocked this environment (HTTP 403). "
                "Run from an allowed network or set NOEL_LEEMING_PROXY to a working proxy."
            )
    except RuntimeError:
        raise
    except Exception:
        # If preflight fails for transient reasons, continue to Selenium attempt.
        pass
    
    print(f"Starting Selenium WebDriver (headless={headless})...")
    driver = setup_driver(headless=headless)
    
    all_products = []
    seen_ids = set()
    
    # Track overall rank across pages
    # NOTE: This variable must persist across pages
    overall_rank_persistent = 1
    
    try:
        print(f"\nNavigating to: {category_url}")
        driver.get(category_url)
        
        if not wait_for_products(driver):
            return []
        
        time.sleep(2)
        total_pages = get_pagination_info(driver) or 5
        print(f"Detected {total_pages} pages")
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        import logging
        log = logging.getLogger(__name__)

        for page_num in range(1, total_pages + 1):
            try:
                if should_abort and bool(should_abort()):
                    return all_products
            except Exception:
                pass
            print(f"--- Page {page_num}/{total_pages} ---")
            try:
                if cmd_id:
                    log.info(f"NOEL_LEEMING_PAGE cmd_id={cmd_id} page={page_num} total_pages={total_pages}")
            except Exception:
                pass
            try:
                if progress_hook and cmd_id:
                    progress_hook(
                        {
                            "phase": "scrape",
                            "supplier": "NOEL_LEEMING",
                            "done": int(page_num - 1),
                            "total": int(total_pages),
                            "message": f"Scraping NL pages: {page_num}/{total_pages}",
                        }
                    )
            except Exception:
                pass
            
            # Navigate if needed
            if page_num > 1:
                page_url = f"{category_url}&start={(page_num-1)*32}"
                driver.get(page_url)
                if not wait_for_products(driver, timeout=15):
                    continue
                time.sleep(2)
            
            # Scroll
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                tiles = driver.find_elements(By.CSS_SELECTOR, "div.product-tile")
                if len(tiles) >= 32:
                    break
            
            driver.execute_script("window.scrollTo(0, 0);")
            
            # Extract Listing Data first
            html = driver.page_source
            page_products = extract_products_from_html(html, page_num, overall_rank_persistent)

            # Best-effort: download the tile image via the browser session (avoids 403 on demandware images).
            # This keeps NL usable in the operator flow without needing deep_scrape.
            try:
                dl = (os.getenv("RETAILOS_NL_BROWSER_IMAGE_DOWNLOAD", "true") or "true").lower() in ("1", "true", "yes", "on")
                per_page = int(os.getenv("RETAILOS_NL_BROWSER_IMAGE_DOWNLOAD_PER_PAGE", "32") or "32")
                per_page = max(0, min(64, per_page))
                if dl and per_page:
                    for i, p in enumerate(page_products[:per_page], 0):
                        try:
                            if should_abort and bool(should_abort()):
                                return all_products
                        except Exception:
                            pass
                        img = (p or {}).get("photo1") or ""
                        pid = str((p or {}).get("source_listing_id") or "").strip()
                        if not pid or not img or not isinstance(img, str):
                            continue
                        if not img.startswith("http"):
                            continue
                        if "noelleeming.co.nz/dw/image/" not in img:
                            continue
                        b = _fetch_bytes_via_selenium(driver, img)
                        if not b:
                            continue
                        try:
                            local = _save_media_bytes(f"NL-{pid}.jpg", b)
                            p["photo1"] = local
                        except Exception:
                            pass
            except Exception:
                pass
            
            # Count how many NEW products we found to update rank counter
            new_this_page = 0
            for p in page_products:
                if p['source_listing_id'] not in seen_ids:
                    seen_ids.add(p['source_listing_id'])
                    new_this_page += 1
            
            # Update rank for next page (add NEW items found, assuming sequential)
            # Actually extract_products uses overall_rank_persistent as start.
            # We need to increment it by the number of items on THIS page (regardless of whether we've seen them before? 
            # No, if we've seen them, rank is dubious. But usually pagination is distinct.
            # We'll increment by len(page_products) to be safe for next page.
            overall_rank_persistent += len(page_products)
            
            # Deep Scrape for High Res Images using Selenium (CONCURRENT)
            if deep_scrape:
                print(f"  Deep scraping {len(page_products)} items for images...")
                
                # Create a worker pool if not already created
                if not hasattr(scrape_category, '_driver_pool'):
                    # Reduced default from 4 to 2 to prevent Selenium timeouts
                    pool_size = int(os.getenv("RETAILOS_NL_CONCURRENT_WORKERS", "2") or "2")
                    pool_size = max(1, min(4, pool_size))  # Limit to max 4
                    scrape_category._driver_pool = WebDriverPool(max_drivers=pool_size, headless=headless)
                
                driver_pool = scrape_category._driver_pool
                
                def scrape_product_worker(product_dict):
                    """Worker function to scrape a single product detail."""
                    pool_driver = None
                    try:
                        print(f"    Starting: {product_dict.get('title', 'unknown')[:50]}")
                        
                        # Check abort flag
                        if should_abort and bool(should_abort()):
                            return product_dict
                        
                        if not product_dict.get("url"):
                            return product_dict
                        
                        # Get a driver from the pool
                        pool_driver = driver_pool.get()
                        
                        # Scrape the detail page with timeout handling
                        try:
                            details = scrape_product_detail(pool_driver, product_dict["url"])
                        except Exception as detail_error:
                            # Log timeout or other errors but don't crash
                            error_msg = str(detail_error)
                            if "timeout" in error_msg.lower() or "renderer" in error_msg.lower():
                                print(f"  Timeout scraping {product_dict.get('url', 'unknown')}, skipping...")
                            else:
                                print(f"  Error scraping detail: {error_msg}")
                            return product_dict
                        
                        if details["images"]:
                            # Prefer browser-session downloads for NL images (requests often 403).
                            limit_imgs = int(os.getenv("RETAILOS_NL_IMAGE_LIMIT_PER_PRODUCT", "2") or "2")
                            limit_imgs = max(0, min(4, limit_imgs))
                            dl = (os.getenv("RETAILOS_NL_BROWSER_IMAGE_DOWNLOAD", "true") or "true").lower() in ("1", "true", "yes", "on")

                            for i, img in enumerate(details["images"][: max(1, limit_imgs)], 0):
                                if not img:
                                    continue
                                # Default to remote URL
                                product_dict[f"photo{i+1}"] = img
                                if not dl:
                                    continue
                                b = _fetch_bytes_via_selenium(pool_driver, img)
                                if b:
                                    pid = str(product_dict.get("source_listing_id") or "").strip() or "NL"
                                    fn = f"NL-{pid}.jpg" if i == 0 else f"NL-{pid}_{i+1}.jpg"
                                    try:
                                        local = _save_media_bytes(fn, b)
                                        product_dict[f"photo{i+1}"] = local
                                    except Exception:
                                        # leave remote URL
                                        pass
                        if details["description"] and len(details["description"]) > len(product_dict.get("title", "")):
                             product_dict["description"] = details["description"]
                        if details.get("specs"):
                             product_dict["specs"] = details["specs"]
                        
                        return product_dict
                    except Exception as e:
                        print(f"  Error in worker for {product_dict.get('url', 'unknown')}: {e}")
                        return product_dict
                    finally:
                        # Always release the driver back to the pool
                        if pool_driver:
                            driver_pool.release(pool_driver)
                
                # Process products concurrently
                # Reduced to 1 to isolate crash issue
                max_workers = int(os.getenv("RETAILOS_NL_CONCURRENT_WORKERS", "1") or "1")
                max_workers = max(1, min(4, max_workers))  # Limit to max 4
                
                print(f"  Processing {len(page_products)} products with {max_workers} workers...")
                
                try:
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit all tasks
                        futures = {executor.submit(scrape_product_worker, p): p for p in page_products}
                        
                        # Collect results
                        completed = 0
                        for future in as_completed(futures):
                            try:
                                result = future.result(timeout=120)  # 2 minute timeout per product
                                if result:
                                    # Find the original product in page_products and update it
                                    # This assumes product objects are mutable and can be updated in place
                                    # Or, if they are replaced, we need to find the index.
                                    # For simplicity, assuming the worker modifies the dict in place,
                                    # or we can re-assign if the worker returns a new dict.
                                    # The original code didn't explicitly re-assign, implying in-place modification.
                                    # If `result` is a new dict, we need to find the original `p` and replace it.
                                    # Given the worker returns `product_dict`, it's likely the same object.
                                    # The instruction's `products[products.index(futures[future])] = result`
                                    # implies replacement. Let's adapt to `page_products`.
                                    original_product = futures[future]
                                    if original_product in page_products:
                                        idx = page_products.index(original_product)
                                        page_products[idx] = result # Replace with potentially updated result
                                completed += 1
                                if completed % 10 == 0:
                                    print(f"    Progress: {completed}/{len(page_products)} products scraped")
                            except TimeoutError:
                                print(f"    TIMEOUT: Product scraping took too long, skipping...")
                            except Exception as e:
                                print(f"    ERROR in future: {type(e).__name__}: {str(e)}")
                                import traceback
                                traceback.print_exc()
                    
                    print(f"  Completed scraping {len(page_products)} products")
                    
                except Exception as e:
                    print(f"  CRITICAL ERROR in ThreadPoolExecutor: {type(e).__name__}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # Don't crash - continue with whatever we have
                
                finally:
                    # Always cleanup the driver pool
                    try:
                        driver_pool.shutdown()
                        print(f"  WebDriver pool shut down successfully")
                    except Exception as e:
                        print(f"  Error shutting down pool: {e}")
            
            print(f"  Extracted {len(page_products)} products")
            all_products.extend(page_products)
            
    finally:
        driver.quit()
        # Shutdown the driver pool if it was created
        if hasattr(scrape_category, '_driver_pool'):
            scrape_category._driver_pool.shutdown()
            delattr(scrape_category, '_driver_pool')

        
    return all_products

if __name__ == "__main__":
    # Test run
    scrape_category(max_pages=1, deep_scrape=False)
