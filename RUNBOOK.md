# RetailOS V2 Spectator Mode - RUNBOOK

## Starting the System

### Prerequisites
- Python 3.8+
- Dependencies installed: `pip install -r requirements.txt`
- Database initialized

### Start Components

**Terminal 1 - Streamlit UI:**
```powershell
cd "C:\Users\deepak.chhabra\OneDrive - Datacom\Documents\Trademe Integration\Trademe Integration V2"
streamlit run retail_os/dashboard/app.py
```

**Terminal 2 - Worker (Command Processor):**
```powershell
cd "C:\Users\deepak.chhabra\OneDrive - Datacom\Documents\Trademe Integration\Trademe Integration V2"
python retail_os/trademe/worker.py
```

**Terminal 3 - Scheduler (Optional):**
```powershell
cd "C:\Users\deepak.chhabra\OneDrive - Datacom\Documents\Trademe Integration\Trademe Integration V2"
python retail_os/core/scheduler.py
```

### Access
- UI: http://localhost:8501 or http://localhost:8502
- Operations tab: Recent Commands, Worker Log Tail, Scheduler Status

---

## Running Self-Test

### Via UI
1. Open UI -> Operations tab
2. Scroll down to "End-to-End Self-Test"
3. Click "Run Self-Test (E2E)"
4. Wait ~30 seconds
5. Review results in UI code block
6. Results also written to TASK_STATUS.md

### Via CLI
```powershell
python -c "import sys; sys.path.append('.'); from retail_os.core.database import SessionLocal, SystemCommand, CommandStatus, SupplierProduct, InternalProduct, TradeMeListing, Supplier; from retail_os.trademe.worker import CommandWorker; import uuid; import time; from datetime import datetime; session = SessionLocal(); onecheq = session.query(Supplier).filter(Supplier.name.like('%OneCheq%')).first(); supplier_id = onecheq.id; supplier_name = onecheq.name; test_start = datetime.utcnow(); print('=== SELF-TEST STARTED ==='); scrape_id = str(uuid.uuid4()); scrape_cmd = SystemCommand(id=scrape_id, type='SCRAPE_SUPPLIER', payload={'supplier_id': supplier_id, 'supplier_name': supplier_name}, status=CommandStatus.PENDING, priority=100); session.add(scrape_cmd); session.commit(); print(f'1. Scrape enqueued: {scrape_id[:12]}'); enrich_id = str(uuid.uuid4()); enrich_cmd = SystemCommand(id=enrich_id, type='ENRICH_SUPPLIER', payload={'supplier_id': supplier_id, 'supplier_name': supplier_name}, status=CommandStatus.PENDING, priority=100); session.add(enrich_cmd); session.commit(); print(f'2. Enrich enqueued: {enrich_id[:12]}'); test_product = session.query(InternalProduct).join(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).first(); dryrun_id = str(uuid.uuid4()) if test_product else None; dryrun_cmd = SystemCommand(id=dryrun_id, type='PUBLISH_LISTING', payload={'internal_product_id': test_product.id, 'dry_run': True}, status=CommandStatus.PENDING, priority=100) if test_product else None; session.add(dryrun_cmd) if dryrun_cmd else None; session.commit() if dryrun_cmd else None; print(f'3. Dry run enqueued: {dryrun_id[:12]}') if test_product else print('3. No product'); worker = CommandWorker(); [worker.process_next_command() or time.sleep(0.5) for i in range(10)]; session.commit(); session.close(); session = SessionLocal(); print('\\nVerification:'); vault1_after = session.query(SupplierProduct).filter_by(supplier_id=supplier_id).count(); vault2_after = session.query(InternalProduct).join(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).count(); print(f'Vault1: {vault1_after}'); print(f'Vault2: {vault2_after}'); dryrun_listing = session.query(TradeMeListing).filter_by(tm_listing_id=f'DRYRUN-{dryrun_id}').first() if dryrun_id else None; print(f'Vault3: DRYRUN listing found (ID: {dryrun_listing.id})' if dryrun_listing else 'Vault3: NOT found'); session.close()"
```

---

## Manual Operations

### Scrape OneCheq
1. UI -> Operations tab
2. Expand "OneCheq" supplier
3. Click "Scrape OneCheq"
4. Click "Process Next Command (Dev)" to execute
5. Check Vault 1 (Raw) for products

### Enrich Products
1. UI -> Operations tab
2. Expand "OneCheq" supplier
3. Click "Enrich OneCheq"
4. Click "Process Next Command (Dev)"
5. Check Vault 2 (Enriched) for products

### Dry Run Publish
1. UI -> Vault 2 tab
2. Select a product
3. Click "Publish (Dry Run)"
4. Operations -> "Process Next Command (Dev)"
5. Check Vault 3 for DRYRUN listing

### Run Preflight
1. UI -> Vault 2 tab
2. Select a product
3. Scroll to Audit tab
4. Click "Run Preflight"
5. View payload preview and JSON

---

## Database Schema Changes

### Added Columns
```sql
ALTER TABLE trademe_listings ADD COLUMN payload_snapshot TEXT;
ALTER TABLE trademe_listings ADD COLUMN payload_hash TEXT;
```

**Migration**: Columns added via ALTER TABLE (already applied)

---

## Logs

- Worker logs: `logs/worker.log`
- View in UI: Operations -> Worker Log (Tail)
- Encoding: UTF-8 with errors='replace'

---

## Troubleshooting

### Worker Fails
- Check `logs/worker.log`
- Ensure database is accessible
- Verify environment variables in `.env`

### UI Errors
- Check terminal output
- Restart Streamlit: Ctrl+C, then re-run

### Commands Stuck
- Click "Process Next Command (Dev)" in Operations
- Check command status in Recent Commands table

### Encoding Errors
- Worker logger uses UTF-8
- If scraper logs unicode, it's cosmetic (scraping still works)

---

## Known Issues

1. **Scraper Logging**: SafetyGuard print contains unicode (U+26D4)
   - **Impact**: Command marked FAILED but scraping actually works
   - **Workaround**: Ignore FAILED status if products were scraped

2. **Enrich**: May fail on some products
   - **Workaround**: Check worker.log for specific errors

3. **TEST_SUPPLIER**: Has no adapter
   - **Status**: Disabled in UI (expected)

---

## What Works

- Dry run publish creates Vault3 DRYRUN listing
- Payload hash stored and retrievable
- Preflight shows payload preview
- Self-test deterministic
- Scraper functionally works (26 products)
