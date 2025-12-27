from dataclasses import dataclass, field
from typing import List, Optional
from retail_os.core.database import InternalProduct

@dataclass
class PolicyResult:
    passed: bool
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

from retail_os.core.database import SessionLocal
from retail_os.core.trust import TrustEngine

class PolicyEngine:
    """
    The Strategy Pillar's Gatekeeper.
    Decides if a product is allowed to go live.
    Ref: Master Requirements Section 4, 8.
    """
    
    BANNED_PHRASES = [
        "no warranty",
        "as is",
        "contact us",
        "call for price",
        "auction",
        "make an offer"
    ]

    TRUSTED_SUPPLIERS = ["ONECHEQ", "NOEL LEEMING", "NOEL_LEEMING", "CASH CONVERTERS", "CASH_CONVERTERS"]
    
    def evaluate(self, product: InternalProduct) -> dict:
        """
        Checks if a product passes policy rules.
        Returns: {"passed": bool, "blockers": []}
        """
        blockers = []
        warnings = []
        
        # TRUSTED SUPPLIER OVERRIDE
        sp = product.supplier_product
        if sp and sp.supplier:
            supplier_name = sp.supplier.name.upper()
            if any(trusted in supplier_name for trusted in self.TRUSTED_SUPPLIERS):
                # Trusted supplier - skip all policy checks
                return {"passed": True, "blockers": []}
        
        # Original check for missing supplier data
        if not sp:
            return {"passed": False, "blockers": ["System Error: No Supplier Data"]}

        # 1. Price Strategy (Section 4: Price <= 0 is hard failure)
        price = sp.cost_price or 0.0
        if price <= 0:
            blockers.append("Zero Cost Price")
            
        # 2. Image Handling (Section 7: No Shortcuts)
        # We check raw URLs here. Worker validates reachability.
        if not sp.images or not isinstance(sp.images, list) or len(sp.images) == 0:
            blockers.append("Missing Images")
            
        # 3. Description & SEO (Section 8)
        desc = sp.description or ""
        desc_lower = desc.lower()
        
        if len(desc) < 50:
            blockers.append("Description too short (<50 chars)")
            
        for phrase in self.BANNED_PHRASES:
            if phrase in desc_lower:
                blockers.append(f"Contains Banned Phrase: '{phrase}'")

        # 4. Stock Safety (Implied)
        if (sp.stock_level or 0) <= 0:
            # Maybe warning if backorder allowed, but let's block for now to be safe
            blockers.append("Out of Stock")

        # 5. Trust Gate (Phase C)
        # We must instantiate a temporary session or pass one in.
        # For now, we create a short-lived session to check trust.
        # This is slightly inefficient but safe.
        db = SessionLocal()
        try:
            trust_engine = TrustEngine(db)
            if not trust_engine.is_trusted(sp.supplier_id):
                 score = trust_engine.get_trust_score(sp.supplier_id)
                 blockers.append(f"Untrusted Supplier (Score {score:.1f}% < 95%)")
        finally:
            db.close()

        # Result
        return PolicyResult(
            passed=(len(blockers) == 0),
            blockers=blockers,
            warnings=warnings
        )
