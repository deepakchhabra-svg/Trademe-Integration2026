# RetailOS — Operator Runbook (current)

This repo ships a **Next.js Operator Console** (recommended) + a Python API + a command worker.

For the full Windows-first guide, see `docs/LOCAL_OPERATOR_RUNBOOK_WINDOWS.md`.

## Start locally (no Docker)

### Prereqs
- Python 3.10+ recommended
- Node.js 20+ (npm available)

### Terminal A — API

```bash
python -m uvicorn services.api.main:app --reload --port 8000
```

### Terminal B — Worker

```bash
python -u retail_os/trademe/worker.py
```

### Terminal C — Web

```bash
cd services/web
npm install
npm run dev -- --port 3000
```

Open the console: `http://localhost:3000`

## Operator flow (canonical)

1. Go to **Ops → Pipeline** and open your supplier.
2. Run: **Scrape → Images → Enrich → Draft**
3. Check **Top blockers** + Vault drilldowns.
4. Use **Trade Me Health** to validate credentials.
5. Publish only **READY** drafts via the publish console.

## Where to look when blocked

- **Pipeline**: top blockers + next actions
- **Ops → Queue**: running/queued work
- **Ops → Inbox**: items needing attention
- **Ops → Jobs**: batch job summaries/failures
- **Command detail**: live tail + progress + safe actions

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
