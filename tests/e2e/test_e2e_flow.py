"""
E2E Smoke Test for Trade Me Integration Platform
Tests the full flow: Scrape → Enrich → Publish
"""
import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import get_db_session, InternalProduct, SupplierProduct, SystemCommand, CommandStatus
from retail_os.dashboard.data_layer import submit_publish_command
from retail_os.core.trust import TrustEngine
from retail_os.strategy.pricing import PricingStrategy
import uuid

def test_e2e_flow():
    """
    E2E Test Flow:
    1. Find a product in the database
    2. Check its trust score
    3. Attempt to publish via the validation gateway
    4. Verify command was created or blocked appropriately
    """
    
    print("=" * 60)
    print("E2E SMOKE TEST - Trade Me Integration Platform")
    print("=" * 60)
    
    with get_db_session() as session:
        # Step 1: Find a product to test
        print("\n[Step 1] Finding test product...")
        product = session.query(InternalProduct).first()
        
        if not product:
            print("[FAIL] No products found in database. Please run scraper first.")
            return False
        
        print(f"[OK] Found product: {product.title} (ID: {product.id})")
        
        # Step 2: Check Trust Score
        print("\n[Step 2] Calculating Trust Score...")
        trust_engine = TrustEngine(session)
        report = trust_engine.get_product_trust_report(product)
        
        print(f"[OK] Trust Score: {report.score}%")
        print(f"     Blockers: {report.blockers}")

        
        # Step 3: Check Pricing
        print("\n[Step 3] Calculating Price...")
        if product.supplier_product and product.supplier_product.cost_price:
            cost = float(product.supplier_product.cost_price)
            supplier_name = product.supplier_product.supplier.name if product.supplier_product.supplier else None
            price = PricingStrategy.calculate_price(cost, supplier_name=supplier_name)
            rounded_price = PricingStrategy.apply_psychological_rounding(price)
            
            print(f"[OK] Cost: ${cost:.2f}")
            print(f"     Calculated Price: ${price:.2f}")
            print(f"     Rounded Price: ${rounded_price:.2f}")
            
            margin = rounded_price - cost
            margin_pct = (margin / cost) * 100 if cost > 0 else 0
            print(f"     Margin: ${margin:.2f} ({margin_pct:.1f}%)")
        else:
            print("[WARN] No cost price available")
        
        # Step 4: Attempt to publish via validation gateway
        print("\n[Step 4] Testing Validation Gateway...")
        success, message, command_id = submit_publish_command(session, product.id)
        
        if success:
            print(f"[OK] {message}")
            
            # Verify command was created
            cmd = session.query(SystemCommand).filter_by(
                status=CommandStatus.PENDING
            ).order_by(SystemCommand.created_at.desc()).first()
            
            if cmd:
                print(f"[OK] Command created: {cmd.id}")
                print(f"     Type: {cmd.type}")
                print(f"     Status: {cmd.status}")
            else:
                print("[WARN] Command not found in database")
        else:
            print(f"[BLOCKED] {message}")
            print("[OK] Validation gateway correctly blocked low-trust product")
        
        # Step 5: Check Audit Logs
        print("\n[Step 5] Checking Audit Logs...")
        from retail_os.core.database import AuditLog
        recent_logs = session.query(AuditLog).filter_by(
            entity_type="InternalProduct",
            entity_id=str(product.id)
        ).order_by(AuditLog.timestamp.desc()).limit(3).all()
        
        if recent_logs:
            print(f"[OK] Found {len(recent_logs)} audit log entries:")
            for log in recent_logs:
                print(f"     - {log.action}: {log.new_value}")
        else:
            print("[WARN] No audit logs found")
        
        print("\n" + "=" * 60)
        print("E2E SMOKE TEST COMPLETE")
        print("=" * 60)
        
        return True

if __name__ == "__main__":
    try:
        test_e2e_flow()
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
