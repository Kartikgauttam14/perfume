# 💎 Mansam Luxury Fragrance AI Concierge

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
