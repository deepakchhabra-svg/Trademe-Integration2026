import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from retail_os.core.database import SessionLocal, SystemCommand

# Check command payload
session = SessionLocal()
cmd = session.query(SystemCommand).filter_by(id='c55c1831-307e-4afa-9bc0-9b85c49e9cf9').first()
if cmd:
    print(f"Command ID: {cmd.id}")
    print(f"Type: {cmd.type}")
    print(f"Payload: {cmd.payload}")
    print(f"Payload type: {type(cmd.payload)}")
    print(f"dry_run in payload: {'dry_run' in cmd.payload if cmd.payload else 'NO PAYLOAD'}")
    if cmd.payload:
        print(f"dry_run value: {cmd.payload.get('dry_run')}")
else:
    print("Command not found")

session.close()
