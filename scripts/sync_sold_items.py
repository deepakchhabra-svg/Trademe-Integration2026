"""
Sync Sold Items from Trade Me
Fetches sold orders and populates Order table for fulfillment tracking
"""

import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, Order, TradeMeListing
from retail_os.trademe.api import TradeMeAPI
from datetime import datetime


class SoldItemSyncer:
    """
    Backward-compatible class wrapper for worker.py integration.
    Wraps the sync_sold_items() function.
    """
    def __init__(self):
        self.api = TradeMeAPI()
    
    def sync_recent_sales(self) -> int:
        """Returns the number of new orders created."""
        return sync_sold_items_internal(self.api)


def sync_sold_items_internal(api: TradeMeAPI = None) -> int:
    """
    Fetch sold items from Trade Me and create Order records.
    Returns: number of new orders created.
    """
    print("🔄 Syncing Sold Items from Trade Me...")
    
    if api is None:
        api = TradeMeAPI()
    session = SessionLocal()
    
    new_orders = 0
    try:
        # Get sold items from Trade Me
        sold_items = api.get_sold_items()
        
        print(f"Found {len(sold_items)} sold items")
        
        updated_orders = 0
        
        for item in sold_items:
            # Extract data from Trade Me response
            tm_listing_id = str(item.get("ListingId"))
            purchase_id = str(item.get("PurchaseId"))  # Use as order reference
            
            # Find our listing
            listing = session.query(TradeMeListing).filter_by(tm_listing_id=tm_listing_id).first()
            
            if not listing:
                print(f"  ⚠️  Listing {tm_listing_id} not found in our database")
                continue
            
            # Check if order already exists
            order = session.query(Order).filter_by(tm_order_ref=purchase_id).first()
            
            if not order:
                # Create new order
                order = Order(
                    tm_order_ref=purchase_id,
                    tm_listing_id=listing.id,
                    sold_price=item.get("Price", 0),
                    sold_date=datetime.fromisoformat(item.get("SoldDate").replace("Z", "+00:00")) if item.get("SoldDate") else datetime.utcnow(),
                    buyer_name=item.get("Buyer", {}).get("Nickname", "Unknown"),
                    buyer_email=item.get("Buyer", {}).get("Email"),
                    order_status="CONFIRMED",
                    payment_status="PAID" if item.get("PaymentStatus") == "Paid" else "PENDING",
                    fulfillment_status="PENDING"
                )
                session.add(order)
                new_orders += 1
                print(f"  ✅ New order: {purchase_id} for listing {tm_listing_id}")
            else:
                # Update existing order
                order.payment_status = "PAID" if item.get("PaymentStatus") == "Paid" else "PENDING"
                order.updated_at = datetime.utcnow()
                updated_orders += 1
                print(f"  🔄 Updated order: {purchase_id}")
        
        session.commit()
        print(f"\n✅ Sync Complete: {new_orders} new orders, {updated_orders} updated")
        
        # Export to CSV for fulfillment
        export_orders_to_csv(session)
        
    except Exception as e:
        print(f"❌ Error syncing sold items: {e}")
        session.rollback()
    finally:
        session.close()
    
    return new_orders


def sync_sold_items():
    """Convenience wrapper for CLI usage."""
    return sync_sold_items_internal()

def export_orders_to_csv(session):
    """
    Export pending orders to CSV for fulfillment team
    """
    import csv
    from pathlib import Path
    
    # Get all pending fulfillment orders
    orders = session.query(Order).filter_by(fulfillment_status="PENDING").all()
    
    if not orders:
        print("No pending orders to export")
        return
    
    # Create export directory
    export_dir = Path("data/exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Export to CSV
    csv_path = export_dir / f"pending_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Order ID", "Trade Me Ref", "Listing ID", "Buyer Name", 
            "Buyer Email", "Sold Price", "Sold Date", "Shipping Address",
            "Payment Status", "Fulfillment Status"
        ])
        
        for order in orders:
            writer.writerow([
                order.id,
                order.tm_order_ref,
                order.listing.tm_listing_id if order.listing else "N/A",
                order.buyer_name,
                order.buyer_email,
                f"${order.sold_price:.2f}" if order.sold_price else "N/A",
                order.sold_date.strftime('%Y-%m-%d %H:%M') if order.sold_date else "N/A",
                order.shipping_address or "N/A",
                order.payment_status,
                order.fulfillment_status
            ])
    
    print(f"📄 Exported {len(orders)} pending orders to: {csv_path}")

if __name__ == "__main__":
    sync_sold_items()
