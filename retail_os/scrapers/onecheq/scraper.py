"""
OneCheq Scraper
Shopify-based e-commerce site scraper
Extracts: title, description, price, specs, images, SKU, condition
"""
import re
import json
import time
from typing import Optional, Dict, List
from selectolax.parser import HTMLParser
import httpx


def get_html_via_httpx(url: str) -> Optional[str]:
    """Fetch HTML using httpx with proper headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-NZ,en;q=0.9",
    }

    # Real retry/backoff for transient supplier instability (503/429/timeouts).
    # This is not a mock: it just makes the scraper resilient to real-world flakiness.
    for attempt in range(1, 5):
        try:
            with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as client:
                response = client.get(url)
                if response.status_code in (429, 503, 502, 504):
                    raise httpx.HTTPStatusError(f"{response.status_code} from supplier", request=response.request, response=response)
                response.raise_for_status()
                return response.text
        except Exception as e:
            wait = min(8.0, 0.7 * (2 ** (attempt - 1)))
            print(f"HTTP Error (attempt {attempt}/4): {e}")
            if attempt < 4:
                time.sleep(wait)
                continue
            return None


def norm_ws(text: str) -> str:
    """Normalize whitespace."""
    if not text:
        return ""
    return " ".join(text.split())


def extract_onecheq_id(url: str) -> str:
    """Extract product ID from OneCheq URL."""
    # URL format: https://onecheq.co.nz/products/product-slug
    match = re.search(r'/products/([^/?]+)', url)
    if match:
        return match.group(1)
    return "UNKNOWN"


def discover_products_from_collection(collection_url: str, max_pages: int = 5) -> List[str]:
    """
    Discover all product URLs from a collection page.
    OneCheq uses Shopify pagination: ?page=N
    """
    print(f"Discovering products from: {collection_url}")
    product_urls = set()
    
    for page_num in range(1, max_pages + 1):
        page_url = f"{collection_url}?page={page_num}"
        print(f"  Fetching page {page_num}...")
        
        html = get_html_via_httpx(page_url)
        if not html:
            print(f"  Failed to fetch page {page_num}")
            break
        
        doc = HTMLParser(html)
        
        # Find product links - Shopify typically uses product-card or similar classes
        product_links = doc.css("a[href*='/products/']")
        
        page_products = set()
        for link in product_links:
            href = link.attributes.get('href', '')
            if '/products/' in href:
                # Build full URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = f"https://onecheq.co.nz{href}"
                else:
                    full_url = f"https://onecheq.co.nz/{href}"
                
                # Remove query params and fragments
                full_url = full_url.split('?')[0].split('#')[0]
                page_products.add(full_url)
        
        if not page_products:
            print(f"  No products found on page {page_num}, stopping pagination")
            break
        
        print(f"  Found {len(page_products)} products on page {page_num}")
        product_urls.update(page_products)
    
    print(f"Total unique products discovered: {len(product_urls)}")
    return list(product_urls)


def scrape_onecheq_product(url: str) -> Optional[Dict]:
    """
    Scrape a single OneCheq product page.
    Returns dict with product data or None if scraping fails.
    """
    print(f"Scraping OneCheq product: {url}")
    
    # Extract product ID
    product_id = extract_onecheq_id(url)
    
    # Fetch HTML
    html = get_html_via_httpx(url)
    if not html:
        print(f"ERROR: Failed to fetch HTML from {url}")
        return None
    
    if not HTMLParser:
        print("ERROR: Selectolax not available")
        return None
    
    # Parse with Selectolax
    doc = HTMLParser(html)
    
    # Extract title (robust fallbacks)
    title = ""
    title_node = doc.css_first(
        "h1.product__title, h1[class*='product-title'], .product-info__title h1, h1"
    )
    if title_node:
        title = norm_ws(title_node.text())

    if not title:
        og = doc.css_first('meta[property="og:title"], meta[name="og:title"]')
        if og:
            title = norm_ws(og.attributes.get("content", ""))

    # JSON-LD Product fallback (Shopify commonly includes this)
    if not title:
        try:
            for node in doc.css('script[type="application/ld+json"]'):
                raw = (node.text() or "").strip()
                if not raw:
                    continue
                data = json.loads(raw)
                candidates = []
                if isinstance(data, dict):
                    if data.get("@type") == "Product":
                        candidates.append(data)
                    elif "@graph" in data and isinstance(data["@graph"], list):
                        candidates.extend([x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "Product"])
                elif isinstance(data, list):
                    candidates.extend([x for x in data if isinstance(x, dict) and x.get("@type") == "Product"])
                for p in candidates:
                    name = p.get("name") or ""
                    if name:
                        title = norm_ws(str(name))
                        raise StopIteration()
        except StopIteration:
            pass
        except Exception:
            pass
    
    # Extract SKU
    sku = product_id
    sku_node = doc.css_first(".product__sku, [class*='sku'], .variant-sku")
    if sku_node:
        sku_text = norm_ws(sku_node.text())
        # Extract just the SKU value (e.g., "SKU: LOT731" -> "LOT731")
        sku_match = re.search(r'SKU:?\s*([A-Z0-9]+)', sku_text, re.IGNORECASE)
        if sku_match:
            sku = sku_match.group(1)
    
    # Extract price
    price = 0.0
    price_node = doc.css_first(
        ".price__regular .price-item--regular, .price-item--regular, .product__price, [class*='price-now'], [class*='price'] .price-item"
    )
    if price_node:
        price_text = norm_ws(price_node.text())
        price_match = re.search(r'\$?([\\d,]+\\.?\\d*)', price_text)
        if price_match:
            price = float(price_match.group(1).replace(',', ''))

    # JSON-LD price fallback
    if not price:
        try:
            for node in doc.css('script[type="application/ld+json"]'):
                raw = (node.text() or "").strip()
                if not raw:
                    continue
                data = json.loads(raw)
                candidates = []
                if isinstance(data, dict):
                    if data.get("@type") == "Product":
                        candidates.append(data)
                    elif "@graph" in data and isinstance(data["@graph"], list):
                        candidates.extend([x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "Product"])
                elif isinstance(data, list):
                    candidates.extend([x for x in data if isinstance(x, dict) and x.get("@type") == "Product"])
                for p in candidates:
                    offers = p.get("offers")
                    if isinstance(offers, dict):
                        pval = offers.get("price")
                        if pval is not None:
                            price = float(str(pval).replace(",", "").strip())
                            raise StopIteration()
        except StopIteration:
            pass
        except Exception:
            pass
    
    # Extract condition
    condition = "Used"  # Default for OneCheq
    condition_node = doc.css_first(".product__condition, [class*='condition']")
    if condition_node:
        condition_text = norm_ws(condition_node.text())
        if 'new' in condition_text.lower():
            condition = "New"
        elif 'refurbished' in condition_text.lower():
            condition = "Refurbished"
    
    # Extract brand from title or meta
    brand = ""
    # Try to extract brand from title (first word often)
    if title:
        # Common patterns: "Apple iPhone", "Samsung Galaxy", etc.
        brand_match = re.match(r'^([A-Za-z]+)', title)
        if brand_match:
            brand = brand_match.group(1)
    
    # Extract description
    description = ""
    desc_node = doc.css_first(".product__description, .product-description, [class*='product-desc']")
    if desc_node:
        # Get text content
        description = norm_ws(desc_node.text())

    if not description:
        ogd = doc.css_first('meta[property="og:description"], meta[name="og:description"]')
        if ogd:
            description = norm_ws(ogd.attributes.get("content", ""))

    if not description:
        # JSON-LD description fallback
        try:
            for node in doc.css('script[type="application/ld+json"]'):
                raw = (node.text() or "").strip()
                if not raw:
                    continue
                data = json.loads(raw)
                candidates = []
                if isinstance(data, dict):
                    if data.get("@type") == "Product":
                        candidates.append(data)
                    elif "@graph" in data and isinstance(data["@graph"], list):
                        candidates.extend([x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "Product"])
                elif isinstance(data, list):
                    candidates.extend([x for x in data if isinstance(x, dict) and x.get("@type") == "Product"])
                for p in candidates:
                    desc = p.get("description") or ""
                    if desc:
                        description = norm_ws(str(desc))
                        raise StopIteration()
        except StopIteration:
            pass
        except Exception:
            pass

    # Hard last resort: use slug-derived title so adapter doesn't drop the row
    if not title:
        title = product_id.replace("-", " ").strip() or "UNKNOWN"
    
    # Extract specs/features from description or dedicated section
    specs = {}
    
    # Look for specification tables
    spec_rows = doc.css(".product-specs tr, .specifications tr, table tr")
    for row in spec_rows:
        cells = row.css("td, th")
        if len(cells) >= 2:
            key = norm_ws(cells[0].text()).rstrip(':')
            value = norm_ws(cells[1].text())
            if key and value:
                specs[key] = value
    
    # If no table specs, try to extract from description
    if not specs and description:
        # Look for key-value patterns in description
        lines = description.split('\\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = norm_ws(parts[0])
                    value = norm_ws(parts[1])
                    if key and value and len(key) < 50:  # Avoid long sentences
                        specs[key] = value
    
    # Add condition to specs
    specs['Condition'] = condition
    
    # Extract images
    images = []
    
    # Shopify typically uses a media gallery
    img_nodes = doc.css(".product__media img, .product-gallery img, [class*='product-image'] img")
    for img in img_nodes:
        src = img.attributes.get('src') or img.attributes.get('data-src')
        if src:
            # Clean up Shopify CDN URLs
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/') and not src.startswith('http'):
                src = 'https://onecheq.co.nz' + src
            
            # Remove size parameters to get full image
            src = re.sub(r'_\\d+x\\d+\\.', '.', src)
            
            if 'http' in src and src not in images:
                images.append(src)
    
    # Limit to 4 images
    images = images[:4]
    
    # Extract availability/stock status
    stock_status = "Available"
    stock_node = doc.css_first(".product__inventory, .product-form__inventory, [class*='stock']")
    if stock_node:
        stock_text = norm_ws(stock_node.text()).lower()
        if 'out of stock' in stock_text or 'sold out' in stock_text:
            stock_status = "Sold"
        elif 'low stock' in stock_text:
            stock_status = "Low Stock"
    
    return {
        "source_id": f"OC-{sku}",
        "source_url": url,
        "title": title,
        "description": description,
        "brand": brand,
        "condition": condition,
        "buy_now_price": price,
        "stock_level": 1 if stock_status == "Available" else 0,
        "photo1": images[0] if len(images) > 0 else None,
        "photo2": images[1] if len(images) > 1 else None,
        "photo3": images[2] if len(images) > 2 else None,
        "photo4": images[3] if len(images) > 3 else None,
        "source_status": stock_status,
        "specs": specs,
        "sku": sku
    }


def scrape_onecheq(limit_pages: int = 1, collection: str = "all") -> List[Dict]:
    """
    Main entry point for OneCheq scraper.
    
    Args:
        limit_pages: Number of pages to scrape per collection (0 = unlimited)
        collection: Collection slug to scrape (default: "all" for all products)
    
    Returns:
        List of product dictionaries
    """
    print(f"=== OneCheq Scraper Started ===")
    print(f"Collection: {collection}")
    print(f"Pages per collection: {'UNLIMITED' if limit_pages <= 0 else limit_pages}")
    
    # Build collection URL
    if collection == "all":
        collection_url = "https://onecheq.co.nz/collections/all"
    else:
        collection_url = f"https://onecheq.co.nz/collections/{collection}"
    
    # Discover products
    max_pages = 999 if limit_pages <= 0 else limit_pages
    product_urls = discover_products_from_collection(collection_url, max_pages)
    
    if not product_urls:
        print("No products found!")
        return []
    
    # Scrape each product
    products = []
    for i, url in enumerate(product_urls, 1):
        print(f"\\nProduct {i}/{len(product_urls)}")
        try:
            product_data = scrape_onecheq_product(url)
            if product_data:
                products.append(product_data)
                print(f"  [OK] Success: {product_data['title'][:50]}...")
            else:
                print(f"  [FAIL] Failed to scrape")
        except Exception as e:
            print(f"  [ERROR] Error: {e}")
    
    print(f"\\n=== Scraping Complete ===")
    print(f"Successfully scraped: {len(products)}/{len(product_urls)} products")
    
    return products


if __name__ == "__main__":
    # Test scraper
    products = scrape_onecheq(limit_pages=1, collection="smartphones-and-mobilephones")
    print(f"\\nScraped {len(products)} products")
    if products:
        print("\\nSample product:")
        print(json.dumps(products[0], indent=2))
