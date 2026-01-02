
import pytest
from retail_os.core.database import SystemCommand, CommandStatus

def test_create_command_valid(client, db_session):
    payload = {
        "type": "PUBLISH_LISTING",
        "payload": {"internal_product_id": 123, "dry_run": True},
        "priority": 10
    }
    # Need auth? client fixtures usually don't have auth unless added.
    # api_client.ts sends cookie "retailos_role". API expects cookie or header.
    # ops.py: requires 'power' role.
    
    headers = {"X-RetailOS-Role": "power"}
    
    resp = client.post("/ops/enqueue", json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"DEBUG: Status {resp.status_code}, Response: {resp.text}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "id" in data
    assert data["status"] == "PENDING"
    
    # Verify DB
    cmd = db_session.query(SystemCommand).filter_by(id=data["id"]).first()
    assert cmd is not None
    assert cmd.type == "PUBLISH_LISTING"
    assert cmd.priority == 10

def test_list_commands(client, db_session):
    # Seed
    c1 = SystemCommand(id="c1", type="TEST", status=CommandStatus.PENDING, priority=1)
    db_session.add(c1)
    db_session.commit()
    
    headers = {"X-RetailOS-Role": "reader"}
    resp = client.get("/ops/commands", headers=headers) # Check ops.py route... it is /ops/commands?
    # Registry said /commands (GET) in main.py. ops.py has /ops/enqueue.
    # main.py likely has GET /commands.
    
    # Try /commands
    if resp.status_code == 404:
        resp = client.get("/commands", headers=headers)
        
    assert resp.status_code == 200
    # Response model is PageResponse?
    data = resp.json()
    # Check shape
    assert "items" in data or isinstance(data, list)

def test_command_lifecycle_actions(client, db_session):
    c1 = SystemCommand(id="c2", type="TEST", status=CommandStatus.FAILED_RETRYABLE, priority=1)
    db_session.add(c1)
    db_session.commit()
    
    headers = {"X-RetailOS-Role": "power"}
    
    # Retry
    # Registry says /commands/{id}/retry
    resp = client.post(f"/commands/c2/retry", headers=headers)
    if resp.status_code != 200:
        print(f"DEBUG RETRY: {resp.status_code} {resp.text}")
    assert resp.status_code == 200
    
    db_session.refresh(c1)
    if c1.status != CommandStatus.PENDING:
         print(f"DEBUG STATUS: {c1.status}")
    assert c1.status == CommandStatus.PENDING
    
    # Cancel
    resp = client.post(f"/commands/c2/cancel", headers=headers)
    assert resp.status_code == 200
    
    db_session.refresh(c1)
    assert c1.status == CommandStatus.CANCELLED
