from sqlalchemy.orm import Session
from retail_os.core.database import (
    TradeMeListing, InternalProduct, SupplierProduct, 
    SystemCommand, CommandStatus, Order, Supplier
)
import uuid
import json

class InventoryOperations:
    def __init__(self, session: Session):
        self.session = session

    def apply_pricing_rule(self, supplier_name: str, margin_type: str, value: float):
        """
        Creates bulk UPDATE_PRICE commands for all listings from a supplier.
        margin_type: "PERCENT" of "FIXED"
        """
        query = self.session.query(TradeMeListing)\
            .join(InternalProduct)\
            .join(SupplierProduct)\
            .filter(TradeMeListing.actual_state == "Live")

        if supplier_name != "All Suppliers":
            supplier = self.session.query(Supplier).filter_by(name=supplier_name).first()
            if supplier:
                query = query.filter(SupplierProduct.supplier_id == supplier.id)
            
        listings = query.all()
            
        commands = []
        for listing in listings:
            cost_price = listing.product.supplier_product.cost_price
            
            if not cost_price:
                continue
                
            if margin_type == "Unknown": # Default/Safety
                continue
            elif "Percentage" in margin_type:
                raw_price = cost_price * (1 + (value / 100))
            else: # Fixed
                raw_price = cost_price + value
                
            # Apply Psychological Rounding from Strategy Engine
            from retail_os.strategy.pricing import PricingStrategy
            new_price = PricingStrategy.apply_psychological_rounding(raw_price)
            
            # Simple check to avoid churn
            if abs(new_price - (listing.actual_price or 0)) > 0.01:
                cmd = SystemCommand(
                    id=str(uuid.uuid4()),
                    type="UPDATE_PRICE",
                    payload={"listing_id": listing.tm_listing_id, "new_price": new_price},
                    status=CommandStatus.PENDING,
                    priority=5
                )
                commands.append(cmd)
                
        if commands:
            self.session.add_all(commands)
            self.session.commit()
            
        return len(commands)

    def withdraw_unavailable_items(self, supplier_id: int | None = None):
        """
        Finds all items where SupplierProduct.sync_status == 'REMOVED'
        and queues withdrawal commands if they are currently Live.
        """
        # Find removed supplier products that map to LIVE internal listings
        query = self.session.query(TradeMeListing)\
            .join(InternalProduct)\
            .join(SupplierProduct)\
            .filter(SupplierProduct.sync_status == "REMOVED")\
            .filter(TradeMeListing.actual_state == "Live")
            
        if supplier_id:
            query = query.filter(SupplierProduct.supplier_id == supplier_id)
            
        targets = query.all()
            
        commands = []
        for listing in targets:
            cmd = SystemCommand(
                id=str(uuid.uuid4()),
                type="WITHDRAW_LISTING",
                payload={"listing_id": listing.tm_listing_id, "reason": "Supplier Out of Stock"},
                status=CommandStatus.PENDING,
                priority=10 # High priority
            )
            commands.append(cmd)
            
        if commands:
            self.session.add_all(commands)
            self.session.commit()
            
        return len(commands)

    def update_order_status(self, order_id: int, tracking_number: str, carrier: str):
        """
        Updates local order status and queues an UPDATE_SHIPPING command to Trade Me.
        """
        order = self.session.query(Order).get(order_id)
        if not order:
            return False
            
        order.status = "Shipped"
        order.tracking_reference = tracking_number
        order.carrier = carrier
        
        # Queue command for Trade Me API
        cmd = SystemCommand(
            id=str(uuid.uuid4()),
            type="UPDATE_SHIPPING",
            payload={
                "order_id": order.tm_order_ref, 
                "tracking": tracking_number, 
                "carrier": carrier
            },
            status=CommandStatus.PENDING
        )
        self.session.add(cmd)
        self.session.commit()
        return True

    def analyze_lifecycle(self) -> dict:
        """
        Runs the LifecycleManager on all listings.
        Returns aggregate stats of recommended actions.
        """
        from retail_os.strategy.lifecycle import LifecycleManager
        
        listings = self.session.query(TradeMeListing).filter(TradeMeListing.actual_state != "WITHDRAWN").all()
        
        results = {
            "PROMOTE": 0,
            "DEMOTE": 0,
            "KILL": 0,
            "NONE": 0,
            "details": []
        }
        
        for listing in listings:
            rec = LifecycleManager.evaluate_state(listing)
            action = rec["action"]
            results[action] += 1
            
            if action != "NONE":
                results["details"].append({
                    "id": listing.tm_listing_id,
                    "title": listing.product.title,
                    "current": listing.actual_state,
                    "action": action,
                    "reason": rec["reason"]
                })
                
        return results
