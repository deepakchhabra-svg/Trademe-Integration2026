"""
Pricing Strategy Engine
Handles dynamic pricing logic, markups, and psychological rounding.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

class PricingStrategy:
    """
    Central logic for determining the selling price of an item.
    """
    
    # Default Markup Rules (can be overridden)
    MIN_MARGIN_DOLLARS = 5.00
    MIN_MARGIN_PERCENT = 0.15 # 15%
    
    @staticmethod
    def calculate_price(cost_price: float, category: str = "General", supplier_name: str = None) -> float:
        """
        Calculate the listing price based on cost.
        Applies margin rules, supplier overrides, and psychological rounding.
        """
        if cost_price is None or cost_price <= 0:
            return 0.0
            
        # 1. Base Markup Strategy
        from retail_os.trademe.config import TradeMeConfig
        mode = TradeMeConfig.MODE
        
        # Default Base
        pct = PricingStrategy.MIN_MARGIN_PERCENT
        flat = PricingStrategy.MIN_MARGIN_DOLLARS
        
        # A. Mode Adjustments
        if mode == "AGGRESSIVE":
            pct = 0.10; flat = 3.00
        elif mode == "HARVEST":
            pct = 0.25; flat = 10.00
            
        # B. Supplier Overrides (Wins over Mode)
        if supplier_name:
            overrides = TradeMeConfig.SUPPLIER_MARGIN_OVERRIDES.get(supplier_name.upper())
            if overrides:
                pct = overrides.get("pct", pct)
                flat = overrides.get("flat", flat)
        
        # Convert Decimal to float before arithmetic operations
        cost_float = float(cost_price) if cost_price else 0.0
        
        markup_pct = cost_float * pct
        markup_flat = flat
        
        target_margin = max(markup_pct, markup_flat)
        raw_price = cost_float + target_margin
        
        # 2. Psychological Rounding
        final_price = PricingStrategy.apply_psychological_rounding(raw_price)
        
        return float(final_price)

    @staticmethod
    def apply_psychological_rounding(price: float) -> float:
        """
        Rounds prices to 'pretty' numbers.
        < 20: Round to .99
        20 - 100: Round to .00 or .50
        > 100: Round to .00
        """
        d_price = Decimal(str(price))
        whole = int(d_price)
        fraction = float(d_price - whole)
        
        if price < 20:
            # e.g. 15.40 -> 15.99
            return whole + 0.99
            
        elif price < 100:
            # Round to nearest .00 or .50 or .99
            # Simple strategy: If > .75 -> Next Dollar .00
            # If > .25 -> .50
            # Else -> .00
            if fraction > 0.75:
                return whole + 1.00
            elif fraction > 0.25:
                # actually 95/99 is better for retail
                return whole + 0.95
            else:
                return whole + 0.00
                
        else:
            # > 100, usually round to whole dollar
            # e.g. 154.30 -> 155.00
            return float(Decimal(price).quantize(Decimal('1.'), rounding=ROUND_HALF_UP))
            
    @staticmethod
    def validate_margin(cost: float, price: float) -> dict:
        """Checks if a price is safe (profitable)."""
        if price <= cost:
            return {"safe": False, "reason": "Loss Leader"}
        
        margin = (price - cost) / price
        if margin < 0.05: # 5% absolute floor
            return {"safe": False, "reason": "Low Margin (<5%)"}
            
        return {"safe": True, "margin_percent": margin}
