# RetailOS — Operator Console (Trade Me pipeline)

RetailOS is an operator console + pipeline for scraping supplier products, enriching copy, and producing Trade Me drafts/publishes with hard quality gates (LaunchLock).

## Quick start (Docker, recommended)

```bash
# 1) Configure environment
cp .env.example .env
# edit .env (Trade Me creds optional unless validating/publishing)

# 2) Run API + Worker + Web
docker-compose up -d

# 3) Open the console
open http://localhost:3000
```

## 📁 Project Structure

```
/
├── README.md                    ← You are here
├── requirements.txt             ← Python dependencies
├── Dockerfile                   ← Container definition
├── docker-compose.yml           ← Orchestration
│
├── /docs                        ← 📚 All documentation
│   ├── REQUIREMENTS.md          ← All 412 requirements
│   ├── ARCHITECTURE.md          ← System design
│   ├── DEPLOYMENT.md            ← Deploy guide
│   └── /guides                  ← Feature guides
│
├── /retail_os                   ← 🎯 Main application
│   ├── /scrapers                ← Supplier scrapers
│   ├── /quality                 ← Quality control
│   └── /trademe                 ← Trade Me API
│
├── /services
│   ├── /api                     ← FastAPI backend (HTTP API)
│   └── /web                     ← Next.js operator console (UI)
│
├── /scripts                     ← 🔧 Automation
│   ├── /ops                     ← Operational scripts
│   └── ...                      ← Feature scripts
│
├── /data                        ← 💾 Runtime data
│   └── retail_os.db             ← SQLite database (default for local/dev)
│
├── /migrations                  ← 🔄 DB migrations
├── /tests                       ← ✅ Test suite
├── /exports                     ← 📊 Generated exports
└── /_archive                    ← 🗄️ Historical files
```

## Supplier support (truth)

- **OneCheq**: supported (pilot scope)
- **Noel Leeming**: present in codebase but **blocked/paused** due to robots/image constraints (see `docs/ARCHITECTURE.md`)
- **Cash Converters**: present in codebase but **not supported** in the current operator flow

## 📚 Documentation

- **[Full Documentation](docs/README.md)** - Complete docs index
- **[Requirements](docs/REQUIREMENTS.md)** - All 418 requirements
- **[Architecture](docs/ARCHITECTURE.md)** - System design
- **[Deployment](docs/DEPLOYMENT.md)** - Deploy guide

## Local dev (no Docker)

- **API**: `python -m uvicorn services.api.main:app --reload --port 8000`
- **Worker**: `python -u retail_os/trademe/worker.py`
- **Web**: `cd services/web && npm install && npm run dev -- --port 3000`

Windows convenience: `powershell -ExecutionPolicy Bypass -File scripts/run_local.ps1`

## Operator UI (start here)

- Open `http://localhost:3000`
- Go to **Ops → Pipeline** for the single-screen supplier flow (Scrape → Images → Enrich → Draft → Validate → Publish).

## 🔐 Environment Variables

Copy `.env.example` to `.env` and configure:

- `CONSUMER_KEY` - Trade Me API key
- `CONSUMER_SECRET` - Trade Me API secret
- `ACCESS_TOKEN` - Trade Me access token
- `ACCESS_TOKEN_SECRET` - Trade Me access token secret
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `GEMINI_API_KEY` - Google Gemini API key (optional)

## 📊 Database

SQLite database located at `data/retail_os.db` (default). Override with `DATABASE_URL`.

- **Backup**: `python scripts/ops/backup.ps1`
- **Migrations**: See `/migrations` directory

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📝 License

Proprietary - All rights reserved

## 🤝 Support

For issues or questions, see [DEPLOYMENT.md](docs/DEPLOYMENT.md)
