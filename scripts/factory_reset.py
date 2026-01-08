import sys
import os
import argparse
from sqlalchemy import text
from typing import List

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retail_os.core.database import (
    SessionLocal,
    TradeMeListing,
    InternalProduct,
    SupplierProduct,
    SystemCommand,
    CommandProgress,
    JobStatus,
    ListingDraft,
    ResourceLock,
    PhotoHash,
    Order,
    ListingMetricSnapshot,
    PriceHistory
)

def get_counts(session) -> dict:
    return {
        "SupplierProducts": session.query(SupplierProduct).count(),
        "InternalProducts": session.query(InternalProduct).count(),
        "TradeMeListings": session.query(TradeMeListing).count(),
        "SystemCommands": session.query(SystemCommand).count(),
        "Orders": session.query(Order).count(),
    }

def soft_reset(session):
    print("--- SOFT RESET ---")
    print("Strategy: Keep LIVE listings and their dependencies. Delete everything else.\n")

    # 1. Identify Live Listings
    live_listings = session.query(TradeMeListing).filter(TradeMeListing.actual_state == "Live").all()
    
    keep_listing_ids = {l.id for l in live_listings}
    keep_internal_ids = {l.internal_product_id for l in live_listings if l.internal_product_id}
    
    keep_supplier_ids = set()
    if keep_internal_ids:
        # Get SupplierProduct IDs linked to these InternalProducts
        linked_sps = session.query(InternalProduct.primary_supplier_product_id).filter(
            InternalProduct.id.in_(keep_internal_ids)
        ).all()
        keep_supplier_ids = {r[0] for r in linked_sps if r[0]}

    print(f"PRESERVING: {len(keep_listing_ids)} Live Listings, {len(keep_internal_ids)} Internal Products, {len(keep_supplier_ids)} Supplier Products.")

    # 2. Delete Queue / Ephemeral Data (Always safe to wipe)
    print("Deleting Queue and Logs...", end=" ")
    session.query(CommandProgress).delete()
    session.query(JobStatus).delete()
    session.query(ListingDraft).delete()
    session.query(ResourceLock).delete()
    session.query(SystemCommand).delete() # Cascades usually, but explicit is safer
    print("Done.")

    # 3. Delete Listings
    print("Deleting Non-Live Listings...", end=" ")
    if keep_listing_ids:
        session.query(PriceHistory).filter(~PriceHistory.listing_id.in_(keep_listing_ids)).delete(synchronize_session=False)
        session.query(ListingMetricSnapshot).filter(~ListingMetricSnapshot.listing_id.in_(keep_listing_ids)).delete(synchronize_session=False)
        session.query(TradeMeListing).filter(~TradeMeListing.id.in_(keep_listing_ids)).delete(synchronize_session=False)
    else:
        session.query(PriceHistory).delete()
        session.query(ListingMetricSnapshot).delete()
        session.query(TradeMeListing).delete()
    print("Done.")

    # 4. Delete Internal Products
    print("Deleting Unlinked Internal Products...", end=" ")
    if keep_internal_ids:
        session.query(InternalProduct).filter(~InternalProduct.id.in_(keep_internal_ids)).delete(synchronize_session=False)
    else:
        session.query(InternalProduct).delete()
    print("Done.")

    # 5. Delete Supplier Products
    print("Deleting Unlinked Supplier Products...", end=" ")
    if keep_supplier_ids:
        session.query(SupplierProduct).filter(~SupplierProduct.id.in_(keep_supplier_ids)).delete(synchronize_session=False)
    else:
        session.query(SupplierProduct).delete()
    print("Done.")

def hard_reset(session):
    print("--- HARD RESET ---")
    print("Strategy: SCORCHED EARTH. Delete ALL Inventory. Preserve Orders (Unlinked).\n")

    # 1. Pre-flight Check
    live_count = session.query(TradeMeListing).filter(TradeMeListing.actual_state == "Live").count()
    if live_count > 0:
        raise Exception(f"ABORTING: Found {live_count} LIVE listings. You must withdraw them first or use Soft Reset.")

    # 2. Financial Safety - Detach Orders
    print("Detaching Orders from Listings...", end=" ")
    # SQLite fallback for bulk update if needed, but SQLAlchemy update() works fine usually
    session.query(Order).update({Order.tm_listing_id: None}, synchronize_session=False)
    print("Done.")

    # 3. Delete Everything
    print("Deleting ALL Listings, Products, and Queue...", end=" ")
    
    # Bottom-up deletion to avoid FK issues (though cascades might handle it, this is explicit)
    session.query(PriceHistory).delete()
    session.query(ListingMetricSnapshot).delete()
    session.query(TradeMeListing).delete()
    
    session.query(InternalProduct).delete()
    session.query(SupplierProduct).delete()
    
    session.query(CommandProgress).delete()
    session.query(JobStatus).delete()
    session.query(ListingDraft).delete()
    session.query(ResourceLock).delete()
    session.query(SystemCommand).delete()
    session.query(PhotoHash).delete()
    print("Done.")

def main():
    parser = argparse.ArgumentParser(description="Factory Reset RetailOS Data")
    parser.add_argument("--hard", action="store_true", help="Delete EVERYTHING including listings/inventory mapping (Refuses if Live items exist)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation (Use with caution)")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        current = get_counts(session)
        print("CURRENT STATE:")
        for k, v in current.items():
            print(f"  {k}: {v}")
        print("")

        if args.hard:
            required_input = "DELETE HARD RESET"
            mode_fn = hard_reset
        else:
            required_input = "DELETE"
            mode_fn = soft_reset

        if not args.force:
            print(f"To confirm, type '{required_input}' (without quotes):")
            confirm = input("> ").strip()
            if confirm != required_input:
                print("Confirmation failed. Aborting.")
                return
        
        mode_fn(session)
        
        session.commit()
        print("\nSUCCESS: Factory Reset Complete.")
        
        # Vacuum if sqlite
        if "sqlite" in str(session.bind.url):
            print("Vacuuming SQLite database...")
            session.execute(text("VACUUM"))
            
        final = get_counts(session)
        print("\nFINAL STATE:")
        for k, v in final.items():
            print(f"  {k}: {v}")

    except Exception as e:
        session.rollback()
        print(f"\nERROR: {e}")
        print("Rolled back all changes.")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()
