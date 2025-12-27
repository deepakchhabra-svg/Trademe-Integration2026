# Deployment Guide - Trade Me Integration

This guide covers deploying the Trade Me Integration system to production environments.

## 🎯 Deployment Options

### Option 1: Local Windows Server (Recommended for MVP)
### Option 2: Cloud VM (Azure/AWS/GCP)
### Option 3: Docker Container (Most Portable)

---

## 📋 Pre-Deployment Checklist

- [ ] All scrapers tested and working
- [ ] Trade Me API credentials verified
- [ ] Database migrations applied
- [ ] `.env` file configured with production credentials
- [ ] Backup strategy defined
- [ ] Monitoring alerts configured
- [ ] Documentation reviewed

---

## 🖥️ Option 1: Local Windows Server Deployment

### Prerequisites
- Windows 10/11 or Windows Server 2019+
- Python 3.12+ installed
- Admin access for service creation
- Stable internet connection

### Step 1: Prepare Environment

```powershell
# Create dedicated directory
mkdir C:\RetailOS
cd C:\RetailOS

# Copy project files (excluding .git, data, logs)
# Use robocopy or manual copy

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```powershell
# Copy and edit .env
cp .env.example .env
notepad .env
```

Ensure these are set:
```
CONSUMER_KEY=your_production_key
CONSUMER_SECRET=your_production_secret
ACCESS_TOKEN=your_production_token
ACCESS_TOKEN_SECRET=your_production_token_secret
DATABASE_URL=sqlite:///C:/RetailOS/data/retail.db
```

### Step 3: Initialize Database

```powershell
# Create data directory
mkdir data\media -Force

# Initialize database
python -c "from retail_os.core.database import Base, engine; Base.metadata.create_all(engine)"
```

### Step 4: Create Windows Service (Dashboard)

Create `dashboard_service.py`:
```python
import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import os

class RetailOSDashboard(win32serviceutil.ServiceFramework):
    _svc_name_ = "RetailOSDashboard"
    _svc_display_name_ = "Retail OS Dashboard"
    _svc_description_ = "Streamlit dashboard for Trade Me integration"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        os.chdir(r'C:\RetailOS')
        self.process = subprocess.Popen([
            r'C:\RetailOS\venv\Scripts\streamlit.exe',
            'run',
            'retail_os/dashboard/app.py',
            '--server.port=8501',
            '--server.address=0.0.0.0'
        ])
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(RetailOSDashboard)
```

Install and start service:
```powershell
# Install pywin32
pip install pywin32

# Install service
python dashboard_service.py install

# Start service
python dashboard_service.py start
```

### Step 5: Create Scheduled Tasks (Scrapers)

```powershell
# Create task for scraper (runs every 6 hours)
$action = New-ScheduledTaskAction -Execute "C:\RetailOS\venv\Scripts\python.exe" `
    -Argument "-u C:\RetailOS\scripts\run_dual_site_pipeline.py --max-pages 1000 --concurrency 10" `
    -WorkingDirectory "C:\RetailOS"

$trigger = New-ScheduledTaskTrigger -Daily -At 12:00AM -RepetitionInterval (New-TimeSpan -Hours 6)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RunOnlyIfNetworkAvailable

Register-ScheduledTask -TaskName "RetailOS-Scraper" -Action $action -Trigger $trigger `
    -Settings $settings -User "SYSTEM" -RunLevel Highest
```

### Step 6: Configure Firewall

```powershell
# Allow dashboard port
New-NetFirewallRule -DisplayName "Retail OS Dashboard" -Direction Inbound `
    -LocalPort 8501 -Protocol TCP -Action Allow
```

### Step 7: Setup Logging

```powershell
# Create logs directory
mkdir C:\RetailOS\logs

# Configure log rotation (use Task Scheduler)
# Create cleanup_logs.ps1:
```

`cleanup_logs.ps1`:
```powershell
# Keep only last 30 days of logs
Get-ChildItem "C:\RetailOS\logs\*.log" | 
    Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} | 
    Remove-Item -Force
```

---

## ☁️ Option 2: Cloud VM Deployment (Azure Example)

### Step 1: Create VM

```bash
# Azure CLI
az vm create \
  --resource-group retail-os-rg \
  --name retail-os-vm \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys
```

### Step 2: Install Dependencies

```bash
# SSH into VM
ssh azureuser@<vm-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install python3.12 python3.12-venv python3-pip -y

# Install git
sudo apt install git -y
```

### Step 3: Deploy Application

```bash
# Clone or copy project
git clone <your-repo-url> /opt/retail-os
cd /opt/retail-os

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure Systemd Service

Create `/etc/systemd/system/retail-os-dashboard.service`:
```ini
[Unit]
Description=Retail OS Dashboard
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/opt/retail-os
Environment="PATH=/opt/retail-os/venv/bin"
ExecStart=/opt/retail-os/venv/bin/streamlit run retail_os/dashboard/app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable retail-os-dashboard
sudo systemctl start retail-os-dashboard
```

### Step 5: Setup Nginx Reverse Proxy

```bash
sudo apt install nginx -y

# Create nginx config
sudo nano /etc/nginx/sites-available/retail-os
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/retail-os /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 6: Setup Cron Jobs

```bash
crontab -e
```

Add:
```cron
# Run scraper every 6 hours
0 */6 * * * cd /opt/retail-os && /opt/retail-os/venv/bin/python scripts/run_dual_site_pipeline.py --max-pages 1000 --concurrency 10 >> /opt/retail-os/logs/scraper.log 2>&1

# Run enrichment daily at 2 AM
0 2 * * * cd /opt/retail-os && /opt/retail-os/venv/bin/python scripts/enrich_products.py >> /opt/retail-os/logs/enrichment.log 2>&1

# Cleanup old logs weekly
0 0 * * 0 find /opt/retail-os/logs -name "*.log" -mtime +30 -delete
```

---

## 🐳 Option 3: Docker Deployment

### Step 1: Build Image

```powershell
# Build
docker-compose build

# Test locally
docker-compose up
```

### Step 2: Deploy to Production

**Using Docker Compose:**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  retail_os:
    build: .
    image: retail_os:latest
    container_name: retail_os_prod
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - CONSUMER_KEY=${CONSUMER_KEY}
      - CONSUMER_SECRET=${CONSUMER_SECRET}
      - ACCESS_TOKEN=${ACCESS_TOKEN}
      - ACCESS_TOKEN_SECRET=${ACCESS_TOKEN_SECRET}
      - DATABASE_URL=sqlite:////app/data/retail.db
    restart: always
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```powershell
docker-compose -f docker-compose.prod.yml up -d
```

**Using Docker Swarm:**
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml retail-os
```

**Using Kubernetes:**
See `k8s/` directory for manifests (create if needed).

---

## 🔄 Backup Strategy

### Automated Backups

**Windows:**
```powershell
# backup.ps1
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "C:\RetailOS\backups\$timestamp"

# Create backup directory
New-Item -ItemType Directory -Path $backupDir -Force

# Backup database
Copy-Item "C:\RetailOS\trademe_store.db" "$backupDir\trademe_store.db"

# Backup media (if small enough)
Compress-Archive -Path "C:\RetailOS\data\media" -DestinationPath "$backupDir\media.zip"

# Backup .env
Copy-Item "C:\RetailOS\.env" "$backupDir\.env"

# Cleanup old backups (keep last 7 days)
Get-ChildItem "C:\RetailOS\backups" -Directory | 
    Where-Object {$_.CreationTime -lt (Get-Date).AddDays(-7)} | 
    Remove-Item -Recurse -Force
```

Schedule with Task Scheduler (daily at 3 AM).

**Linux:**
```bash
#!/bin/bash
# backup.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/retail-os/backups/$TIMESTAMP"

mkdir -p "$BACKUP_DIR"

# Backup database
cp /opt/retail-os/trademe_store.db "$BACKUP_DIR/"

# Backup media
tar -czf "$BACKUP_DIR/media.tar.gz" /opt/retail-os/data/media

# Backup .env
cp /opt/retail-os/.env "$BACKUP_DIR/"

# Cleanup old backups
find /opt/retail-os/backups -type d -mtime +7 -exec rm -rf {} +
```

Add to crontab:
```cron
0 3 * * * /opt/retail-os/backup.sh
```

---

## 📊 Monitoring & Alerts

### Health Checks

Create `healthcheck.py`:
```python
import requests
import smtplib
from email.mime.text import MIMEText

def check_dashboard():
    try:
        r = requests.get('http://localhost:8501/_stcore/health', timeout=5)
        return r.status_code == 200
    except:
        return False

def send_alert(message):
    # Configure SMTP settings
    msg = MIMEText(message)
    msg['Subject'] = 'Retail OS Alert'
    msg['From'] = 'alerts@yourcompany.com'
    msg['To'] = 'admin@yourcompany.com'
    
    # Send email (configure SMTP server)
    # s = smtplib.SMTP('smtp.gmail.com', 587)
    # s.send_message(msg)

if __name__ == '__main__':
    if not check_dashboard():
        send_alert('Dashboard is down!')
```

### Log Monitoring

Use tools like:
- **Windows**: Event Viewer, PRTG
- **Linux**: journalctl, Logwatch, ELK Stack
- **Cloud**: Azure Monitor, CloudWatch, Stackdriver

---

## 🔐 Security Hardening

1. **Firewall**: Only expose port 8501 (or 80/443 with reverse proxy)
2. **Authentication**: Add Streamlit authentication or nginx basic auth
3. **HTTPS**: Use Let's Encrypt with Caddy or Certbot
4. **Secrets**: Use Azure Key Vault or AWS Secrets Manager for production
5. **Updates**: Regularly update dependencies (`pip list --outdated`)

---

## 🚀 Post-Deployment

### Verify Deployment

1. **Dashboard**: Access http://your-server:8501
2. **Database**: Check tables exist and are populated
3. **Scrapers**: Manually trigger and verify logs
4. **Trade Me**: Test listing creation in sandbox mode first

### Monitoring Checklist

- [ ] Dashboard accessible
- [ ] Scrapers running on schedule
- [ ] Database growing with new products
- [ ] Logs being written
- [ ] Backups completing successfully
- [ ] No errors in logs
- [ ] Trade Me API calls succeeding

---

## 📞 Support & Troubleshooting

### Common Issues

**Service won't start:**
- Check logs in Event Viewer (Windows) or journalctl (Linux)
- Verify Python path and virtual environment
- Check file permissions

**Database locked:**
- Ensure only one process writes at a time
- Check WAL mode is enabled
- Restart services

**Scraper failures:**
- Check internet connectivity
- Verify supplier sites are accessible
- Review rate limiting settings

### Getting Help

- Review logs in `logs/` directory
- Check dashboard for error messages
- Consult `README.md` and `PRODUCTION_LAUNCH.md`

---

**Last Updated**: December 2025
