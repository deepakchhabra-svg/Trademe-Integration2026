"""
MISSION 1 VALIDATION SCRIPT
Tests command contract compatibility shim
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus
import uuid

def test_insert_command():
    """Insert a TEST_COMMAND and verify it's in DB"""
    session = SessionLocal()
    try:
        cmd_id = str(uuid.uuid4())
        cmd = SystemCommand(
            id=cmd_id,
            type="TEST_COMMAND",
            payload={"test": "data"},
            status=CommandStatus.PENDING
        )
        session.add(cmd)
        session.commit()
        print(f"[OK] Inserted TEST_COMMAND: {cmd_id}")
        return cmd_id
    finally:
        session.close()

def test_insert_publish_dry_run():
    """Insert a PUBLISH_LISTING command with dry_run=True"""
    session = SessionLocal()
    try:
        cmd_id = str(uuid.uuid4())
        cmd = SystemCommand(
            id=cmd_id,
            type="PUBLISH_LISTING",
            payload={"internal_product_id": 1, "dry_run": True},
            status=CommandStatus.PENDING
        )
        session.add(cmd)
        session.commit()
        print(f"[OK] Inserted PUBLISH_LISTING (dry_run): {cmd_id}")
        return cmd_id
    finally:
        session.close()

def query_commands():
    """Query all SystemCommand rows and print status"""
    session = SessionLocal()
    try:
        commands = session.query(SystemCommand).order_by(SystemCommand.created_at.desc()).limit(10).all()
        print("\n[COMMANDS] Recent Commands:")
        print(f"{'ID':<40} {'Type':<20} {'Status':<20} {'Error':<30}")
        print("-" * 110)
        for cmd in commands:
            cmd_type = getattr(cmd, 'type', None) or getattr(cmd, 'command_type', None) or 'UNKNOWN'
            error = (cmd.last_error or '')[:30]
            print(f"{cmd.id:<40} {cmd_type:<20} {cmd.status.value:<20} {error:<30}")
    finally:
        session.close()

if __name__ == "__main__":
    print("=== MISSION 1 VALIDATION ===\n")
    
    # Insert test commands
    test_cmd_id = test_insert_command()
    publish_cmd_id = test_insert_publish_dry_run()
    
    # Query and display
    query_commands()
    
    print("\n[OK] Validation script complete. Now run worker to process these commands.")
    print("   Command: python retail_os/trademe/worker.py")
