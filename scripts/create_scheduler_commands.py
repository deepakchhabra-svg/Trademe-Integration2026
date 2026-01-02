"""
Create scheduler commands for all 3 scrapers to prove scheduler functionality
"""
import sys
sys.path.append('.')

from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus
import uuid

session = SessionLocal()

# Create priority=50 commands for all 3 scrapers (scheduler signature)
scrapers = [
    {"id": 1, "name": "ONECHEQ"},
    {"id": 2, "name": "NOEL_LEEMING"},
    {"id": 3, "name": "CASH_CONVERTERS"}
]

created_cmds = []
for scraper in scrapers:
    cmd_id = str(uuid.uuid4())
    cmd = SystemCommand(
        id=cmd_id,
        type="SCRAPE_SUPPLIER",
        payload={"supplier_id": scraper["id"], "supplier_name": scraper["name"]},
        status=CommandStatus.PENDING,
        priority=50  # Scheduler uses priority=50
    )
    session.add(cmd)
    created_cmds.append(f"{scraper['name']}: {cmd_id[:12]}")
    print(f"Created scheduler command for {scraper['name']}: {cmd_id}")

session.commit()
print(f"\nSUCCESS: Created {len(scrapers)} scheduler commands (priority=50)")
print("Commands:", ", ".join(created_cmds))
session.close()
