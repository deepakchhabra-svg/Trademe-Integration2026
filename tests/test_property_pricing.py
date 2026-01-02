
import pytest
from hypothesis import given, strategies as st, settings
from retail_os.strategy.pricing import PricingStrategy

# Hypothesis strategies
prices = st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)

@settings(max_examples=50)
@given(cost=prices)
def test_pricing_always_profitable(cost):
    """
    Property: Price must always be > Cost.
    """
    price = PricingStrategy.calculate_price(cost)
    assert price >= cost, f"Price {price} should be >= Cost {cost}"
    
    # Margin check using the static method
    safety = PricingStrategy.validate_margin(cost, price)
    if cost > 0.10: # avoid tiny rounding issues with near-zero
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

def test_specific_edge_cases():
    """
    Regression tests for specific values.
    """
    # 10.00 -> 15.99
    p = PricingStrategy.calculate_price(10.00)
    assert abs(p - 15.99) < 0.01
    
    # 200.00 -> 230.00
    p200 = PricingStrategy.calculate_price(200.00)
    assert abs(p200 - 230.00) < 0.01
