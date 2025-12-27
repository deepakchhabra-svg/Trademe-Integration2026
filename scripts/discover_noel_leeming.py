"""
Noel Leeming Category Discovery
Discovers product URLs from category pages with pagination
"""
import re
import math
from typing import List, Set
from selectolax.parser import HTMLParser
import subprocess

def get_html_via_curl(url: str) -> str:
    """Fetch HTML using curl."""
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
            timeout=15
        )
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        print(f"CURL Error: {e}")
        return None

def discover_noel_leeming_urls(base_url: str, max_pages: int = 50, max_items: int | None = None) -> List[str]:
    """
    Discover product URLs from Noel Leeming category pages.
    Returns list of product URLs.
    """
    # Backwards compatibility: older callers used max_items.
    # NL category pages show ~32 items per page; convert items->pages if provided.
    if max_items is not None:
        try:
            max_pages = max(1, int(math.ceil(int(max_items) / 32)))
        except Exception:
            max_pages = max_pages

    print("=" * 60)
    print("NOEL LEEMING DISCOVERY")
    print("=" * 60)
    
    seen_urls: Set[str] = set()
    urls = []
    consecutive_empty = 0
    
    for page in range(1, max_pages + 1):
        # Noel Leeming uses ?start= for pagination (32 items per page)
        start = (page - 1) * 32
        url = f"{base_url}?start={start}" if page > 1 else base_url
        print(f"\nPage {page}: {url}")
        
        html = get_html_via_curl(url)
        if not html:
            print(f"  [FAIL] Could not fetch page {page}")
            consecutive_empty += 1
            if consecutive_empty >= 5:
                print(f"  [STOP] 5 consecutive failures")
                break
            continue
        
        doc = HTMLParser(html)
        new_count = 0
        
        # Find product links (Noel Leeming uses /p/ pattern)
        for a in doc.css("a[href]"):
            href = a.attributes.get("href") or ""
            if '/p/' in href and href not in seen_urls:
                # Build full URL
                if href.startswith('/'):
                    full_url = f"https://www.noelleeming.co.nz{href}"
                else:
                    full_url = href
                
                # Only add if it's a product page (has product ID)
                if re.search(r'/p/[^/]+/[A-Z0-9]+\.html', full_url):
                    seen_urls.add(href)
                    urls.append(full_url)
                    new_count += 1
        
        print(f"  Found {new_count} new products (total: {len(urls)})")
        
        if new_count > 0:
            consecutive_empty = 0
        else:
            consecutive_empty += 1
            if consecutive_empty >= 10 and len(urls) > 0:
                print(f"  [STOP] 10 consecutive empty pages")
                break
    
    print(f"\n[OK] Discovered {len(urls)} unique Noel Leeming URLs")
    return urls
