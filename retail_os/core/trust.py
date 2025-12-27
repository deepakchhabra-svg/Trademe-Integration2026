from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func
from retail_os.core.database import SessionLocal, AuditLog, SupplierProduct, InternalProduct
from retail_os.quality.rebuilder import ContentRebuilder

@dataclass
class TrustReport:
    score: float
    is_trusted: bool
    blockers: List[str]
    breakdown: Dict[str, str]

class TrustEngine:
    """
    Calculates Trust Scores and enforces Gates.
    Ref: Phase C (Visual Validation).
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.rebuilder = ContentRebuilder()
        
    def get_trust_score(self, supplier_id: int) -> float:
        """
        Calculates a 0-100 score based on recent history (Supplier Level).
        """
        # 1. Total Validation Checks in last 24h
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        fails = self.db.query(AuditLog).filter(
            AuditLog.action == "VALIDATION_FAIL",
            AuditLog.timestamp > cutoff
        ).count()
        
        # Simple penalty model
        penalty = fails * 20.0
        score = max(0.0, 100.0 - penalty)
        
        return score

    def get_product_trust_report(self, product: InternalProduct) -> TrustReport:
        """
        Detailed trust analysis for a single product.
        Enforces Phase C Hard Reset Rules.
        """
        score = 100.0
        blockers = []
        breakdown = {}
        
        # 1. Content Rebuilder Check (Hard Gate)
        # We simulate the rebuild to see if it triggers blockers
        sp = product.supplier_product
        if not sp:
            return TrustReport(0.0, False, ["Missing Supplier Data"], {})

        # Rebuild Attempt
        rebuild_result = self.rebuilder.rebuild(
            title=sp.title,
            specs=sp.specs or {},
            condition=sp.condition or "Used",
            warranty_months=0 # Default for check
        )
        
        if not rebuild_result.is_clean:
            score -= 100.0 # Instant Fail
            blockers.extend(rebuild_result.blockers)
            breakdown["Content"] = "FAILED (Prohibited Patterns Found)"
        else:
            breakdown["Content"] = "PASS (Reconstructed & Clean)"
        
        # 1.5 MISSING SPEC PENALTY
        # If item has zero technical specifications, drop to 60%
        spec_count = len(sp.specs or {})
        if spec_count == 0:
            score = 60.0  # Hard cap at 60%
            blockers.append("Missing Technical Specifications")
            breakdown["Specifications"] = f"PENALTY (0 specs found - Score capped at 60%)"
        else:
            breakdown["Specifications"] = f"PASS ({spec_count} specs found)"
            
        # 2. Image Check (Hard Gate with Physical Verification + Placeholder Block)
        if not sp.images or len(sp.images) == 0:
            score = 0.0
            blockers.append("No Images Available")
            breakdown["Images"] = "FAILED (None)"
        else:
            # Check for placeholder fraud
            img_path = sp.images[0]
            if img_path is None or 'placehold.co' in str(img_path):
                score = 0.0
                blockers.append("Placeholder Image Detected")
                breakdown["Images"] = "FAILED (Placeholder)"
            else:
                # Physical verification for local images
                import os
                physical_verified = False
                if os.path.exists(img_path):
                    physical_verified = True
                
                if not physical_verified and any('data/media' in str(img) for img in sp.images):
                    # Local path expected but file missing
                    score = 0.0
                    blockers.append("Image File Missing from Disk")
                    breakdown["Images"] = "FAILED (File not found)"
                else:
                    breakdown["Images"] = f"PASS ({len(sp.images)} available)"

        # 3. Price Sity (Soft Gate)
        # Just check it's not zero
        if sp.cost_price is None or sp.cost_price <= 0:
             score -= 100.0
             blockers.append("Invalid Cost Price")
             breakdown["Pricing"] = "FAILED (Zero/Null)"
        else:
             breakdown["Pricing"] = "PASS"
             
        final_score = max(0.0, score)
        return TrustReport(
            score=final_score,
            is_trusted=final_score >= 95.0,
            blockers=blockers,
            breakdown=breakdown
        )
        
    def is_trusted(self, supplier_id: int) -> bool:
        """
        Returns True if score >= 95%.
        """
        return self.get_trust_score(supplier_id) >= 95.0
        
    def get_trust_label(self, supplier_id: int) -> str:
        score = self.get_trust_score(supplier_id)
        if score >= 95:
            return "TRUSTED"
        elif score >= 80:
            return "WARNING"
        else:
            return "BLOCKED"
