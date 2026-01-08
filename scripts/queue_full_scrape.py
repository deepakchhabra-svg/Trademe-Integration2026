"""
Queue full site scraping and enrichment for both suppliers.

Usage:
    python scripts/queue_full_scrape.py
"""
import os
import sys
import uuid
import json
from datetime import datetime

# Add repo root to path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus

def queue_command(db, cmd_type: str, supplier_id: int, supplier_name: str, priority: int = 70):
    """Queue a command."""
    cmd_id = str(uuid.uuid4())
    cmd = SystemCommand(
        id=cmd_id,
        type=cmd_type,
        status=CommandStatus.PENDING,
        priority=priority,
        payload=json.dumps({
            "supplier_id": supplier_id,
            "supplier_name": supplier_name
        })
    )
    db.add(cmd)
    db.commit()
    print(f"[OK] Queued {cmd_type} for {supplier_name}: {cmd_id}")
    return cmd_id

def main():
    print("Queuing full site scraping and enrichment...")
    print()
    
    db = SessionLocal()
    try:
        # Queue scraping jobs (higher priority)
        nl_scrape_id = queue_command(db, "SCRAPE_SUPPLIER", 2, "NOEL_LEEMING", priority=70)
        oc_scrape_id = queue_command(db, "SCRAPE_SUPPLIER", 1, "ONECHEQ", priority=70)
        
        print()
        
        # Queue enrichment jobs (lower priority, will run after scraping)
        nl_enrich_id = queue_command(db, "ENRICH_SUPPLIER", 2, "NOEL_LEEMING", priority=60)
        oc_enrich_id = queue_command(db, "ENRICH_SUPPLIER", 1, "ONECHEQ", priority=60)
        
        print()
        print("All jobs queued successfully!")
        print()
        print("Execution order (by priority):")
        print(f"  1. SCRAPE_SUPPLIER (NOEL_LEEMING) - {nl_scrape_id}")
        print(f"  2. SCRAPE_SUPPLIER (ONECHEQ) - {oc_scrape_id}")
        print(f"  3. ENRICH_SUPPLIER (NOEL_LEEMING) - {nl_enrich_id}")
        print(f"  4. ENRICH_SUPPLIER (ONECHEQ) - {oc_enrich_id}")
        print()
        print("Monitor progress at: http://localhost:3000/ops/commands")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
