# 💎 Mansam Luxury Fragrance AI Concierge

## WhatsApp Cloud API webhook

The endpoint `/api/whatsapp/webhook` verifies Meta's GET challenge and authenticates
POST events using `X-Hub-Signature-256`. It stores incoming messages and delivery
statuses in a deduplicated SQLite inbox. It does not send automatic replies or
marketing messages yet; a worker and conversation policy must be connected before
enabling the concierge on WhatsApp. No access token is needed for this ingress.

1. Deploy the changed files to the existing Render service.
2. In Render environment settings, set `WHATSAPP_VERIFY_TOKEN` to a random secret,
   `META_APP_SECRET` to the existing Mansam Perfume app secret, and
   `WHATSAPP_PHONE_NUMBER_ID` to `1307049029167597`. Keep all secrets out of GitHub
   and chat. Set `WHATSAPP_INBOX_PATH` to a location on an existing persistent disk,
   such as `/var/data/whatsapp.sqlite3`. Render's ordinary filesystem is ephemeral;
   without persistent storage, events will be lost on restart/redeploy. Adding a
   paid disk or changing the service plan requires the owner's approval.
3. After deployment, set Meta's callback to
   `https://perfume-p6gi.onrender.com/api/whatsapp/webhook` and use the same verify
   token. Click Verify and save, subscribe to the `messages` field and the Mansam
   messaging account. Subscribing exposes customer events to this server and must
   be approved by the owner.
4. Complete Meta's publish requirements before receiving production webhooks.
   Confirm publishing with the owner; business verification alone is insufficient.
5. Test signed webhook delivery and check the inbox on the server. Do not expose
   a public inbox viewer. Configure retention/access controls for customer data.

Run isolated webhook tests with `python -m pytest tests/test_whatsapp.py`.

> An intelligent, bilingual AI Concierge & Discovery Suite for **Mansam Fine Fragrances** (Kingdom of Saudi Arabia), built on Retrieval-Augmented Generation (RAG) directly grounded in the brand's Single Source of Truth (SSOT).

---

## 📖 Features

- **🏛️ Grounded in SSOT**: Uses 586 curated knowledge chunks covering perfume notes, Al-Kindi perfumery philosophy, pricing, boutique locations, and objection handling.
- **✨ "The Galaxy" Emotional Discovery**: Recommends signature fragrances based on 7 core emotional moods (*Nobility, Pride, Pleasure, Passion, Generosity, Happiness, Desire*).
- **🇸🇦 Bilingual & Culturally Tuned**: Seamlessly switches between refined **Saudi/Khaleeji Arabic** and elegant **English**.
- **🛡️ Strict Guardrails**: Eliminates hallucinations, enforces exact official pricing, prohibits competitor criticism, and follows Saudi hospitality modesty norms.
- **🎫 Concierge Ticket Handover**: Implements BANTQ customer qualification and instant WhatsApp advisor handoff.

---

## 🏗️ Architecture

Please see the comprehensive [`SYSTEM_ARCHITECTURE.md`](file:///k:/projects/RAG/SYSTEM_ARCHITECTURE.md) for full diagrams, sequence flows, data pipeline schemas, and component breakdown.

---

## 🚀 Quickstart & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set your API keys:
```bash
cp .env.example .env
```

### 3. Ingest Chunks into ChromaDB Vector DB (Optional / Automated on Startup)
```bash
python -m src.vectordb
```

### 4. Run the Backend API & Web App
```bash
python -m uvicorn src.main:app --reload --port 8000
```
Open your browser at `http://localhost:8000` to interact with the luxury concierge UI.

---

## 📂 Project Structure

```
k:/projects/RAG/
├── SYSTEM_ARCHITECTURE.md       # Full architecture & design specifications
├── DEVELOPMENT_RULES.md         # Development guidelines and coding standards
├── README.md                     # Project overview and runbook
├── requirements.txt              # Python libraries (FastAPI, ChromaDB, etc.)
├── .env.example                  # Environment template
├── mansam_chunks.jsonl           # 586 knowledge chunks
├── mansam_chunks_summary.json    # Summary metrics
├── chroma_db/                    # Persistent ChromaDB vector storage
├── src/                          # Application source code
│   ├── config.py                 # App configuration & SSOT constants
│   ├── models.py                 # Pydantic schemas & Dataclasses
│   ├── loader.py                 # JSONL knowledge loader & deduplicator
│   ├── vectordb.py               # ChromaDB Vector Store & batch ingestion
│   ├── retriever.py              # Hybrid (ChromaDB Dense + BM25 Sparse) retriever
│   ├── agent.py                  # Concierge AI Agent with bilingual guardrails
│   └── main.py                   # FastAPI app & REST endpoints
├── static/                       # Luxury bilingual UI (HTML, CSS, JS)
└── tests/                        # Pytest unit & integration test suite
```
