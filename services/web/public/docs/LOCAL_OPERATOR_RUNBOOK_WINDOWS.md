## Local Operator Runbook (Windows-first)

This runbook is for running **OC (ONECHEQ)** end-to-end locally with the operator console.

### Prereqs

- **Python 3.12+**
- **Node 18+**
- Trade Me credentials in `.env` (repo root) if you want to validate/publish:
  - `CONSUMER_KEY`
  - `CONSUMER_SECRET`
  - `ACCESS_TOKEN`
  - `ACCESS_TOKEN_SECRET`

### Terminal A — API (FastAPI)

From repo root:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python -m uvicorn services.api.main:app --reload --port 8000
```

### Terminal B — Worker

From repo root (same venv):

```bash
.venv\\Scripts\\activate
python -u retail_os\\trademe\\worker.py
```

### Terminal C — Web (Next.js)

```bash
cd services\\web
npm install
npm run dev
```

Open the UI at `http://localhost:3000`.

---

## Operator flow (OC)

### 1) Scrape 2 categories

Go to **Ops → Pipeline** and open the supplier (ONECHEQ).

- **Select supplier**: ONECHEQ (OC)
- **Source category**:
  - OC: Shopify collection handle (example: `smartphones-and-mobilephones`)
- Set **Pages = 1–2** (start small)
- Click **Run scrape**
- Click **Open Vault 1** to confirm items appear

Repeat for a second category.

### 2) Enrich

In **Pipeline**:

- Set **Batch size** (start with 25)
- Click **Run enrich**
- Click **Open Vault 2** to confirm items appear

### 3) Create drafts

- In **Pipeline**, click **Build drafts** (safe)
- Then open **Vault 3** filtered to **Draft**

### 4) Judge quality in Vault 3 only

Open any Draft listing:

- **Listing preview** shows what buyers will see (title, price, category, shipping/payment summary, description, images).
- **Hard gates (LaunchLock)** show **READY/BLOCKED** with **Top blocker** and checklist.

### 5) Validate Trade Me (real)

Go to **Ops → Trade Me Health**:

- Confirms **Configured / Auth OK / Auth failed** + **last checked (NZT)**
- Click **Validate 10** (uses real Trade Me Validate endpoint)

### 6) Publish (optional live smoke)

Only do this if:

- Trade Me Health shows **Configured + Auth OK**
- The Draft you chose is **READY**

In **Pipeline / Runbook**:

- Click **Publish approved drafts**
- Default safety: stop-on-failure (enqueues one at a time)

---

## When something is blocked / fails

- **Vault 3 listing shows the Top blocker** (what failed + why).
- Use:
  - **Queue** (Ops → Queue) for commands that need attention
  - **Jobs** (Ops → Jobs) for background job failures
  - **Command log** (Ops → Command log) for full command history

