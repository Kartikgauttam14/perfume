# 🚀 Render Deployment Guide — Mansam Luxury Fragrance RAG Concierge

This document provides a step-by-step guide to deploying the **Mansam Luxury Fragrance RAG Concierge** on [Render.com](https://render.com).

---

## 📋 Prerequisites

1. A [Render.com](https://render.com) account.
2. A GitHub or GitLab repository containing this project codebase.
3. Your **OpenRouter API Key** (`sk-or-v1-...`).

---

## Option 1: Fast GUI Deployment (Recommended)

### Step 1: Push Code to GitHub
Ensure all code and knowledge chunks are committed and pushed:
```bash
git add .
git commit -m "Prepare codebase for Render deployment"
git push origin main
```

---

### Step 2: Create a New Web Service on Render
1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Click **"New +"** in the top-right corner and select **"Web Service"**.
3. Connect your Git repository (`RAG` / `mansam-concierge`).
4. Configure the service settings:

| Setting | Recommended Value |
|---|---|
| **Name** | `mansam-concierge` |
| **Region** | Select closest to target users (e.g., `Frankfurt` for Middle East / Europe) |
| **Branch** | `main` |
| **Root Directory** | Leave blank (root of repository) |
| **Runtime** | `Python` (or `Docker` if using Dockerfile) |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn src.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Starter` ($7/mo) or `Standard` (for production traffic) |

---

### Step 3: Configure Environment Variables
In the **"Environment Variables"** tab of your Render Web Service, add the following key-value pairs:

| Key | Value | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | `sk-or-v1-xxxxxxxxxxxxxxxx` | **(Secret)** Your OpenRouter API Key |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | OpenRouter model ID |
| `CHUNKS_FILE_PATH` | `./mansam_chunks.jsonl` | Path to SSOT chunks dataset |
| `SUMMARY_FILE_PATH` | `./mansam_chunks_summary.json` | Path to categories metadata |
| `HOST` | `0.0.0.0` | Bind address |
| `DEBUG` | `False` | Production mode |
| `PYTHON_VERSION` | `3.11.9` | Ensure Python 3.11+ is used |

---

### Step 4: Health Check Path
In the **Advanced Settings** section:
* **Health Check Path**: `/api/health`
* Render will automatically monitor this endpoint and handle zero-downtime restarts.

---

### Step 5: Click "Create Web Service"
* Render will clone the repository, install dependencies from `requirements.txt`, index the ChromaDB vector database, and start the Uvicorn ASGI server.
* Once the build completes, your app will be live at:
  `https://mansam-concierge.onrender.com`

---

## Option 2: 1-Click Deployment via `render.yaml` Blueprint

This repository includes a pre-configured [`render.yaml`](./render.yaml).

1. Go to [Render Blueprints](https://dashboard.render.com/blueprints).
2. Click **"New Blueprint Instance"**.
3. Select your repository.
4. Render will read `render.yaml`, configure all build settings, and prompt you to input `OPENROUTER_API_KEY`.
5. Click **"Apply"** to deploy.

---

## Option 3: Docker Runtime Deployment

If you prefer containerized deployment:
1. In Render, select **Runtime: Docker**.
2. Render will automatically detect the [`Dockerfile`](./Dockerfile) in the root folder.
3. Add the `OPENROUTER_API_KEY` environment variable.
4. Deploy!

---

## 🌐 Custom Domain & SSL Setup

1. In your Render Web Service dashboard, go to **"Settings"** $\rightarrow$ **"Custom Domains"**.
2. Add your domain (e.g. `concierge.mansamworld.com` or `chat.mansam.com`).
3. Update your DNS provider (Cloudflare, GoDaddy, Namecheap) with the provided `CNAME` or `A` records.
4. Render automatically provisions and renews a free **Let's Encrypt SSL/TLS certificate**.

---

## 🔍 Verification & Testing

Once deployed, verify the endpoints:
1. **Web Interface**: Open `https://your-service.onrender.com/` in your browser.
2. **API Health Check**: 
   ```bash
   curl -i https://your-service.onrender.com/api/health
   ```
3. **Chat Endpoint Test**:
   ```bash
   curl -X POST https://your-service.onrender.com/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What is Shatha Biladi?", "language": "en"}'
   ```
4. **Arabic Audio TTS**:
   ```bash
   curl -i "https://your-service.onrender.com/api/tts?text=أهلا+بك+في+منسم&lang=ar"
   ```

---

## 🛠️ Troubleshooting & Logs

* **Viewing Live Logs**: In the Render Dashboard, click the **"Logs"** tab to see real-time Uvicorn output, request logs, and error traces.
* **ChromaDB Initialization**: On first boot, the backend reads `mansam_chunks.jsonl` (586 chunks) and feeds the local Chroma collection automatically in $< 2$ seconds.
* **Cold Starts**: If using the Free tier, Render services sleep after 15 minutes of inactivity. Upgrade to the **Starter ($7/mo)** plan for 24/7 instant availability.
