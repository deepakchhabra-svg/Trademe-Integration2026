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
from pathlib import Path
from urllib.parse import urljoin
from typing import List, Dict, Optional

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

def scrape_product_detail(driver, url: str) -> Dict[str, any]:
    """
    Scrape individual product page for full details and images using Selenium.
    Returns dict with 'images' list and 'description' text.
    """
    try:
        driver.get(url)
        # Wait for meaningful content
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-name, h1"))
        )
        time.sleep(1) # Extra settling
        
        # Get Source
        html = driver.page_source
        tree = HTMLParser(html)
        
        # Extract images from JSON-LD (Most Reliable)
        json_ld_nodes = tree.css('script[type="application/ld+json"]')
        images = []
        
        for node in json_ld_nodes:
            try:
                data = json.loads(node.text(strip=True))
                # Check directly or in @graph
                candidates = []
                if isinstance(data, dict):
                    if data.get("@type") == "Product":
                        candidates.append(data)
                    elif "@graph" in data:
                        candidates.extend([item for item in data["@graph"] if item.get("@type") == "Product"])
                elif isinstance(data, list):
                    candidates.extend([item for item in data if item.get("@type") == "Product"])
                
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
            except:
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
            import re
            clean = re.sub(r'_\d+x\d+', '', clean)  # Remove _400x400, _800x800, etc.
            clean = re.sub(r'-thumb|-small|-medium', '', clean)  # Remove size suffixes
            
            # Ensure absolute URL
            if not clean.startswith("http"):
                clean = urljoin(BASE_URL, clean)
                
            # Deduplicate
            if clean not in clean_images:
                clean_images.append(clean)
                    
        # Extract Description & Technical Specs
        # Noel Leeming often lists specs in .product-features-benefits ul li
        specs = {}
        feature_nodes = tree.css(".product-features-benefits ul li")
        for li in feature_nodes:
            text = li.text(strip=True)
            if ":" in text:
                parts = text.split(":", 1)
                k = parts[0].strip()
                v = parts[1].strip()
                if k and v and len(k) < 40:
                    specs[k] = v
        
        # Product Details section (Model, Product ID)
        sku_node = tree.css_first(".product-manufacturer-sku .value")
        if sku_node:
            specs["Model"] = sku_node.text(strip=True)
        
        # Prioritize body content over thin metadata
        desc_node = tree.css_first(".product-description, #collapsible-details-1, .description-text, div.content-asset")
        description = desc_node.text(strip=True) if desc_node else ""
        
        return {
            "images": clean_images[:4],
            "description": description,
            "specs": specs
        }
    except Exception as e:
        print(f"  Error scraping detail {url}: {e}")
        return {"images": [], "description": ""}

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
            path = ChromeDriverManager().install()
            service = Service(path)
        except Exception:
            clear_webdriver_cache()
            try:
                path = ChromeDriverManager().install()
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

def scrape_category(headless: bool = True, max_pages: int = None, category_url: str = None, deep_scrape: bool = False):
    """
    Scrape a category using Selenium.
    deep_scrape: If True, visits every product URL to get more images (SLOW).
    """
    if not category_url:
        category_url = DEFAULT_CATEGORY_URL

    # Fast preflight: if the site is returning 403 from this environment, Selenium will just spin and time out.
    # This is NOT a mock — it's a real network check to fail fast with a clear diagnosis.
    try:
        r = httpx.get(BASE_URL, follow_redirects=True, timeout=10.0, headers={"User-Agent": "Mozilla/5.0"})
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
        
        for page_num in range(1, total_pages + 1):
            print(f"--- Page {page_num}/{total_pages} ---")
            
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
            
            # Deep Scrape for High Res Images using Selenium
            if deep_scrape:
                print(f"  Deep scraping {len(page_products)} items for images...")
                for p in page_products:
                    if p.get("url"):
                        # Use the SAME driver to visit detail page
                        details = scrape_product_detail(driver, p["url"])
                        
                        if details["images"]:
                            for i, img in enumerate(details["images"]):
                                p[f"photo{i+1}"] = img
                        if details["description"] and len(details["description"]) > len(p.get("title", "")):
                             p["description"] = details["description"]
                        
                        # Note: we are at detail page now.
                        # Next iteration of loop will navigate to p["url"], so it's fine.
                        # The OUTER loop (page_num) will navigate to next category page.
                        # This works.
            
            print(f"  Extracted {len(page_products)} products")
            all_products.extend(page_products)
            
    finally:
        driver.quit()
        
    return all_products

if __name__ == "__main__":
    # Test run
    scrape_category(max_pages=1, deep_scrape=False)
