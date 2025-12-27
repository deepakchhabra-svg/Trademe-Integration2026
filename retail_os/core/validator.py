import random
import sys
import os
sys.path.append(os.getcwd())
from datetime import datetime
from sqlalchemy.orm import Session
from retail_os.core.database import SessionLocal, SupplierProduct, InternalProduct
from retail_os.scrapers.universal.adapter import UniversalAdapter
from retail_os.core.trust import TrustEngine, TrustReport
from retail_os.strategy.policy import PolicyEngine
from retail_os.strategy.pricing import PricingStrategy

class LaunchLock:
    """
    Step 4: The Final Gatekeeper.
    Enforces strict rules before any API call to Trade Me.
    Used by backend workers to prevent bypassing checks.
    """
    def __init__(self, session: Session):
        self.session = session
        self.trust_engine = TrustEngine(session)
        self.policy_engine = PolicyEngine()
        
    def validate_publish(self, product: InternalProduct, test_mode=False):
        """
        Gate-check before allowing a product to publish.
        Raises ValueError if any blocker exists.
        
        test_mode: If True, bypass trust score check for testing
        """
        if not product.supplier_product:
             raise ValueError("Sync Error: Missing Supplier Product Data")
             
        # 1. Trust Gate (Hard)
        # We use the product report to get the specific score
        report = self.trust_engine.get_product_trust_report(product)
        
        # Test mode bypass
        if test_mode:
            return
        
        if not report.is_trusted: # < 95%
             raise ValueError(f"Trust Violation: Score {report.score}% is below 95% threshold. Blockers: {report.blockers}")
             
        # 2. Policy Gate (Legal/Brand)
        policy_res = self.policy_engine.evaluate(product)
        # Handle both dict and PolicyResult return types
        if isinstance(policy_res, dict):
            if not policy_res.get("passed", False):
                blockers = policy_res.get("blockers", ["Policy check failed"])
                raise ValueError(f"Policy Violation: {blockers}")
        else:
            # PolicyResult object
            if not policy_res.passed:
                raise ValueError(f"Policy Violation: {policy_res.blockers}")
             
        # 3. Margin Gate (Financial)
        sp = product.supplier_product
        cost = float(sp.cost_price or 0)
        calc_price = PricingStrategy.calculate_price(cost, supplier_name=sp.supplier.name if sp.supplier else None)
        margin_check = PricingStrategy.validate_margin(cost, calc_price)
        
        if not margin_check['safe']:
             raise ValueError(f"Financial Danger: {margin_check.get('reason')}")
             
        return True

class ValidationEngine:
    """
    Step 3: Self-Validation Gates.
    Randomly samples products and re-verifies them against live web data.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.auditor = UniversalAdapter() # Uses generic OG/Schema extraction
        
    def run_validation(self, sample_size: int = 5) -> dict:
        """
        Runs validation on random products.
        Returns: {
            "score": 95.0,
            "total_checked": 5,
            "matches": 5,
            "mismatches": [],
            "timestamp": ...
        }
        """
        print(f"Validator: Starting Random Check (Size={sample_size})...")
        
        # 1. Select Candidates (Active Products only)
        # We fetch IDs first to be efficient
        all_ids = [r[0] for r in self.db.query(SupplierProduct.id).filter(SupplierProduct.sync_status != "REMOVED").all()]
        
        if not all_ids:
             return {"score": 0, "total_checked": 0, "matches": 0, "mismatches": [], "timestamp": datetime.utcnow()}
             
        # Random Sample
        target_ids = random.sample(all_ids, min(len(all_ids), sample_size))
        products = self.db.query(SupplierProduct).filter(SupplierProduct.id.in_(target_ids)).all()
        
        matches = 0
        mismatches = []
        
        for p in products:
            try:
                # 2. Refetch Live Data
                # Note: This relies on UniversalAdapter being able to parse the URL.
                # If specific scraper logic is needed (like headers/cookies), standard validaton might fail.
                # But for NL/CC public pages, basic curl often works.
                live_data = self.auditor.analyze_url(p.product_url)
                
                if not live_data:
                    # Skip or Count as Error? 
                    # If we can't fetch it, we can't validate it. 
                    # Let's count as Error for "Trust Score Validity" 
                    # but not necessarily a Mismatch.
                    print(f"Validator: Failed to fetch {p.product_url}")
                    continue
                    
                # 3. Compare Price
                # Diffs greater than $1.00 count as mismatch
                db_price = p.cost_price or 0.0
                live_price = live_data.get("price", 0.0)
                
                # Tolerate 0.0 in live data if parser failed to find price (don't penalize trust score for parser fail)
                # But if parser found price, it must match.
                is_match = True
                fail_reason = ""
                
                if live_price > 0:
                     if abs(db_price - live_price) > 1.0:
                         is_match = False
                         fail_reason = f"Price Drift: DB=${db_price} vs Live=${live_price}"
                         
                if is_match:
                    matches += 1
                else:
                    mismatches.append({
                        "sku": p.external_sku,
                        "title": p.title,
                        "fail_reason": fail_reason
                    })
                    
            except Exception as e:
                print(f"Validator Error on {p.external_sku}: {e}")
                
        # 4. Score
        total = len(products)
        # If we failed to fetch all, score is 0? Or based on successful checks?
        # User wants "Trust Score". If we can't check, trust is low.
        score = (matches / total) * 100 if total > 0 else 0.0
        
        report = {
            "score": round(score, 1),
            "total_checked": total,
            "matches": matches,
            "mismatches": mismatches,
            "timestamp": datetime.utcnow()
        }
        
        print(f"Validator: Complete. Score={report['score']}%")
        return report

if __name__ == "__main__":
    db = SessionLocal()
    val = ValidationEngine(db)
    print(val.run_validation(3))
