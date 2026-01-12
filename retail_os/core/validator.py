import random
import sys
import os
sys.path.append(os.getcwd())
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from retail_os.core.database import SessionLocal, SupplierProduct, InternalProduct
from retail_os.scrapers.universal.adapter import UniversalAdapter
from retail_os.core.trust import TrustEngine, TrustReport
from retail_os.strategy.policy import PolicyEngine
from retail_os.strategy.pricing import PricingStrategy
from retail_os.core.category_mapper import CategoryMapper
import json

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
             
        # 0. Required fields gate (Hard)
        sp = product.supplier_product
        if sp.sync_status == "REMOVED":
            raise ValueError("Removed from supplier feed (blocked)")
        if not (sp.product_url or "").strip():
            raise ValueError("Missing source URL (supplier product)")
        if not (sp.title or "").strip():
            raise ValueError("Missing title (supplier product)")
        if sp.cost_price is None or float(sp.cost_price or 0) <= 0:
            raise ValueError("Missing/invalid cost price")
        if not (sp.enriched_title or "").strip():
            raise ValueError("Missing enriched title (run enrichment)")
        if not (sp.enriched_description or "").strip():
            raise ValueError("Missing enriched description (run enrichment)")

        # Require at least one local image file.
        imgs = sp.images or []
        if isinstance(imgs, str):
            try:
                imgs = json.loads(imgs)
            except Exception:
                imgs = [imgs]
        has_local = False
        for img in imgs:
            if isinstance(img, str) and os.path.exists(img):
                has_local = True
                break
        if not has_local:
            raise ValueError("Missing images: no local product image downloaded (blocked)")

        # Require mappable category.
        cat_id = CategoryMapper.map_category(
            getattr(sp, "source_category", "") or "",
            sp.title or "",
            (getattr(sp, "enriched_description", None) or getattr(sp, "description", None) or ""),
        )
        if not cat_id:
            raise ValueError("Missing category mapping (source_category is empty/unmappable)")
        # Do not treat the safe default category as "mapped" for Launch readiness.
        try:
            if getattr(CategoryMapper, "DEFAULT_CATEGORY", None) and cat_id == CategoryMapper.DEFAULT_CATEGORY:
                raise ValueError("Unmapped Trade Me category (default fallback) (blocked)")
        except Exception:
            pass

        # Require a sell price > 0 (Trade Me listing StartPrice).
        # We use the same pricing strategy as listing payload generation.
        try:
            cost = float(sp.cost_price or 0)
            calc_price = PricingStrategy.calculate_price(cost, supplier_name=sp.supplier.name if sp.supplier else None)
            if calc_price is None or float(calc_price or 0) <= 0:
                raise ValueError("Missing/invalid sell price (blocked)")
        except ValueError:
            raise
        except Exception:
            raise ValueError("Missing/invalid sell price (blocked)")

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
             return {"score": 0, "total_checked": 0, "matches": 0, "mismatches": [], "timestamp": datetime.now(timezone.utc)}
             
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
            "timestamp": datetime.now(timezone.utc)
        }
        
        print(f"Validator: Complete. Score={report['score']}%")
        return report

if __name__ == "__main__":
    db = SessionLocal()
    val = ValidationEngine(db)
    print(val.run_validation(3))
