import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from retail_os.core.database import SessionLocal, SystemCommand, TradeMeListing

# Check NEW command status
session = SessionLocal()
cmd = session.query(SystemCommand).filter_by(id='c55c1831-307e-4afa-9bc0-9b85c49e9cf9').first()
print(f"Command Status: {cmd.status.value if cmd else 'NOT FOUND'}")
print(f"Last Error: {cmd.last_error if cmd and cmd.last_error else 'None'}")

# Check Vault3 listing
listing = session.query(TradeMeListing).filter(TradeMeListing.tm_listing_id.like('DRYRUN-%')).first()
print(f"\nVault3 Listing found: {listing is not None}")
if listing:
    print(f"tm_listing_id: {listing.tm_listing_id}")
    print(f"actual_state: {listing.actual_state}")
    print(f"internal_product_id: {listing.internal_product_id}")

session.close()
