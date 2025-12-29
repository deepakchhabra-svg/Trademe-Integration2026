
import os
import sys
import time
import uuid
from datetime import datetime, timezone

# Add parent dir to path
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus, InternalProduct, SupplierProduct
from retail_os.core.database import Supplier

def queue_command(session, cmd_type, payload, priority=10):
    cmd_id = str(uuid.uuid4())
    cmd = SystemCommand(
        id=cmd_id,
        type=cmd_type,
        payload=payload,
        status=CommandStatus.PENDING,
        priority=priority,
        created_at=datetime.now(timezone.utc)
    )
    session.add(cmd)
    session.commit()
    return cmd_id

def wait_for_command(session, cmd_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        session.expire_all()
        cmd = session.get(SystemCommand, cmd_id)
        if cmd.status == CommandStatus.SUCCEEDED:
            print(f"[ORCHESTRATOR] Command {cmd_id} ({cmd.type}) SUCCEEDED")
            return True
        if cmd.status in [CommandStatus.FAILED_FATAL, CommandStatus.HUMAN_REQUIRED]:
            print(f"[ORCHESTRATOR] Command {cmd_id} ({cmd.type}) BLOCKED: {cmd.error_message}")
            return False
        time.sleep(5)
    print(f"[ORCHESTRATOR] Command {cmd_id} timed out")
    return False

def main():
    session = SessionLocal()
    
    print("=== STARTING HANDSFREE 2-CATEGORY PILOT RUN ===")

    # Resolve supplier IDs dynamically (no hardcoded IDs).
    def supplier_id(name: str, base_url: str) -> int:
        s = session.query(Supplier).filter(Supplier.name == name).first()
        if not s:
            s = Supplier(name=name, base_url=base_url, is_active=True)
            session.add(s)
            session.commit()
        return int(s.id)

    oc_id = supplier_id("ONECHEQ", "https://onecheq.co.nz")
    nl_id = supplier_id("NOEL_LEEMING", "https://www.noelleeming.co.nz")
    
    # 1. Noel Leeming Computers
    print("\n--- Phase 1: Scraping Noel Leeming (Computers) ---")
    nl_payload = {
        "supplier_id": nl_id,
        "supplier_name": "NOEL_LEEMING",
        "source_category": "https://www.noelleeming.co.nz/search?cgid=computersofficetech-computers",
        "pages": 1,
        "deep_scrape": True
    }
    nl_scrape_id = queue_command(session, "SCRAPE_SUPPLIER", nl_payload, priority=1)
    
    # 2. OneCheq Smartphones
    print("\n--- Phase 2: Scraping OneCheq (Smartphones) ---")
    oc_payload = {
        "supplier_id": oc_id,
        "supplier_name": "ONECHEQ",
        "source_category": "smartphones-and-mobilephones",
        "pages": 1
    }
    oc_scrape_id = queue_command(session, "SCRAPE_SUPPLIER", oc_payload, priority=1)
    
    print("Waiting for scrapes to finish...")
    nl_ok = wait_for_command(session, nl_scrape_id)
    oc_ok = wait_for_command(session, oc_scrape_id)
    
    if not (nl_ok or oc_ok):
        print("Scrapes failed. Aborting.")
        return

    # 3. Enrichment
    print("\n--- Phase 3: Triggering Enrichment ---")
    # We trigger enrichment for the suppliers
    enrich_nl_id = queue_command(session, "ENRICH_SUPPLIER", {"supplier_id": nl_id}, priority=5)
    enrich_oc_id = queue_command(session, "ENRICH_SUPPLIER", {"supplier_id": oc_id}, priority=5)
    
    wait_for_command(session, enrich_nl_id)
    wait_for_command(session, enrich_oc_id)

    # 4. Publishing Sample
    print("\n--- Phase 4: Publishing Samples ---")
    # Pick top 2 from each category that were just updated/synced
    # This is simple: just find Products from these suppliers.
    
    def get_sample_ids(supplier_id, count=2):
        sps = session.query(SupplierProduct).filter_by(supplier_id=supplier_id).limit(count).all()
        ids = []
        for sp in sps:
            ip = session.query(InternalProduct).filter_by(primary_supplier_product_id=sp.id).first()
            if ip:
                ids.append(ip.id)
        return ids

    nl_samples = get_sample_ids(nl_id, 2)
    oc_samples = get_sample_ids(oc_id, 2)
    
    all_samples = nl_samples + oc_samples
    print(f"Identified {len(all_samples)} products for publishing: {all_samples}")
    
    # Safety: default to DRY_RUN. Real publish is destructive, must be explicitly enabled.
    allow_publish = os.getenv("RETAILOS_ALLOW_PUBLISH", "0") == "1"
    publish_ids = []
    for pid in all_samples:
        pub_id = queue_command(
            session,
            "PUBLISH_LISTING",
            {"internal_product_id": pid, "dry_run": (not allow_publish)},
            priority=20,
        )
        publish_ids.append(pub_id)
        mode = "PUBLISH" if allow_publish else "DRY_RUN"
        print(f"  Queued {mode} for IP {pid} (CMD {pub_id})")

    print("Waiting for publications...")
    for pub_id in publish_ids:
        wait_for_command(session, pub_id)

    print("\n=== PILOT RUN COMPLETE ===")
    session.close()

if __name__ == "__main__":
    main()
