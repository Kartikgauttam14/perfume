# ☁️ AWS Server Deployment Guide — Mansam Luxury Fragrance RAG Concierge

This comprehensive guide details how to deploy and operate the **Mansam Luxury Fragrance RAG Concierge** on **Amazon Web Services (AWS)** for high-availability, production-grade performance.

---

## 🏛️ Architecture Options

```
                    Internet (Clients)
                           │
                           ▼
                  AWS Route 53 (DNS)
                           │
                           ▼
               Let's Encrypt SSL (HTTPS:443)
                           │
                           ▼
                    Nginx Reverse Proxy
                           │
                           ▼
             Uvicorn / Systemd ASGI Daemon (Port 8000)
                           │
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
ChromaDB Vector Store               OpenRouter API (LLM)
(Local Persistent Disk)              (HTTPS External)
```

We cover two deployment strategies:
* **Option 1 (Recommended & Cost-Effective)**: **AWS EC2** (Ubuntu 24.04 LTS) with Nginx reverse proxy, Systemd daemon, and free Let's Encrypt SSL.
* **Option 2 (Serverless Container)**: **AWS App Runner / ECS Fargate** using Docker.

---

# Option 1: AWS EC2 Virtual Server (Complete Guide)

### Step 1: Launch an EC2 Instance
1. Go to **AWS Management Console** $\rightarrow$ **EC2** $\rightarrow$ **Launch Instance**.
2. Configure instance details:
   * **Name**: `mansam-concierge-prod`
   * **AMI**: `Ubuntu Server 24.04 LTS` (or `22.04 LTS`)
   * **Architecture**: `64-bit (x86)`
   * **Instance Type**: `t3.small` (2 vCPU, 2GB RAM) or `t3.medium` (for high concurrency)
   * **Key Pair**: Create or select an existing SSH key pair (`.pem` file)
   * **Storage**: `20 GiB gp3` SSD

3. **Security Group Rules (Firewall)**:
   * Allow **SSH (Port 22)**: From your IP (or trusted bastion)
   * Allow **HTTP (Port 80)**: From `0.0.0.0/0` (Anywhere)
   * Allow **HTTPS (Port 443)**: From `0.0.0.0/0` (Anywhere)

4. Click **"Launch Instance"**.

---

### Step 2: Connect to the Server & Install System Dependencies
Connect to your EC2 instance via SSH:
```bash
chmod 400 your-key.pem
ssh -i "your-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

Update system packages and install Python, pip, git, and Nginx:
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx curl
```

---

### Step 3: Clone the Repository & Configure Virtual Environment
```bash
# Navigate to web application directory
cd /var/www

# Clone repository (replace with your repo URL)
sudo git clone https://github.com/your-org/RAG.git mansam
sudo chown -R ubuntu:ubuntu /var/www/mansam
cd /var/www/mansam

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install all requirements
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 4: Configure Production Environment Variables
Create the production `.env` file:
```bash
nano /var/www/mansam/.env
```

Paste your production configuration:
```ini
# Server Settings
HOST=127.0.0.1
PORT=8000
DEBUG=False

# LLM Provider — OpenRouter (https://openrouter.ai)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Data Paths
CHUNKS_FILE_PATH=./mansam_chunks.jsonl
SUMMARY_FILE_PATH=./mansam_chunks_summary.json

# Brand Contacts
KSA_WHATSAPP=+966500000000
```
Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

### Step 5: Configure Systemd Service (Auto-restart & Background Daemon)
Create a systemd unit file so the application starts on boot and restarts automatically if it crashes:
```bash
sudo nano /etc/systemd/system/mansam.service
```

Add the following configuration:
```ini
[Unit]
Description=Mansam Luxury Fragrance RAG Concierge Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/mansam
EnvironmentFile=/var/www/mansam/.env
ExecStart=/var/www/mansam/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000 --workers 2

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mansam
sudo systemctl start mansam

# Check service status
sudo systemctl status mansam
```

---

### Step 6: Configure Nginx as Reverse Proxy
Create an Nginx server block configuration:
```bash
sudo nano /etc/nginx/sites-available/mansam
```

Add the following Nginx configuration (replace `yourdomain.com` with your actual domain name or EC2 public DNS):
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com; # or your EC2 Public IP

    # Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Static assets cache
    location /static/ {
        alias /var/www/mansam/static/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    # Proxy to FastAPI / Uvicorn Backend
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket and streaming timeout configs
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 90s;
        proxy_connect_timeout 90s;
    }
}
```

Enable the site and restart Nginx:
```bash
sudo ln -sf /etc/nginx/sites-available/mansam /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

### Step 7: Configure HTTPS with Free Let's Encrypt SSL
1. Point your domain's DNS `A Record` to your EC2 instance's **Elastic IP** (or Public IP).
2. Run Certbot to generate and install the SSL certificate:
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
3. Follow the interactive prompts. Certbot will configure auto-renewal via cron.

---

### Step 8: Configure Server Firewall (UFW)
```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

---

# Option 2: AWS App Runner (Serverless Container Deployment)

If you prefer a fully managed serverless container service with zero OS management:

### Step 1: Push Docker Image to Amazon ECR
```bash
# 1. Authenticate Docker with Amazon ECR
aws ecr get-login-password --region <YOUR_REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com

# 2. Create an ECR repository
aws ecr create-repository --repository-name mansam-concierge

# 3. Build and tag the Docker image
docker build -t mansam-concierge .
docker tag mansam-concierge:latest <ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/mansam-concierge:latest

# 4. Push to ECR
docker push <ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/mansam-concierge:latest
```

### Step 2: Deploy on AWS App Runner
1. Open **AWS App Runner** in the AWS Console $\rightarrow$ **Create Service**.
2. **Source**: Container registry $\rightarrow$ Select `Amazon ECR` $\rightarrow$ Choose `mansam-concierge:latest`.
3. **Deployment Settings**: Automatic.
4. **Port**: `8000`.
5. **Environment Variables**: Add `OPENROUTER_API_KEY`, `OPENROUTER_MODEL=openai/gpt-4o-mini`.
6. Click **"Create & Deploy"**.
7. App Runner provides an automated HTTPS domain with auto-scaling based on incoming requests.

---

## 🔄 Deployment Automation & Updating the App

To deploy updates easily on EC2, create a deployment script `/var/www/mansam/deploy.sh`:

```bash
#!/bin/bash
set -e

echo "=== Pulling latest changes from Git ==="
cd /var/www/mansam
git pull origin main

echo "=== Updating Python dependencies ==="
source .venv/bin/activate
pip install -r requirements.txt

echo "=== Restarting Mansam Service ==="
sudo systemctl restart mansam

echo "=== Checking Service Status ==="
sudo systemctl status mansam --no-pager

echo "=== Deployment Completed Successfully! ==="
```

Make it executable:
```bash
chmod +x /var/www/mansam/deploy.sh
```
Whenever you update your code, simply run `./deploy.sh` on the server!

---

## 📊 Monitoring & Log Management

| Action | Command |
|---|---|
| **View Live App Logs** | `sudo journalctl -u mansam -f` |
| **View Nginx Access Logs** | `sudo tail -f /var/log/nginx/access.log` |
| **View Nginx Error Logs** | `sudo tail -f /var/log/nginx/error.log` |
| **Restart Application** | `sudo systemctl restart mansam` |
| **Test Health Endpoint** | `curl http://localhost:8000/api/health` |
