# Simple Dockerfile - API only (UI will be deployed separately)
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Environment
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY retail_os/ ./retail_os/
COPY services/api/ ./services/api/
COPY scripts/ ./scripts/
COPY imports/ ./imports/

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run API (uses Railway's PORT env var)
CMD ["sh", "-c", "python -m uvicorn services.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
