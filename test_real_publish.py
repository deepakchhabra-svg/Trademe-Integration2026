
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus, InternalProduct, TradeMeListing
from retail_os.trademe.worker import CommandWorker

def perform_real_listing():
    print("=== EXECUTING REAL LISTING TEST ===\n")
    session = SessionLocal()
    try:
        # 1. Find the product
        target_sku = "OC-2000-pc-ancient-map"
        prod = session.query(InternalProduct).filter(InternalProduct.sku == target_sku).first()
        if not prod:
            print(f"Error: Product {target_sku} not found.")
            return
            
        print(f"Product Found: {prod.title} (ID: {prod.id})")
        
        # 2. Enqueue REAL Publish Command
        cmd_id = str(uuid.uuid4())
        cmd = SystemCommand(
            id=cmd_id,
            type="PUBLISH_LISTING",
            payload={"internal_product_id": prod.id, "dry_run": False},
            status=CommandStatus.PENDING,
            priority=100
        )
        session.add(cmd)
        session.commit()
        print(f"Command Enqueued: {cmd_id}")
        
        # 3. Process with Worker
        worker = CommandWorker()
        print("\nWorker: Starting processing cycle...")
        # We manually call process_next_command so we don't end up in an infinite loop
        # The command we just added is the only one in the DB (based on check_db_stats)
        worker.process_next_command()
        
        # 4. Verify Result
        session.expire_all() # Refresh from DB
        final_cmd = session.query(SystemCommand).get(cmd_id)
        print(f"\nCommand Status: {final_cmd.status}")
        if final_cmd.last_error:
            print(f"Error: {final_cmd.last_error}")
            
        # Check for listing record
        listing = session.query(TradeMeListing).filter(TradeMeListing.internal_product_id == prod.id).order_by(TradeMeListing.id.desc()).first()
        if listing and listing.tm_listing_id and not listing.tm_listing_id.startswith("DRYRUN"):
            print(f"\n[SUCCESS] REAL LISTING CREATED!")
            print(f"Trade Me Listing ID: {listing.tm_listing_id}")
            print(f"View it at: https://www.trademe.co.nz/Browse/Listing.aspx?id={listing.tm_listing_id}")
        else:
            print("\n[FAILURE] Real listing not found in database.")
            
    finally:
        session.close()

if __name__ == "__main__":
    perform_real_listing()
