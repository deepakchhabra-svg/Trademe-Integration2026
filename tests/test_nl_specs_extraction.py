"""
Fixture-based tests for Noel Leeming sellable specs extraction.
Tests the parsing logic without requiring live Selenium or network access.
"""
import sys
import os
import pytest
from selectolax.parser import HTMLParser

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# We test the extraction logic directly by simulating HTML parsing.
# The actual scrape_product_detail uses Selenium, but the parsing is done with selectolax.
# We'll create a helper that mirrors the extraction logic for testing.

import re
from urllib.parse import urljoin

BASE_URL = "https://www.noelleeming.co.nz"

def extract_specs_from_html(html: str, url: str = "https://www.noelleeming.co.nz/p/test-product/N123456.html") -> dict:
    """
    Extract sellable specs from HTML content.
    Mirrors the logic in scrape_product_detail() for testability without Selenium.
    """
    tree = HTMLParser(html)
    specs = {}
    
    # --- Product ID / SKU ---
    sku_match = re.search(r'/([A-Z]?\d{5,10})\.html', url)
    if sku_match:
        specs["sku"] = sku_match.group(1)
        numeric_match = re.search(r'(\d+)', sku_match.group(1))
        if numeric_match:
            specs["product_id"] = numeric_match.group(1)
    
    sku_node = tree.css_first(".product-manufacturer-sku .value, .product-id .value")
    if sku_node:
        sku_text = sku_node.text(strip=True)
        specs["model"] = sku_text
        if "product_id" not in specs:
            numeric = re.search(r'(\d+)', sku_text)
            if numeric:
                specs["product_id"] = numeric.group(1)
    
    # --- Features List ---
    features = []
    feature_nodes = tree.css(".product-features-benefits ul li, .product-features li, .features-list li")
    for li in feature_nodes:
        text = li.text(strip=True)
        if text and len(text) > 3 and len(text) < 500:
            features.append(text)
    specs["features"] = features
    
    # --- Warranty Months ---
    warranty_months = None
    # Match patterns like "12 month warranty", "2 year warranty", "2 year manufacturer warranty"
    warranty_pattern = re.compile(r'(\d+)\s*(?:month|year)s?(?:\s+\w+)?\s*(?:warranty|guarantee)', re.IGNORECASE)
    for f in features:
        match = warranty_pattern.search(f)
        if match:
            val = int(match.group(1))
            if "year" in f.lower():
                val = val * 12
            warranty_months = val
            break
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
    stock_status = "UNKNOWN"
    stock_node = tree.css_first(".availability-status, .stock-status, .in-stock, .out-of-stock, .product-availability")
    if stock_node:
        stock_text = stock_node.text(strip=True).lower()
        if "out of stock" in stock_text or "unavailable" in stock_text:
            stock_status = "OUT_OF_STOCK"
        elif "low stock" in stock_text or "limited" in stock_text or "few left" in stock_text:
            stock_status = "LOW_STOCK"
        elif "in stock" in stock_text or "available" in stock_text:
            stock_status = "IN_STOCK"
    if stock_status == "UNKNOWN":
        add_btn = tree.css_first("button.add-to-cart, button.add-to-basket, .add-to-cart-button")
        if add_btn:
            btn_disabled = add_btn.attributes.get("disabled")
            if btn_disabled:
                stock_status = "OUT_OF_STOCK"
            else:
                stock_status = "IN_STOCK"
    specs["stock_status"] = stock_status
    
    # --- Offer End Date ---
    offer_end_date = None
    promo_node = tree.css_first(".promo-end-date, .offer-ends, .sale-ends, .promotion-end")
    if promo_node:
        promo_text = promo_node.text(strip=True)
        date_match = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})', promo_text)
        if date_match:
            d, m, y = date_match.groups()
            y = int(y) if len(y) == 4 else 2000 + int(y)
            offer_end_date = f"{y:04d}-{int(m):02d}-{int(d):02d}"
    specs["offer_end_date"] = offer_end_date
    
    # --- Condition ---
    condition_raw = None
    condition_normalized = "NEW"
    condition_node = tree.css_first(".product-condition, .condition-badge, .refurbished-badge")
    if condition_node:
        condition_raw = condition_node.text(strip=True)
        condition_lower = condition_raw.lower()
        if "refurb" in condition_lower or "renewed" in condition_lower:
            condition_normalized = "REFURBISHED"
        elif "used" in condition_lower or "pre-owned" in condition_lower:
            condition_normalized = "USED"
    page_text_lower = (tree.body.text() if tree.body else "").lower()
    if "refurbished" in page_text_lower or "renewed" in page_text_lower:
        condition_normalized = "REFURBISHED"
        if not condition_raw:
            condition_raw = "Refurbished"
    specs["condition_raw"] = condition_raw
    specs["condition_normalized"] = condition_normalized
    
    return specs


# ============================================================
# HTML FIXTURES
# ============================================================

FIXTURE_NL_PRODUCT_PAGE = """
<!DOCTYPE html>
<html>
<head><title>Apple MacBook Pro 14-inch</title></head>
<body>
    <h1 class="product-name">Apple MacBook Pro 14-inch with M4 Chip</h1>
    
    <div class="product-manufacturer-sku">
        <span class="label">Model:</span>
        <span class="value">MRX63NZ/A</span>
    </div>
    
    <div class="product-features-benefits">
        <ul>
            <li>Apple M4 chip with 10-core CPU</li>
            <li>16GB unified memory</li>
            <li>512GB SSD storage</li>
            <li>14.2-inch Liquid Retina XDR display</li>
            <li>12 month warranty included</li>
        </ul>
    </div>
    
    <div class="availability-status">In Stock</div>
    
    <div class="promo-end-date">Offer ends 15/01/2024</div>
    
    <button class="add-to-cart">Add to Cart</button>
    
    <div class="product-description">
        The new MacBook Pro delivers exceptional performance with the M4 chip.
    </div>
</body>
</html>
"""

FIXTURE_NL_OUT_OF_STOCK = """
<!DOCTYPE html>
<html>
<body>
    <h1>Samsung Galaxy S24</h1>
    <div class="product-features-benefits">
        <ul>
            <li>6.2-inch Dynamic AMOLED display</li>
            <li>2 year manufacturer warranty</li>
        </ul>
    </div>
    <div class="availability-status">Out of Stock</div>
    <button class="add-to-cart" disabled>Add to Cart</button>
</body>
</html>
"""

FIXTURE_NL_REFURBISHED = """
<!DOCTYPE html>
<html>
<body>
    <h1>Apple iPhone 13 (Refurbished)</h1>
    <div class="refurbished-badge">Certified Refurbished</div>
    <div class="product-features-benefits">
        <ul>
            <li>128GB Storage</li>
            <li>6 months warranty</li>
        </ul>
    </div>
    <div class="stock-status">In stock - Limited availability</div>
</body>
</html>
"""


# ============================================================
# TESTS
# ============================================================

def test_extract_product_id_and_sku():
    """Test extraction of product_id and sku from URL."""
    specs = extract_specs_from_html(FIXTURE_NL_PRODUCT_PAGE)
    
    assert specs["product_id"] == "123456"
    assert specs["sku"] == "N123456"


def test_extract_model():
    """Test extraction of model number from page."""
    specs = extract_specs_from_html(FIXTURE_NL_PRODUCT_PAGE)
    
    assert specs["model"] == "MRX63NZ/A"


def test_extract_features():
    """Test extraction of features list."""
    specs = extract_specs_from_html(FIXTURE_NL_PRODUCT_PAGE)
    
    assert isinstance(specs["features"], list)
    assert len(specs["features"]) == 5
    assert "Apple M4 chip with 10-core CPU" in specs["features"]
    assert "14.2-inch Liquid Retina XDR display" in specs["features"]


def test_extract_warranty_months():
    """Test extraction and parsing of warranty duration."""
    specs = extract_specs_from_html(FIXTURE_NL_PRODUCT_PAGE)
    assert specs["warranty_months"] == 12
    
    # Test year conversion
    specs_year = extract_specs_from_html(FIXTURE_NL_OUT_OF_STOCK, url="https://www.noelleeming.co.nz/p/test/N999999.html")
    assert specs_year["warranty_months"] == 24  # 2 years = 24 months


def test_extract_stock_status_in_stock():
    """Test stock status extraction for in-stock items."""
    specs = extract_specs_from_html(FIXTURE_NL_PRODUCT_PAGE)
    assert specs["stock_status"] == "IN_STOCK"


def test_extract_stock_status_out_of_stock():
    """Test stock status extraction for out-of-stock items."""
    specs = extract_specs_from_html(FIXTURE_NL_OUT_OF_STOCK, url="https://www.noelleeming.co.nz/p/test/N888888.html")
    assert specs["stock_status"] == "OUT_OF_STOCK"


def test_extract_stock_status_low_stock():
    """Test stock status extraction for low-stock items."""
    specs = extract_specs_from_html(FIXTURE_NL_REFURBISHED, url="https://www.noelleeming.co.nz/p/test/N777777.html")
    assert specs["stock_status"] == "LOW_STOCK"


def test_extract_offer_end_date():
    """Test extraction of promotional offer end date."""
    specs = extract_specs_from_html(FIXTURE_NL_PRODUCT_PAGE)
    assert specs["offer_end_date"] == "2024-01-15"


def test_extract_condition_new():
    """Test condition defaults to NEW for standard products."""
    specs = extract_specs_from_html(FIXTURE_NL_PRODUCT_PAGE)
    assert specs["condition_normalized"] == "NEW"
    assert specs["condition_raw"] is None


def test_extract_condition_refurbished():
    """Test condition detection for refurbished items."""
    specs = extract_specs_from_html(FIXTURE_NL_REFURBISHED, url="https://www.noelleeming.co.nz/p/test/N666666.html")
    assert specs["condition_normalized"] == "REFURBISHED"
    assert specs["condition_raw"] == "Certified Refurbished"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
