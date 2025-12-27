# RetailOS Project Structure

This document provides a visual overview of the project organization.

## ?? Directory Tree

```
RetailOS/
¦
+-- ?? README.md                    # Project overview & quick start
+-- ?? requirements.txt             # Python dependencies
+-- ?? Dockerfile                   # Container definition
+-- ?? docker-compose.yml           # Container orchestration
+-- ?? .env.example                 # Environment template
+-- ?? .env.template                # Environment template (alt)
+-- ?? .gitignore                   # Git exclusions
¦
+-- ?? /docs                        # All documentation
¦   +-- README.md                   # Documentation index
¦   +-- REQUIREMENTS.md             # All 412 requirements
¦   +-- ARCHITECTURE.md             # System design
¦   +-- DEPLOYMENT.md               # Deployment guide
¦   +-- ARCHIVE_MANIFEST.md         # Archive tracking
¦   +-- /guides                     # Feature guides
¦       +-- UNIVERSAL_SCRAPER_GUIDE.md
¦
+-- ?? /retail_os                   # Main application code
¦   +-- /dashboard                  # Streamlit UI
¦   ¦   +-- app.py                  # Main dashboard
¦   ¦   +-- /tabs                   # Dashboard tabs
¦   +-- /scrapers                   # Supplier scrapers
¦   ¦   +-- /cash_converters
¦   ¦   +-- /noel_leeming
¦   ¦   +-- /onecheq
¦   ¦   +-- /universal
¦   +-- /ai                         # AI enrichment
¦   ¦   +-- enrichment.py
¦   ¦   +-- semantic_standardizer.py
¦   +-- /quality                    # Quality control
¦   ¦   +-- trust_engine.py
¦   ¦   +-- policy_engine.py
¦   ¦   +-- content_rebuilder.py
¦   +-- /trademe                    # Trade Me integration
¦   ¦   +-- api.py
¦   ¦   +-- sync.py
¦   +-- /strategy                   # Pricing & lifecycle
¦   ¦   +-- pricing_engine.py
¦   ¦   +-- lifecycle_manager.py
¦   +-- /db                         # Database layer
¦       +-- schema.py
¦       +-- operations.py
¦
+-- ?? /scripts                     # Automation scripts
¦   +-- /ops                        # Operational scripts
¦   ¦   +-- healthcheck.py          # System health check
¦   ¦   +-- backup.ps1              # Backup automation
¦   ¦   +-- bootstrap.ps1           # Environment setup
¦   ¦   +-- setup_git.ps1           # Git configuration
¦   ¦   +-- run_daily_sync.bat      # Daily sync runner
¦   +-- ...                         # Feature-specific scripts
¦
+-- ?? /data                        # Runtime data
¦   +-- trademe_store.db            # Main database (15 MB)
¦   +-- trademe_store.db-shm        # SQLite shared memory
¦   +-- trademe_store.db-wal        # Write-ahead log
¦   +-- /media                      # Downloaded images
¦
+-- ?? /migrations                  # Database migrations
+-- ? /tests                       # Test suite
+-- ?? /exports                     # Generated CSV/JSON exports
+-- ???  /_archive                   # Historical files
¦   +-- /docs                       # Archived documentation
¦   +-- /scripts                    # Archived scripts
¦   +-- /code                       # Legacy code
¦
+-- ?? /.vscode                     # VS Code settings
+-- ?? /.git                        # Git repository
+-- ?? /.agent                      # AI agent workflows

```

## ?? Key Principles

### 1. **Clean Root Directory**
Only essential project files in the root:
- Configuration files (Docker, requirements)
- Main README for quick start
- Environment templates

### 2. **Documentation Centralization**
All documentation in /docs:
- Easy to find and navigate
- Separate from code
- Includes guides and requirements

### 3. **Logical Code Organization**
- /retail_os - Main application (modular by feature)
- /scripts - Automation and operations
- /tests - Test suite
- /migrations - Database evolution

### 4. **Data Separation**
- /data - Runtime data (databases, media)
- /exports - Generated outputs
- /_archive - Historical files

### 5. **Self-Explanatory Structure**
Anyone can understand the project layout at a glance without needing to ask questions.

## ?? Navigation Guide

| I want to...                          | Go to...                          |
|---------------------------------------|-----------------------------------|
| Understand the project                | /README.md                      |
| See all requirements                  | /docs/REQUIREMENTS.md           |
| Understand the architecture           | /docs/ARCHITECTURE.md           |
| Deploy the application                | /docs/DEPLOYMENT.md             |
| Run the dashboard                     | /retail_os/dashboard/app.py     |
| Add a new scraper                     | /retail_os/scrapers/            |
| Run health checks                     | /scripts/ops/healthcheck.py     |
| View the database                     | /data/trademe_store.db          |
| Find archived files                   | /_archive/                      |

## ?? Quick Commands

```bash
# Start the application
docker-compose up -d

# Run health check
python scripts/ops/healthcheck.py

# Backup database
powershell scripts/ops/backup.ps1

# Access dashboard
http://localhost:8501
```

---

**Last Updated:** 2025-12-22
**Structure Version:** 2.0 (Post-Reorganization)
