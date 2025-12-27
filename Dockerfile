# Base Image
FROM python:3.12-slim

# Working Directory
WORKDIR /app

# System Dependencies
# curl: for universal adapter and healthchecks
# chromium: for selectolax/httpx scraping logic (some sites check for browser headers)
# build-essential: for compiling some python deps
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Requirements
COPY requirements.txt .

# Install Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Application Code
COPY . .

# Environment Variables (Default)
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Expose Port
EXPOSE 8501

# Default Command (Run Dashboard)
CMD ["streamlit", "run", "retail_os/dashboard/app.py"]
