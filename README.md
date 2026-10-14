# 💎 Mansam Luxury Fragrance AI Concierge

## WhatsApp Cloud API webhook

The endpoint `/api/whatsapp/webhook` verifies Meta's GET challenge and authenticates
POST events using `X-Hub-Signature-256`. It stores incoming messages and delivery
statuses in a deduplicated SQLite inbox. An optional worker sends the approved
`shop_now` English (`en`) template once per new incoming customer message, including
media messages. Status events, reactions, system events, and messages older than
24 hours do not trigger replies. The static Shop Now button is part of the template;
the image header must be supplied at send time. Auto replies are disabled by default.

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
5. Set `WHATSAPP_ACCESS_TOKEN` securely in Render (existing token with
   `whatsapp_business_messaging` access to this phone number), plus either
   `WHATSAPP_TEMPLATE_IMAGE_URL` (public HTTPS JPG/PNG; defaults to the Safaa Al Nada
   product image on ae.mansamworld.com) or
   `WHATSAPP_TEMPLATE_IMAGE_ID` (valid WhatsApp media ID). Then set
   `WHATSAPP_AUTO_REPLY_ENABLED=True` and restart the service. Keep the template
   name `shop_now`, language `en`, and API version `v25.0` unless intentionally
   changing the approved template/API version. Run one web process/instance for
   this SQLite-backed worker. Use a shared queue/database before scaling replicas.
6. Test signed webhook delivery and check the inbox on the server. Do not expose
   a public inbox viewer. Configure retention/access controls for customer data.
   Inbox `processed` states: 0 pending, 2 claimed/possibly sent, 1 Meta accepted,
   3 ignored/expired, -1 failed/uncertain. Failed or interrupted sends need manual
   review before retrying because Meta may have accepted a timed-out request.
   Meta's accepted response does not guarantee delivery; check status events.
   Changing a row to 0 can resend it. Do not reset states without checking delivery.
   Keep storage persistent or duplicate protection will be lost on redeployment.

No LLM is called and no message content is sent to OpenRouter by this worker.
Automatic replies may incur Meta marketing-template charges. It does not broadcast
to contacts or send proactive campaigns.

Run isolated tests with `python -m pytest tests/test_whatsapp.py tests/test_whatsapp_reply.py`.

### Supabase Free alternative

Keep Render auto replies disabled when using Supabase, so only one endpoint sends.
The separate function at `supabase/functions/whatsapp-webhook/index.ts` uses
Postgres instead of a Render disk. It answers the incoming question with at most
two short text lines. Matching perfumes appear as a media carousel with product
images and Shop Now buttons; one product uses a single image/URL-button message.
Support and greeting replies do not automatically send product promotions.
These are service-window replies, not proactive marketing templates.

1. Apply `supabase/migrations/202610130001_whatsapp_reply_events.sql` once. The new
   table has RLS enabled, no public/user policies, and service-role access only.
   It stores message IDs, recipient numbers, timestamps and send states, not text.
2. Deploy the function as `whatsapp-webhook`. Disable Supabase's JWT verification
   for this function only; Meta's `X-Hub-Signature-256` HMAC is checked by the
   handler instead. Obtain owner approval before configuring credentials/public
   webhook access. Do not expose service-role keys or add public table policies.
3. Set Edge Function secrets `META_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`,
   `WHATSAPP_ACCESS_TOKEN`, and `WHATSAPP_PHONE_NUMBER_ID=1307049029167597`.
   Add `WHATSAPP_AUTO_REPLY_ENABLED=true` only when ready to activate. API version
   defaults to `v25.0`. Built-in Supabase secrets provide database access.
   Keyword-based English/Arabic recommendations work without an AI key.
   No AI provider receives WhatsApp question text. Each question is matched
   independently; conversation history is not stored.
   Never promise stock, sale pricing or delivery dates from the static catalogue.
4. For project fpyaudimfmhthepqohdm, use callback
   `https://fpyaudimfmhthepqohdm.supabase.co/functions/v1/whatsapp-webhook`.
   Set the same verify token in Meta, subscribe the `messages` field and Mansam
   account, and complete Meta publishing requirements before production use.
5. Test with a customer who requests the reply. Duplicate inbound message IDs are
   suppressed by a database primary key. Old (>24h), reaction, system, unsupported,
   other-phone and error events do not send. Each distinct new customer message
   triggers a reply; status updates do not. This does not send outside the service
   window. Apply migration `202610130002_whatsapp_delivery_events.sql` to retain
   asynchronous delivery results. Stop requests receive a non-promotional response;
   this does not manage subscriptions to any separate marketing campaign.

Supabase background tasks are bounded by function runtime limits. A crash after
claiming or a send timeout can leave `claimed`/`uncertain` rows, which require
manual review against Meta delivery records before retrying. Do not clear the
table or reset rows casually; this can send duplicate messages. `accepted` means
Meta accepted the request, not confirmed delivery. Disabled-mode messages are
recorded as `disabled` and are not replayed on activation. Restrict database
access and set a customer-data retention policy. Free projects can pause after
inactivity, and free quotas apply; this is not an always-on availability guarantee.

Test the handler without credentials or real sends:
`node --test tests/whatsapp_supabase.test.mjs tests/whatsapp_recommendations.test.mjs` (Node 24+).
For the dashboard's single-file editor, concatenate `catalog.ts`, `reply.ts` and
`index.ts` in that order, removing their local import lines. CLI deployments use
the source modules directly.

### Marketing carousel review

`campaigns/mansam-floral-carousel.json` is the inactive three-card campaign draft.
The `whatsapp-template-admin` Edge Function submits that fixed draft to Meta using
the existing server-side WhatsApp token. It uploads public product images through
Meta's resumable upload API and returns only template ID/name/status. GET checks
status; POST creates the template only if that name/language is not already present.
It cannot send customer messages or approve a template on Meta's behalf.

Keep **Verify JWT with legacy secret ON** for this function. Supabase's gateway
verifies the JWT signature and expiration; the handler additionally requires the
project's service_role claim. Never disable gateway verification: the role check
is not a standalone signature verifier. Existing administrator JWTs can be used
privately in the dashboard tester. Do not put credentials in source or chat.
The customer webhook's separate HMAC authentication is unchanged.

After submission, wait for Meta's APPROVED status before campaign sends. The
campaign still needs opted-in recipients and an authenticated sender/scheduler.
Run `node --test tests/whatsapp_template_admin.test.mjs` to check submission and
administrator restrictions with mocked API calls.

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
