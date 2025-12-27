import sys
import os
sys.path.append(os.getcwd())

import re
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

def discover_cash_converters_urls(base_url: str, max_pages: int = 5) -> List[str]:
    """
    Discover listing URLs from Cash Converters browse pages.
    Returns list of /Listing/Details/XXXXX URLs.
    Continues through ALL pages up to max_pages (doesn't stop on empty pages).
    """
    print("=" * 60)
    print("CASH CONVERTERS DISCOVERY")
    print("=" * 60)
    
    seen_ids: Set[str] = set()
    urls = []
    consecutive_empty = 0
    
    for page in range(1, max_pages + 1):
        url = f"{base_url}?page={page}" if page > 1 else base_url
        print(f"\nPage {page}: {url}")
        
        html = get_html_via_curl(url)
        if not html:
            print(f"  [FAIL] Could not fetch page {page}")
            consecutive_empty += 1
            if consecutive_empty >= 5:  # Stop after 5 consecutive failures
                print(f"  [STOP] 5 consecutive page failures, stopping")
                break
            continue
        
        doc = HTMLParser(html)
        new_count = 0
        
        # Find all links with /Listing/Details/ pattern
        for a in doc.css("a[href]"):
            href = a.attributes.get("href") or ""
            match = re.search(r'/Listing/Details/(\d+)/', href)
            if match:
                listing_id = match.group(1)
                if listing_id not in seen_ids:
                    seen_ids.add(listing_id)
                    full_url = f"https://shop.cashconverters.co.nz/Listing/Details/{listing_id}/"
                    urls.append(full_url)
                    new_count += 1
        
        print(f"  Found {new_count} new listings (total: {len(urls)})")
        
        # Reset consecutive empty counter if we found items
        if new_count > 0:
            consecutive_empty = 0
        else:
            consecutive_empty += 1
            # Only stop if we have 10 consecutive empty pages AND we've found at least some items
            if consecutive_empty >= 10 and len(urls) > 0:
                print(f"  [STOP] 10 consecutive empty pages, stopping")
                break
    
    print(f"\n[OK] Discovered {len(urls)} unique Cash Converters URLs")
    return urls

def discover_noel_leeming_urls(base_url: str, max_pages: int = 5) -> List[str]:
    """
    Discover product URLs from Noel Leeming category pages.
    Returns list of product URLs.
    """
    print("=" * 60)
    print("NOEL LEEMING DISCOVERY")
    print("=" * 60)
    
    seen_urls: Set[str] = set()
    urls = []
    
    for page in range(1, max_pages + 1):
        # Noel Leeming uses ?start= for pagination
        start = (page - 1) * 32  # 32 items per page
        url = f"{base_url}?start={start}" if page > 1 else base_url
        print(f"\nPage {page}: {url}")
        
        html = get_html_via_curl(url)
        if not html:
            print(f"  [FAIL] Could not fetch page {page}")
            break
        
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
                
                seen_urls.add(href)
                urls.append(full_url)
                new_count += 1
        
        print(f"  Found {new_count} new products (total: {len(urls)})")
        
        if new_count == 0:
            print(f"  No new products, stopping")
            break
    
    print(f"\n[OK] Discovered {len(urls)} unique Noel Leeming URLs")
    return urls

if __name__ == "__main__":
    # Test discovery
    cc_url = "https://shop.cashconverters.co.nz/Browse/R160787-R160789/North_Island-Auckland"
    nl_url = "https://www.noelleeming.co.nz/shop/computers-office-tech/computers"
    
    cc_urls = discover_cash_converters_urls(cc_url, max_pages=2)
    print(f"\nFirst 5 CC URLs:")
    for url in cc_urls[:5]:
        print(f"  {url}")
    
    # nl_urls = discover_noel_leeming_urls(nl_url, max_pages=2)
    # print(f"\nFirst 5 NL URLs:")
    # for url in nl_urls[:5]:
    #     print(f"  {url}")
