# Base Image
FROM python:3.12-slim

# Working Directory
WORKDIR /app

# System Dependencies
# Added chromium and clean up in one layer
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Environment Variables
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user and change ownership of app files
RUN useradd -m myuser && chown -R myuser /app
USER myuser

# Expose Port
EXPOSE 8501

# Default Command
CMD ["streamlit", "run", "retail_os/dashboard/app.py"]