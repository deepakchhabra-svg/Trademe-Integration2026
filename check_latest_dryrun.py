import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from retail_os.core.database import SessionLocal, SystemCommand, TradeMeListing

# Get latest dry run command
session = SessionLocal()
cmd = session.query(SystemCommand).filter(
    SystemCommand.type == 'PUBLISH_LISTING'
).order_by(SystemCommand.created_at.desc()).first()

if cmd:
    print(f"=== LATEST COMMAND ===")
    print(f"ID: {cmd.id[:12]}...")
    print(f"Status: {cmd.status.value}")
    print(f"Payload: {cmd.payload}")
    print(f"Error: {cmd.last_error if cmd.last_error else 'None'}")
    
    # Check if dry run listing exists
    if cmd.payload and cmd.payload.get('dry_run'):
        listing = session.query(TradeMeListing).filter_by(
            tm_listing_id=f"DRYRUN-{cmd.id}"
        ).first()
        
        if listing:
            print(f"\n=== VAULT3 LISTING ===")
            print(f"tm_listing_id: {listing.tm_listing_id}")
            print(f"payload_hash: {listing.payload_hash[:16] if listing.payload_hash else 'None'}...")
            print(f"Has payload_snapshot: {listing.payload_snapshot is not None}")
            if listing.payload_snapshot:
                import json
                payload = json.loads(listing.payload_snapshot)
                print(f"Payload keys: {list(payload.keys())}")
        else:
            print("\n=== NO VAULT3 LISTING FOUND ===")

session.close()
