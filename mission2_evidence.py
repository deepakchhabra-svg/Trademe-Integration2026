import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from retail_os.core.database import SessionLocal, SystemCommand, TradeMeListing

# Final validation
session = SessionLocal()

# Check command
cmd = session.query(SystemCommand).filter_by(id='df101ba9-f513-4760-b4f4-da0158208d6f').first()
print("=== RECENT COMMANDS ===")
print(f"ID: {cmd.id[:12]}...")
print(f"Type: {cmd.type}")
print(f"Status: {cmd.status.value}")
print(f"Error: {cmd.last_error if cmd.last_error else 'None'}")
print(f"Created: {cmd.created_at}")

# Check Vault3
listing = session.query(TradeMeListing).filter_by(tm_listing_id='DRYRUN-df101ba9-f513-4760-b4f4-da0158208d6f').first()
print("\n=== VAULT3 LISTING ===")
if listing:
    print(f"tm_listing_id: {listing.tm_listing_id}")
    print(f"actual_state: {listing.actual_state}")
    print(f"internal_product_id: {listing.internal_product_id}")
    print(f"desired_price: ${listing.desired_price}")
else:
    print("NOT FOUND")

session.close()

# Show logs
print("\n=== WORKER LOG (Last 10 lines) ===")
with open('logs/worker.log', 'r') as f:
    lines = f.readlines()
    for line in lines[-10:]:
        print(line.strip())
