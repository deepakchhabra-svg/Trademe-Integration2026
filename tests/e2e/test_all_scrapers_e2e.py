"""
Comprehensive E2E Test for All 3 Scrapers
Tests OneCheq, Cash Converters, and Noel Leeming end-to-end
"""
import sys
import time
sys.path.append('.')

from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus, SupplierProduct, InternalProduct
from retail_os.trademe.worker import CommandWorker
import uuid

def test_all_scrapers():
    print("="*60)
    print("E2E TEST: ALL 3 SCRAPERS")
    print("="*60)
    
    session = SessionLocal()
    worker = CommandWorker()
    
    # Define all 3 scrapers
    scrapers = [
        {"id": 1, "name": "ONECHEQ"},
        {"id": 2, "name": "NOEL_LEEMING"},
        {"id": 3, "name": "CASH_CONVERTERS"}
    ]
    
    results = {}
    
    for scraper in scrapers:
        print(f"\n{'='*60}")
        print(f"TESTING: {scraper['name']}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # 1. SCRAPE
        print(f"\n[1] Scraping {scraper['name']}...")
        scrape_id = str(uuid.uuid4())
        scrape_cmd = SystemCommand(
            id=scrape_id,
            type="SCRAPE_SUPPLIER",
            payload={"supplier_id": scraper["id"], "supplier_name": scraper["name"]},
            status=CommandStatus.PENDING,
            priority=100
        )
        session.add(scrape_cmd)
        session.commit()
        
        # Process scrape
        for _ in range(10):
            worker.process_next_command()
            session.commit()
            session.close()
            session = SessionLocal()
            cmd = session.query(SystemCommand).filter_by(id=scrape_id).first()
            if cmd and cmd.status not in [CommandStatus.PENDING, CommandStatus.EXECUTING]:
                break
            time.sleep(0.5)
        
        scrape_status = cmd.status if cmd else "NOT_FOUND"
        products = session.query(SupplierProduct).filter_by(supplier_id=scraper["id"]).count()
        
        print(f"   Scrape Status: {scrape_status}")
        print(f"   Products: {products}")
        
        # 2. ENRICH  
        print(f"\n[2] Enriching {scraper['name']}...")
        enrich_id = str(uuid.uuid4())
        enrich_cmd = SystemCommand(
            id=enrich_id,
            type="ENRICH_SUPPLIER",
            payload={"supplier_id": scraper["id"], "supplier_name": scraper["name"]},
            status=CommandStatus.PENDING,
            priority=100
        )
        session.add(enrich_cmd)
        session.commit()
        
        # Process enrich
        for _ in range(10):
            worker.process_next_command()
            session.commit()
            session.close()
            session = SessionLocal()
            cmd = session.query(SystemCommand).filter_by(id=enrich_id).first()
            if cmd and cmd.status not in [CommandStatus.PENDING, CommandStatus.EXECUTING]:
                break
            time.sleep(0.5)
        
        enrich_status = cmd.status if cmd else "NOT_FOUND"
        internal_products = session.query(InternalProduct).join(SupplierProduct).filter(
            SupplierProduct.supplier_id == scraper["id"]
        ).count()
        
        print(f"   Enrich Status: {enrich_status}")
        print(f"   Internal Products: {internal_products}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        results[scraper["name"]] = {
            "scrape_status": str(scrape_status),
            "scrape_products": products,
            "enrich_status": str(enrich_status),
            "internal_products": internal_products,
            "duration_sec": round(duration, 2),
            "pass": scrape_status == CommandStatus.SUCCEEDED and enrich_status == CommandStatus.SUCCEEDED and products > 0
        }
        
        print(f"\n   Duration: {duration:.2f}s")
        print(f"   Result: {'PASS' if results[scraper['name']]['pass'] else 'FAIL'}")
    
    session.close()
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY: ALL 3 SCRAPERS")
    print(f"{'='*60}")
    
    for name, result in results.items():
        status = "✓ PASS" if result["pass"] else "✗ FAIL"
        print(f"\n{name}: {status}")
        print(f"  Products: {result['scrape_products']}")
        print(f"  Enriched: {result['internal_products']}")
        print(f"  Duration: {result['duration_sec']}s")
    
    # Performance comparison
    print(f"\n{'='*60}")
    print("PERFORMANCE COMPARISON")
    print(f"{'='*60}")
    durations = {name: r["duration_sec"] for name, r in results.items()}
    avg = sum(durations.values()) / len(durations)
    for name, dur in durations.items():
        diff = ((dur - avg) / avg * 100) if avg > 0 else 0
        print(f"{name}: {dur}s ({diff:+.1f}% vs avg)")
    
    # Overall result
    all_pass = all(r["pass"] for r in results.values())
    print(f"\n{'='*60}")
    print(f"OVERALL: {'PASS - All 3 scrapers working E2E' if all_pass else 'FAIL - Some scrapers failed'}")
    print(f"{'='*60}")
    
    return all_pass

if __name__ == "__main__":
    result = test_all_scrapers()
    sys.exit(0 if result else 1)
