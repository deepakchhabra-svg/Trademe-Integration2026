# 🤖 Universal Scraper Guide
**Code Location:** `retail_os/scrapers/universal/adapter.py`

This often-overlooked module is the "Magic Wand" of the system.

## How to use it manually
```python
from retail_os.scrapers.universal.adapter import UniversalAdapter

ua = UniversalAdapter()
ua.import_url("https://www.thewarehouse.co.nz/p/some-product")
```

## How it works
1.  **CURL Bypass**: Uses system `curl` to bypass 403 blocks (Line 28).
2.  **OpenGraph Extraction**: Reads `<meta property="og:title">` (Line 92).
3.  **Auto-Supplier**: Detects domain (e.g., `thewarehouse`) and creates a new Supplier ID automatically (Line 50).

## Why this matters
This satisfies the requirement: *"automatic development of scraping for any new site with ease"*. You don't need to write code for simple sites; you just feed the URL.
