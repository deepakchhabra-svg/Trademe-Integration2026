
"""
Profitability Analysis Engine.
Calculates Net Profit after Trade Me Fees, Shipping, and COGS.
"""

from decimal import Decimal

class ProfitabilityAnalyzer:
    
    # Trade Me Standard Fees (Approximate Estimates for Pilot)
    SUCCESS_FEE_PCT = 0.079 # 7.9%
    SUCCESS_FEE_CAP = 249.00
    PING_FEE_PCT = 0.0195 # 1.95%
    
    @staticmethod
    def calculate_net_profit(sold_price: float, cost_price: float, shipping_charged: float, shipping_actual_cost: float, promo_fees: float = 0.0) -> dict:
        """
        Returns detailed profit breakdown.
        """
        sold_price = float(sold_price)
        cost_price = float(cost_price)
        
        # 1. Trade Me Success Fee
        tm_fee = min(sold_price * ProfitabilityAnalyzer.SUCCESS_FEE_PCT, ProfitabilityAnalyzer.SUCCESS_FEE_CAP)
        
        # 2. Payment Proc. Fee (Ping) - Assume 50% adoption for estimation
        ping_fee = sold_price * ProfitabilityAnalyzer.PING_FEE_PCT * 0.5
        
        # 3. Shipping Delta
        shipping_diff = shipping_charged - shipping_actual_cost
        
        # 4. Total Deductions
        total_fees = tm_fee + ping_fee + promo_fees
        total_costs = cost_price + shipping_actual_cost
        
        revenue = sold_price + shipping_charged
        
        net_profit = revenue - (cost_price + shipping_actual_cost + total_fees)
        
        # Avoid div by zero
        roi = (net_profit / cost_price * 100) if cost_price > 0 else 0.0
        
        return {
            "sold_price": sold_price,
            "cost_price": cost_price,
            "tm_success_fee": round(tm_fee, 2),
            "est_ping_fee": round(ping_fee, 2),
            "promo_fees": round(promo_fees, 2),
            "total_fees": round(total_fees, 2),
            "shipping_delta": round(shipping_diff, 2),
            "net_profit": round(net_profit, 2),
            "roi_percent": round(roi, 1),
            "is_profitable": net_profit > 0
        }

    @staticmethod
    def predict_profitability(listing_price: float, cost_price: float) -> dict:
        """
        Pre-listing check. Assumes standard shipping neutral.
        """
        return ProfitabilityAnalyzer.calculate_net_profit(
            sold_price=listing_price,
            cost_price=cost_price,
            shipping_charged=0,
            shipping_actual_cost=0
        )
