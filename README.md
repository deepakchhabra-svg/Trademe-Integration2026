# RetailOS - Autonomous Trade Me Dropshipping Platform

**RetailOS** is an autonomous trading platform that scrapes products from multiple suppliers, enriches them with AI, and automatically lists them on Trade Me.

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd "Trademe Integration"

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run with Docker
docker-compose up -d

# 4. Access dashboard
# Open http://localhost:8501
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
│   ├── /dashboard               ← Streamlit UI
│   ├── /scrapers                ← Supplier scrapers
│   ├── /ai                      ← AI enrichment
│   ├── /quality                 ← Quality control
│   └── /trademe                 ← Trade Me API
│
├── /scripts                     ← 🔧 Automation
│   ├── /ops                     ← Operational scripts
│   └── ...                      ← Feature scripts
│
├── /data                        ← 💾 Runtime data
│   └── trademe_store.db         ← SQLite database
│
├── /migrations                  ← 🔄 DB migrations
├── /tests                       ← ✅ Test suite
├── /exports                     ← 📊 Generated exports
└── /_archive                    ← 🗄️ Historical files
```

## 🎯 Core Features

- **Multi-Supplier Scraping** - OneCheq, Noel Leeming, Cash Converters
- **AI Enrichment** - OpenAI/Gemini for titles & descriptions
- **Quality Control** - Trust scoring, policy enforcement, content sanitization
- **Trade Me Integration** - Full CRUD operations, order syncing
- **Lifecycle Management** - Auto-pricing, performance tracking
- **Real-time Dashboard** - Streamlit UI for monitoring & control

## 📚 Documentation

- **[Full Documentation](docs/README.md)** - Complete docs index
- **[Requirements](docs/REQUIREMENTS.md)** - All 418 requirements
- **[Architecture](docs/ARCHITECTURE.md)** - System design
- **[Deployment](docs/DEPLOYMENT.md)** - Deploy guide

## 🛠️ Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard locally
streamlit run retail_os/dashboard/app.py

# Run scrapers
python scripts/ops/run_daily_sync.bat

# Health check
python scripts/ops/healthcheck.py
```

## 🔐 Environment Variables

Copy `.env.example` to `.env` and configure:

- `TRADEME_CONSUMER_KEY` - Trade Me API key
- `TRADEME_CONSUMER_SECRET` - Trade Me API secret
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `GEMINI_API_KEY` - Google Gemini API key (optional)

## 📊 Database

SQLite database located at `/data/trademe_store.db`

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
