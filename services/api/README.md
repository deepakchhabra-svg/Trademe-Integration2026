# RetailOS API (FastAPI)

This service exposes a clean JSON API over the existing RetailOS database and command queue.

## Run (dev)

From repo root:

```bash
pip install -r requirements.txt
uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints (high level)

- `/health`
- `/vaults/raw` (SupplierProduct)
- `/vaults/enriched` (InternalProduct + SupplierProduct join)
- `/vaults/live` (TradeMeListing)
- `/orders`
- `/commands` (create/list)

