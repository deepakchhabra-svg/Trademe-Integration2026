from datetime import datetime
from sqlalchemy.orm import Session
from retail_os.core.database import SessionLocal, SupplierProduct, TradeMeListing, SystemCommand, CommandStatus, AuditLog
import uuid

class ReconciliationEngine:
    """
    Handles the 'Missing Item' lifecycle.
    Ref: Master Requirements Section 6 (Supplier URL Presence Logic).
    """
    
    def __init__(self, db: Session):
        self.db = db

    def process_orphans(self, supplier_id: int, current_run_timestamp: datetime):
        """
        Detects items not seen in the current scrape run.
        """
        print(f"Reconciliation: Checking items for Supplier {supplier_id}...")
        
        # 1. Find items belonging to this supplier
        # We check checks:
        # A. Last Scraped < Run Start (Implies it wasn't touched this run)
        # B. Not already Removed
        
        orphans = self.db.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.last_scraped_at < current_run_timestamp,
            SupplierProduct.sync_status != "REMOVED"
        ).all()
        
        updates = 0
        withdrawals = 0
        
        for sp in orphans:
            old_status = sp.sync_status or "PRESENT"
            
            if old_status == "PRESENT":
                # First Miss -> MISSING_ONCE
                sp.sync_status = "MISSING_ONCE"
                self._log_change(sp, "STATUS_CHANGE", "PRESENT", "MISSING_ONCE")
                updates += 1
                
            elif old_status == "MISSING_ONCE":
                # Second Miss -> REMOVED (Confirmed)
                sp.sync_status = "REMOVED"
                self._log_change(sp, "STATUS_CHANGE", "MISSING_ONCE", "REMOVED")
                
                # Trigger Withdraw Logic
                if self._trigger_withdraw(sp):
                    withdrawals += 1
                updates += 1
                
        # 2. Check for Reappearance (Healed items)
        # Items seen this run BUT marked as MISSING/REMOVED
        healed = self.db.query(SupplierProduct).filter(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.last_scraped_at >= current_run_timestamp,
            SupplierProduct.sync_status.in_(["MISSING_ONCE", "REMOVED"])
        ).all()
        
        for sp in healed:
            old = sp.sync_status
            sp.sync_status = "PRESENT"
            self._log_change(sp, "STATUS_CHANGE", old, "PRESENT")
            updates += 1

        self.db.commit()
        print(f"Reconciliation Complete: {updates} Status Updates, {withdrawals} Withdrawals Triggered.")

    def _trigger_withdraw(self, sp: SupplierProduct) -> bool:
        """
        If this product is live on Trade Me, withdraw it.
        """
        # Find linked Internal Product -> TradeMeListing
        if not sp.internal_product:
            return False
            
        for listing in sp.internal_product[0].listings:
            if listing.actual_state == "Live":
                # Create Command
                cmd_id = str(uuid.uuid4())
                payload = {
                    "reason": "Supplier Item Removed (Missing Confirmed)",
                    "tm_listing_id": listing.tm_listing_id
                }
                cmd = SystemCommand(
                    id=cmd_id,
                    type="WITHDRAW_LISTING", # Handler needs to support this type
                    payload=payload,
                    status=CommandStatus.PENDING
                )
                self.db.add(cmd)
                print(f"   -> AUTO-WITHDRAW Queued for {listing.tm_listing_id}")
                return True
        return False

    def _log_change(self, sp, action, old, new):
        log = AuditLog(
            entity_type="SupplierProduct",
            entity_id=str(sp.id),
            action=action,
            old_value=old,
            new_value=new,
            user="ReconciliationEngine",
            timestamp=datetime.utcnow()
        )
        self.db.add(log)
