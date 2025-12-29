
import os
import sys
from decimal import Decimal

# Add parent dir to path
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SupplierProduct, InternalProduct, TradeMeListing, Supplier
from retail_os.core.marketplace_adapter import MarketplaceAdapter
from retail_os.core.standardizer import Standardizer
from retail_os.strategy.pricing import PricingStrategy
from sqlalchemy import func

def run_deep_audit():
    session = SessionLocal()
    print("="*80)
    print("RETAIL OS: SYSTEM DEEP AUDIT & VALIDATION")
    print("="*80)

    # 1. Scraping & Data Integrity (Per Supplier)
    print("\n[1] DATA EXTRACTION & INTEGRITY CHECK")
    suppliers = session.query(Supplier).all()
    for s in suppliers:
        count = session.query(SupplierProduct).filter_by(supplier_id=s.id).count()
        with_specs = session.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == s.id,
            SupplierProduct.specs != {}
        ).count()
        print(f"  Supplier: {s.name:20} | Scraped: {count:4} | With Tech Specs: {with_specs:4}")

    # 2. Enrichment & Marketing Removal Showcase
    print("\n[2] ENRICHMENT & CONTENT POLISHING (Marketing Removal)")
    # Pick a sample OneCheq item
    sample = session.query(SupplierProduct).filter(SupplierProduct.supplier_id == 1).first()
    if sample:
        processed = MarketplaceAdapter.prepare_for_trademe(sample, use_ai=False) # Heuristic check
        print(f"  Sample Item: {sample.title[:50]}...")
        print(f"  Raw Desc Length: {len(sample.description or '')}")
        print(f"  Cleaned Desc Length: {len(processed['description'])}")
        
        # Check for banned words in cleaned desc
        found_banned = [w for w in Standardizer.BANNED_TOPICS if w in processed['description'].lower()]
        print(f"  Marketing Stripping Result: {'PASSED (Clean)' if not found_banned else f'FAILED (Found: {found_banned})'}")
        
    # 3. Margin & Financial Validation
    print("\n[3] MARGIN & PRICING STRATEGY CHECK")
    for s in suppliers:
        sp = session.query(SupplierProduct).filter_by(supplier_id=s.id).first()
        if sp and sp.cost_price > 0:
            final_price = PricingStrategy.calculate_price(sp.cost_price, supplier_name=s.name)
            markup = final_price - float(sp.cost_price)
            margin_pct = (markup / final_price) * 100
            print(f"  {s.name:20}: Cost: ${sp.cost_price:7.2f} -> Sell: ${final_price:7.2f} | Margin: {margin_pct:5.1f}% (Markup: ${markup:.2f})")

    # 4. Consistency & Shipping (Draft Payload Verification)
    print("\n[4] LISTING CONSISTENCY (Shipping & Payment)")
    from retail_os.trademe.config import TradeMeConfig
    print(f"  Payment Methods: {TradeMeConfig.get_payment_methods()} (Default: 5 = Bank Deposit + Cash)")
    print(f"  Shipping Options: {len(TradeMeConfig.DEFAULT_SHIPPING)} types configured.")
    for opt in TradeMeConfig.DEFAULT_SHIPPING:
        print(f"    - {opt['Method']}: ${opt['Price']:.2f}")

    # 5. Trust Gate Status
    print("\n[5] TRUST GATE & GATEKEEPING")
    from retail_os.core.trust import TrustEngine
    engine = TrustEngine(session)
    recent_ips = session.query(InternalProduct).limit(5).all()
    for ip in recent_ips:
        report = engine.get_product_trust_report(ip)
        print(f"  IP {ip.id:4} | Trust: {report.score:5.1f}% | Passed: {str(report.is_trusted):5} | Blockers: {report.blockers}")

    session.close()

if __name__ == "__main__":
    run_deep_audit()
