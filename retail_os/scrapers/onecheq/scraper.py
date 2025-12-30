"""
OneCheq Scraper
Shopify-based e-commerce site scraper
Extracts: title, description, price, specs, images, SKU, condition
"""
import re
import json
import time
import os
import html as _html
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from selectolax.parser import HTMLParser
import httpx


def _fmt_secs(secs: float) -> str:
    if secs < 0:
        secs = 0.0
    if secs < 60:
        return f"{secs:.0f}s"
    m = int(secs // 60)
    s = int(secs % 60)
    return f"{m}m{s:02d}s"


def get_html_via_httpx(url: str, client: Optional[httpx.Client] = None) -> Optional[str]:
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
            if client is None:
                with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as c:
                    response = c.get(url)
            else:
                response = client.get(url, headers=headers)

            if response.status_code in (429, 503, 502, 504):
                raise httpx.HTTPStatusError(
                    f"{response.status_code} from supplier", request=response.request, response=response
                )
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


_SKU_SAFE_RE = re.compile(r"[^A-Za-z0-9]+")


def normalize_sku(raw: str) -> str:
    """
    Normalize supplier SKU into a stable identifier.
    We enforce alnum-only + uppercase to avoid drift and DB duplicates.
    """
    s = (raw or "").strip()
    if not s:
        return ""
    s = re.sub(r"^(sku|item|product)\s*[:#-]?\s*", "", s, flags=re.I).strip()
    s = _SKU_SAFE_RE.sub("", s).upper()
    return s[:32]


def _iter_jsonld_products(doc: HTMLParser) -> List[Dict]:
    """
    Best-effort extractor for JSON-LD Product objects.
    Shopify commonly embeds Product JSON-LD.
    """
    out: List[Dict] = []
    for node in doc.css('script[type="application/ld+json"]'):
        raw = (node.text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        candidates: list[dict] = []
        if isinstance(data, dict):
            if data.get("@type") == "Product":
                candidates.append(data)
            elif "@graph" in data and isinstance(data["@graph"], list):
                candidates.extend([x for x in data["@graph"] if isinstance(x, dict) and x.get("@type") == "Product"])
        elif isinstance(data, list):
            candidates.extend([x for x in data if isinstance(x, dict) and x.get("@type") == "Product"])

        out.extend(candidates)
    return out


def _extract_brand_from_jsonld(products: List[Dict]) -> str:
    for p in products:
        b = p.get("brand")
        if isinstance(b, dict):
            name = b.get("name")
            if name:
                return norm_ws(str(name))
        if isinstance(b, str) and b.strip():
            return norm_ws(b)
        m = p.get("manufacturer")
        if isinstance(m, dict):
            name = m.get("name")
            if name:
                return norm_ws(str(name))
    return ""


def _extract_sku_from_jsonld(products: List[Dict]) -> str:
    for p in products:
        for k in ("sku", "mpn"):
            v = p.get(k)
            if v:
                sku = normalize_sku(str(v))
                if sku:
                    return sku
        offers = p.get("offers")
        if isinstance(offers, dict):
            v = offers.get("sku") or offers.get("mpn")
            if v:
                sku = normalize_sku(str(v))
                if sku:
                    return sku
    return ""


def extract_onecheq_id(url: str) -> str:
    """Extract product ID from OneCheq URL."""
    # URL format: https://onecheq.co.nz/products/product-slug
    match = re.search(r'/products/([^/?]+)', url)
    if match:
        return match.group(1)
    return "UNKNOWN"


def discover_products_from_collection(
    collection_url: str,
    max_pages: int = 5,
    client: Optional[httpx.Client] = None,
    max_products: Optional[int] = None,
) -> List[str]:
    """
    Discover all product URLs from a collection page.
    OneCheq uses Shopify pagination: ?page=N
    """
    print(f"Discovering products from: {collection_url}")
    product_urls: set[str] = set()
    consecutive_no_new = 0
    
    for page_num in range(1, max_pages + 1):
        page_url = f"{collection_url}?page={page_num}"
        print(f"  Fetching page {page_num}...")
        
        html = get_html_via_httpx(page_url, client=client)
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

        # If this page contributes no NEW product URLs, we're likely past the end.
        new_on_page = page_products - product_urls
        if not new_on_page:
            consecutive_no_new += 1
            # Shopify pages can include persistent /products/ links (header/footer/featured).
            # Once we see no-new pages twice in a row, stop to avoid infinite pagination.
            if consecutive_no_new >= 2:
                print(f"  No new products found for {consecutive_no_new} pages; stopping pagination")
                break
        else:
            consecutive_no_new = 0
        
        print(f"  Found {len(page_products)} products on page {page_num}")
        product_urls.update(new_on_page)
        if max_products and len(product_urls) >= int(max_products):
            print(f"  Reached max_products={max_products}; stopping discovery")
            break
    
    print(f"Total unique products discovered: {len(product_urls)}")
    return list(product_urls)


def _strip_html(s: str) -> str:
    if not s:
        return ""
    text = re.sub(r"<[^>]+>", " ", s)
    text = _html.unescape(text)
    return norm_ws(text)


def _shopify_products_json_url(collection: str, page: int, limit: int = 250) -> str:
    if collection == "all":
        return f"https://onecheq.co.nz/collections/all/products.json?limit={int(limit)}&page={int(page)}"
    return f"https://onecheq.co.nz/collections/{collection}/products.json?limit={int(limit)}&page={int(page)}"


def _iter_onecheq_products_via_shopify_json(collection: str, max_pages: int, client: httpx.Client, cmd_id: str | None = None):
    """
    Fast, authoritative Shopify JSON scrape.
    Iterates products from /collections/<handle>/products.json (250/page).
    """
    limit = int(os.getenv("RETAILOS_ONECHEQ_JSON_LIMIT", "250") or "250")
    limit = max(1, min(250, limit))

    page = int(os.getenv("RETAILOS_ONECHEQ_START_PAGE", "1") or "1")
    if page < 1:
        page = 1

    pages_seen = 0
    total = 0
    started = time.monotonic()

    max_products_env = os.getenv("RETAILOS_ONECHEQ_MAX_PRODUCTS")
    max_products = int(max_products_env) if (max_products_env and max_products_env.isdigit()) else None

    # Print/log shopify progress for operator visibility (even in cmd.exe).
    # Optional `cmd_id` lets the worker persist logs to the command detail UI.
    import logging
    log = logging.getLogger(__name__)

    while True:
        if max_pages and pages_seen >= int(max_pages):
            break

        url = _shopify_products_json_url(collection, page=page, limit=limit)
        try:
            elapsed = _fmt_secs(time.monotonic() - started)
            print(f"[ONECHEQ] Shopify JSON page {page} (collection={collection}, limit={limit}) elapsed={elapsed}")
            if cmd_id:
                log.info(f"ONECHEQ_JSON_PAGE cmd_id={cmd_id} collection={collection} page={page} limit={limit} elapsed={elapsed}")
        except Exception:
            pass

        r = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        products = (r.json() or {}).get("products") or []
        if not products:
            break

        pages_seen += 1
        for p in products:
            handle = (p or {}).get("handle") or ""
            if not handle:
                continue

            title = norm_ws((p or {}).get("title") or "") or handle
            desc = _strip_html((p or {}).get("body_html") or "") or title

            vendor = norm_ws((p or {}).get("vendor") or "")
            product_type = norm_ws((p or {}).get("product_type") or "")

            # OneCheq encodes condition inside vendor sometimes: "Condition: New"
            condition = "Used"
            brand = vendor
            m = re.search(r"condition\s*:\s*(new|used|refurbished)", vendor, re.I)
            if m:
                condition = m.group(1).capitalize()
                brand = ""

            variants = (p or {}).get("variants") or []
            price = 0.0
            available = False
            supplier_lot = ""
            try:
                if variants and isinstance(variants, list):
                    v0 = variants[0] or {}
                    price = float(str(v0.get("price") or "0").replace(",", ""))
                    available = bool(v0.get("available", False))
                    supplier_lot = normalize_sku(str(v0.get("sku") or v0.get("id") or ""))  # best-effort
            except Exception:
                price = 0.0

            imgs = []
            for im in (p or {}).get("images") or []:
                if isinstance(im, dict):
                    src = (im.get("src") or "").strip()
                    if src:
                        imgs.append(src.split("?")[0])
                elif isinstance(im, str):
                    imgs.append(im.split("?")[0])
            imgs = [x for x in imgs if x][:4]

            specs = {}
            if brand:
                specs["Vendor"] = brand
            if product_type:
                specs["ProductType"] = product_type
            if supplier_lot:
                lot = supplier_lot
                if lot.isdigit() and lot.startswith("0"):
                    lot = f"LOT{lot}"
                specs["SupplierLot"] = lot
            specs["Condition"] = condition

            total += 1
            yield {
                "source_id": f"OC-{handle}",
                "source_url": f"https://onecheq.co.nz/products/{handle}",
                "title": title,
                "description": desc,
                "brand": brand,
                "condition": condition,
                "buy_now_price": price,
                "stock_level": 1 if available else 0,
                "photo1": imgs[0] if len(imgs) > 0 else None,
                "photo2": imgs[1] if len(imgs) > 1 else None,
                "photo3": imgs[2] if len(imgs) > 2 else None,
                "photo4": imgs[3] if len(imgs) > 3 else None,
                "source_status": "Available" if available else "Sold",
                "specs": specs,
                "sku": handle,
                "collection_rank": total,
                "collection_page": page,
            }

            if max_products and total >= int(max_products):
                return

        # Periodic progress for long runs
        if total and (total % 250 == 0 or total % 1000 == 0):
            try:
                elapsed = _fmt_secs(time.monotonic() - started)
                print(f"[ONECHEQ] JSON progress: {total} products processed (pages_seen={pages_seen}) elapsed={elapsed}")
                if cmd_id:
                    log.info(f"ONECHEQ_JSON_PROGRESS cmd_id={cmd_id} collection={collection} pages_seen={pages_seen} total={total} elapsed={elapsed}")
            except Exception:
                pass

        page += 1


def scrape_onecheq_product(url: str, client: Optional[httpx.Client] = None) -> Optional[Dict]:
    """
    Scrape a single OneCheq product page.
    Returns dict with product data or None if scraping fails.
    """
    print(f"Scraping OneCheq product: {url}")
    
    # Extract product ID
    product_id = extract_onecheq_id(url)
    
    # Fetch HTML
    html = get_html_via_httpx(url, client=client)
    if not html:
        print(f"ERROR: Failed to fetch HTML from {url}")
        return None
    
    if not HTMLParser:
        print("ERROR: Selectolax not available")
        return None
    
    # Parse with Selectolax
    doc = HTMLParser(html)
    products_jsonld = _iter_jsonld_products(doc)
    
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
            # Used for control flow to break out of nested JSON-LD parsing loops once a title is found.
            pass
        except Exception as e:
            # Best-effort JSON-LD parsing; ignore failures but log for debugging.
            print(f"Error parsing JSON-LD product data: {e}")
    
    # Extract supplier-provided SKU/MPN (often a lot number on OneCheq).
    # IMPORTANT: this value is not reliably unique across the entire catalog, so we do NOT use it as our primary key.
    supplier_sku_extracted = _extract_sku_from_jsonld(products_jsonld) or ""
    sku_node = doc.css_first(".product__sku, [class*='sku'], .variant-sku")
    if sku_node:
        sku_text = norm_ws(sku_node.text())
        # Extract just the SKU value (e.g., "SKU: LOT731" -> "LOT731")
        sku_match = re.search(r'SKU:?\s*([A-Z0-9]+)', sku_text, re.IGNORECASE)
        if sku_match:
            supplier_sku_extracted = normalize_sku(sku_match.group(1))

    # Canonical primary identifier for our pipeline: Shopify product handle from URL (stable & unique).
    # This prevents data corruption caused by reused lot numbers overwriting other rows.
    sku = (product_id or "").strip()
    if not sku:
        sku = (supplier_sku_extracted or "").strip()
    
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

    # Meta price fallback (Shopify often exposes these reliably)
    if not price:
        meta_price = doc.css_first(
            'meta[property="product:price:amount"], meta[property="og:price:amount"], meta[itemprop="price"], meta[name="product:price:amount"]'
        )
        if meta_price:
            raw = (meta_price.attributes.get("content") or "").strip()
            m = re.search(r"([0-9]+(?:\\.[0-9]+)?)", raw.replace(",", ""))
            if m:
                try:
                    price = float(m.group(1))
                except Exception:
                    pass

    # JSON-LD price fallback (use pre-parsed Product objects; avoid json.loads on broken scripts)
    if not price:
        try:
            for p in products_jsonld:
                offers = p.get("offers")
                offer_list = []
                if isinstance(offers, dict):
                    offer_list = [offers]
                elif isinstance(offers, list):
                    offer_list = [x for x in offers if isinstance(x, dict)]
                for off in offer_list:
                    pval = off.get("price")
                    if pval is None:
                        continue
                    sval = str(pval).replace(",", "").strip()
                    m = re.search(r"([0-9]+(?:\\.[0-9]+)?)", sval)
                    if not m:
                        continue
                    price = float(m.group(1))
                    raise StopIteration()
        except StopIteration:
            # Used to break out of nested loops once a valid price has been found.
            pass
        except Exception as e:
            # Best-effort JSON-LD extraction; ignore failures but log for debugging.
            print(f"Error while extracting JSON-LD price data: {e}")
    
    # Extract condition
    condition = "Used"  # Default for OneCheq
    condition_node = doc.css_first(".product__condition, [class*='condition']")
    if condition_node:
        condition_text = norm_ws(condition_node.text())
        if 'new' in condition_text.lower():
            condition = "New"
        elif 'refurbished' in condition_text.lower():
            condition = "Refurbished"
    
    # Extract brand (prefer JSON-LD Product.brand; then meta hints; then title heuristic)
    brand = _extract_brand_from_jsonld(products_jsonld)
    if not brand:
        meta_brand = doc.css_first('meta[property="product:brand"], meta[name="product:brand"], meta[name="brand"]')
        if meta_brand:
            brand = norm_ws(meta_brand.attributes.get("content", ""))

    if not brand and title:
        brand_match = re.match(r"^([A-Za-z][A-Za-z0-9&]+)", title)
        if brand_match:
            brand = brand_match.group(1).strip()
    
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
            for p in products_jsonld:
                desc = p.get("description") or ""
                if desc:
                    description = norm_ws(str(desc))
                    raise StopIteration()
        except StopIteration:
            # Used for early exit once a valid description has been found.
            pass
        except Exception as e:
            # Best-effort JSON-LD parsing; ignore failures but log for debugging.
            print(f"Error parsing JSON-LD for description: {e}")

    # Ensure description isn't absurdly short; fall back to title.
    if description and len(description) < 20 and title:
        description = title

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

    # Preserve extracted supplier SKU/lot for audit/search, but do NOT use it as the primary key.
    # IMPORTANT: store it in a "phone-regex-safe" form (avoid leading 0 at a word boundary).
    if supplier_sku_extracted and supplier_sku_extracted.strip():
        lot = supplier_sku_extracted.strip()
        if lot.isdigit() and lot.startswith("0"):
            lot = f"LOT{lot}"
        specs.setdefault("SupplierLot", lot)
    
    # Extract images
    images = []
    
    def _canon_img(u: str) -> str:
        u = (u or "").strip()
        if not u:
            return ""
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/") and not u.startswith("http"):
            u = "https://onecheq.co.nz" + u
        # Remove Shopify size parameters (best-effort)
        u = re.sub(r"_\\d+x\\d+\\.", ".", u)
        return u

    # 1) JSON-LD image field (often best signal)
    for p in products_jsonld:
        img = p.get("image")
        if isinstance(img, str):
            cu = _canon_img(img)
            if cu and cu not in images:
                images.append(cu)
        elif isinstance(img, list):
            for x in img:
                if isinstance(x, str):
                    cu = _canon_img(x)
                    if cu and cu not in images:
                        images.append(cu)

    # 2) OG image fallbacks
    for sel in ['meta[property="og:image"]', 'meta[name="twitter:image"]', 'meta[property="og:image:secure_url"]']:
        node = doc.css_first(sel)
        if node:
            cu = _canon_img(node.attributes.get("content") or "")
            if cu and cu not in images:
                images.append(cu)

    # 3) Shopify media gallery / product images (grab src, data-src, and srcset)
    img_nodes = doc.css(".product__media img, .product-gallery img, [class*='product-image'] img, img[srcset], img[data-srcset]")
    for img in img_nodes:
        src = img.attributes.get("src") or img.attributes.get("data-src") or ""
        srcset = img.attributes.get("srcset") or img.attributes.get("data-srcset") or ""
        candidates = []
        if src:
            candidates.append(src)
        if srcset:
            # pick the last candidate (usually highest resolution)
            parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
            if parts:
                candidates.append(parts[-1])
        for c in candidates:
            cu = _canon_img(c)
            if cu and cu not in images:
                images.append(cu)
    
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


def scrape_onecheq(limit_pages: int = 1, collection: str = "all", concurrency: int = 8, cmd_id: str | None = None):
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
    
    mode = (os.getenv("RETAILOS_ONECHEQ_SOURCE", "json") or "json").strip().lower()

    # Fast path: Shopify JSON (authoritative; scales to 10k+)
    if mode == "json":
        max_pages = 0 if limit_pages <= 0 else int(limit_pages)
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            yield from _iter_onecheq_products_via_shopify_json(collection=collection, max_pages=max_pages, client=client, cmd_id=cmd_id)
        return

    # Build collection URL (HTML fallback)
    if collection == "all":
        collection_url = "https://onecheq.co.nz/collections/all"
    else:
        collection_url = f"https://onecheq.co.nz/collections/{collection}"
    
    # Discover products (page fetches are cheap; product pages are expensive).
    max_pages = 999 if limit_pages <= 0 else limit_pages
    concurrency = max(1, min(32, int(concurrency or 1)))
    max_products_env = os.getenv("RETAILOS_ONECHEQ_MAX_PRODUCTS")
    max_products = int(max_products_env) if (max_products_env and max_products_env.isdigit()) else None

    # Reuse a single client for connection pooling (much faster).
    client = httpx.Client(follow_redirects=True, timeout=20.0)
    try:
        product_urls = discover_products_from_collection(collection_url, max_pages, client=client, max_products=max_products)
    finally:
        # We recreate a new client for concurrent section to avoid sharing mutable state across threads on older httpx versions.
        client.close()
    
    if not product_urls:
        print("No products found!")
        return
    
    # Scrape products concurrently (bounded). This is the main speed win.
    total = len(product_urls)
    print(f"Scraping {total} product pages with concurrency={concurrency} ...")

    # Use a threadpool; each worker uses its own client.
    def _scrape(url: str) -> Optional[Dict]:
        with httpx.Client(follow_redirects=True, timeout=20.0) as c:
            return scrape_onecheq_product(url, client=c)

    completed = 0
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {ex.submit(_scrape, url): url for url in product_urls}
        for fut in as_completed(futures):
            completed += 1
            url = futures[fut]
            try:
                product_data = fut.result()
                if product_data:
                    yield product_data
            except Exception as e:
                print(f"  [ERROR] {completed}/{total} failed url={url}: {e}")
            if completed % 25 == 0 or completed == total:
                print(f"  Progress: {completed}/{total} scraped")
    
    print(f"\\n=== Scraping Complete ===")
    print(f"Successfully scraped: {completed}/{len(product_urls)} products")


if __name__ == "__main__":
    # Test scraper
    products = list(scrape_onecheq(limit_pages=1, collection="smartphones-and-mobilephones"))
    print(f"\\nScraped {len(products)} products")
    if products:
        print("\\nSample product:")
        print(json.dumps(products[0], indent=2))
