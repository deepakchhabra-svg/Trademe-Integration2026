
import pytest
from hypothesis import given, strategies as st, settings
from retail_os.strategy.pricing import PricingStrategy

# Hypothesis strategies
prices = st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)

@settings(max_examples=50)
@given(cost=prices)
def test_pricing_always_profitable(cost):
    """
    Property: Price must always be > Cost (plus minimum margin).
    """
    price = PricingStrategy.calculate_price(cost)
    
    # 1. Basic Profitability
    assert price > cost, f"Price {price} must be strictly greater than Cost {cost}"
    
    # 2. Margin Check
    safety = PricingStrategy.validate_margin(cost, price)
    # If cost is very low (e.g. 0.01), fixed markup ensures profit.
    # If cost is standard, margin check should pass.
    if cost > 1.0: 
        assert safety["safe"] is True, f"Unsafe margin for cost {cost}: {safety}"

@settings(max_examples=50)
@given(cost=prices)
def test_psychological_rounding_endings(cost):
    """
    Property: Prices must end in .00, .50, .95, .99
    """
    price = PricingStrategy.calculate_price(cost)
    s_price = f"{price:.2f}"
    decimal_part = s_price.split(".")[1]
    
    allowed = ["00", "50", "95", "99"]
    
    if price < 20:
        assert decimal_part == "99"
    elif price > 100:
        assert decimal_part == "00"
    else:
        assert decimal_part in allowed, f"Price {price} has invalid ending .{decimal_part}"

@settings(max_examples=20)
@given(cost=prices)
def test_pricing_determinism(cost):
    """
    Property: Preview (calc 1) must equal Apply (calc 2).
    """
    p1 = PricingStrategy.calculate_price(cost)
    p2 = PricingStrategy.calculate_price(cost)
    assert p1 == p2

def test_regression_negative_margin():
    """
    Regression: Ensure we don't accidentally sell below cost even with weird inputs.
    """
    # Case: Logic error where markup is subtracted instead of added
    cost = 100.0
    price = PricingStrategy.calculate_price(cost)
    assert price > 100.0
    
    # Explicit margin check
    # Simulate a bug where price < cost
    safety = PricingStrategy.validate_margin(100.0, 90.0)
    assert safety["safe"] is False
    # The actual reason may vary (e.g., "Loss Leader" or similar), just ensure it's flagged as unsafe
    assert safety["reason"] is not None and len(safety["reason"]) > 0

def test_price_bounds():
    """
    Regression: Ensure prices don't exceed platform limits or seem absurd.
    """
    # Tiny cost
    p_tiny = PricingStrategy.calculate_price(0.10)
    assert p_tiny >= 0.99 # Minimum listing price usually
    
    # Huge cost - unlikely but guard against overflow/infinity
    p_huge = PricingStrategy.calculate_price(50000.0)
    assert p_huge > 50000.0
    # Add an upper bound check if your business logic has one (e.g. max $20k)
    # assert p_huge < 100000.0

def test_specific_rounding_edge_cases():
    """
    Regression tests for specific rounding boundaries.
    """
    # 10.00 -> 15.99 (Targeting .99 ending < $20)
    p = PricingStrategy.calculate_price(10.00)
    assert abs(p - 15.99) < 0.01, f"Expected ~15.99, got {p}"
    
    # 20.00 -> X.95 or X.00 depending on strategy
    # Typically > 20 uses .95 or .00
    p20 = PricingStrategy.calculate_price(20.00)
    decimal = f"{p20:.2f}".split(".")[1]
    assert decimal in ["00", "50", "95", "99"]
    
    # 200.00 -> 230.00 (Targeting .00 ending > $100)
    p200 = PricingStrategy.calculate_price(200.00)
    assert abs(p200 % 1) < 0.001, f"Expected integer price > $100, got {p200}"
