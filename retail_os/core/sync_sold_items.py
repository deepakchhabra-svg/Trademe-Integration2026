import sys
import os
import time
from datetime import datetime
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, TradeMeListing, Order, ListingState, InternalProduct, SupplierProduct
from retail_os.trademe.api import TradeMeAPI

class SoldItemSyncer:
    """
    Polls Trade Me for recent sales.
    Updates local inventory and creates Order records.
    Ref: 'Robot Heartbeat' - Sold Item Inventory Sync.
    """
    def __init__(self):
        self.api = TradeMeAPI()
        
    def sync_recent_sales(self):
        print(f"[{datetime.now()}] SoldSync: Checking for new sales...")
        session = SessionLocal()
        try:
            # 1. Fetch Sold Items (Last 24h usually, API paged)
            # Using mock or real API call logic
            sold_items = self.api.get_sold_items(days=1)
            
            new_orders = 0
            
            for sale in sold_items:
                tm_order_id = str(sale.get("OrderId"))
                tm_listing_id = str(sale.get("ListingId"))
                
                # Check duplication
                exists = session.query(Order).filter_by(tm_order_ref=tm_order_id).first()
                if exists:
                    continue
                    
                print(f"SoldSync: New Sale Detected! Order {tm_order_id} (Listing {tm_listing_id})")
                
                # 2. Update Listing Status
                listing = session.query(TradeMeListing).filter_by(tm_listing_id=tm_listing_id).first()
                if listing:
                    listing.actual_state = "Sold"
                    listing.is_locked = True # Lock generic updates
                    # Decrement Stock?
                    if listing.product and listing.product.supplier_product:
                        listing.product.supplier_product.stock_level = max(0, listing.product.supplier_product.stock_level - 1)
                        print(f"          -> Stock decremented for {listing.product.title}")
                
                # 3. Create Order
                order = Order(
                    tm_order_ref=tm_order_id,
                    tm_listing_id=listing.id if listing else None,
                    sold_price=sale.get("Price", 0.0),
                    sold_date=datetime.utcnow(), # Parse from API in real impl
                    buyer_name=sale.get("Buyer", {}).get("Nickname"),
                    order_status="PENDING"
                )
                session.add(order)
                new_orders += 1
                
            session.commit()
            return new_orders
            
        except Exception as e:
            print(f"SoldSync Error: {e}")
            session.rollback()
            return 0
        finally:
            session.close()

if __name__ == "__main__":
    syncer = SoldItemSyncer()
    while True:
        syncer.sync_recent_sales()
        time.sleep(300) # 5 minutes
