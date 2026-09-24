"""
OpenRouter API Performance Test for Mansam RAG Concierge.
Tests connection, response quality, latency, and bilingual capabilities.
"""

import time
import sys
import os

# Load .env first
from dotenv import load_dotenv
load_dotenv()

from src.config import settings
from src.loader import KnowledgeLoader
from src.vectordb import ChromaVectorDB
from src.retriever import HybridRetriever
from src.agent import ConciergeAgent
from src.models import ChatRequest


# ── Colour helpers ──────────────────────────────────────────────────────────
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def hr(char="─", n=70):
    print(char * n)

def section(title):
    print(f"\n{BOLD}{CYAN}{'━' * 70}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'━' * 70}{RESET}\n")


# ── 1. Config sanity check ───────────────────────────────────────────────────
section("1 · OpenRouter Configuration")
key = settings.OPENROUTER_API_KEY
masked = key[:12] + "..." + key[-6:] if key else "NOT SET"
print(f"  API Key   : {GREEN}{masked}{RESET}")
print(f"  Model     : {GREEN}{settings.OPENROUTER_MODEL}{RESET}")
print(f"  Base URL  : {GREEN}{settings.OPENROUTER_BASE_URL}{RESET}")

if not key:
    print(f"\n{RED}✗ OPENROUTER_API_KEY is not set in .env — aborting.{RESET}")
    sys.exit(1)


# ── 2. Raw OpenRouter ping ───────────────────────────────────────────────────
section("2 · Raw API Connection Test")
from openai import OpenAI

client = OpenAI(api_key=settings.OPENROUTER_API_KEY, base_url=settings.OPENROUTER_BASE_URL)

t0 = time.perf_counter()
try:
    ping = client.chat.completions.create(
        model=settings.OPENROUTER_MODEL,
        messages=[{"role": "user", "content": "Reply with exactly: PONG"}],
        temperature=0,
        max_tokens=10,
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    reply_text = ping.choices[0].message.content.strip()
    print(f"  {GREEN}✔ Connected{RESET}  →  '{reply_text}'")
    print(f"  Latency   : {YELLOW}{latency_ms:.0f} ms{RESET}")
    usage = ping.usage
    if usage:
        print(f"  Tokens    : prompt={usage.prompt_tokens}, completion={usage.completion_tokens}")
except Exception as e:
    print(f"  {RED}✗ Connection failed: {e}{RESET}")
    sys.exit(1)


# ── 3. Build full RAG pipeline ───────────────────────────────────────────────
section("3 · Initialising RAG Pipeline")

t0 = time.perf_counter()
loader = KnowledgeLoader(settings.CHUNKS_PATH)
chunks = loader.load_chunks()
t_load = (time.perf_counter() - t0) * 1000
print(f"  {GREEN}✔ Loaded{RESET} {len(chunks)} chunks  ({t_load:.0f} ms)")

t0 = time.perf_counter()
vectordb = ChromaVectorDB()
t_chroma = (time.perf_counter() - t0) * 1000
print(f"  {GREEN}✔ ChromaDB{RESET} ready  — {vectordb.count()} vectors  ({t_chroma:.0f} ms)")

t0 = time.perf_counter()
retriever = HybridRetriever(chunks, vectordb=vectordb)
t_bm25 = (time.perf_counter() - t0) * 1000
print(f"  {GREEN}✔ Hybrid Retriever{RESET} BM25 + dense  ({t_bm25:.0f} ms)")

agent = ConciergeAgent(retriever)
print(f"  {GREEN}✔ ConciergeAgent{RESET} provider = '{agent.provider}'  model = '{settings.OPENROUTER_MODEL}'")


# ── 4. Benchmark queries ─────────────────────────────────────────────────────
section("4 · End-to-End RAG Benchmark")

QUERIES = [
    ("EN · Product",    "en", "Tell me about Shatha Biladi — its notes and the mood it represents."),
    ("EN · Price",      "en", "How much does an Oud Collection EDP cost and what is the free gift offer?"),
    ("EN · Boutiques",  "en", "Where are the Mansam boutiques located in Saudi Arabia?"),
    ("EN · Galaxy",     "en", "What is the Mansam Galaxy system and how does Al-Kindi's philosophy inspire it?"),
    ("AR · منتج",       "ar", "حدثني عن عطر شذى بلادي ومكوناته العطرية."),
    ("AR · سعر",        "ar", "ما هو سعر عطور مجموعة العود وما هو عرض الـ 12 مل المجاني؟"),
]

results = []
for label, lang, query in QUERIES:
    req = ChatRequest(message=query, language=lang)
    t0 = time.perf_counter()
    res = agent.chat(req)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    reply_preview = res.reply.replace("\n", " ")[:120]
    products_found = len(res.products)
    product_url = res.suggested_product_url or "—"

    results.append({
        "label": label, "latency_ms": elapsed_ms,
        "lang": res.language, "sources": len(res.sources),
        "products": products_found, "url": product_url,
        "reply": reply_preview,
    })

    status = GREEN + "✔" + RESET
    print(f"  {status}  {BOLD}{label}{RESET}")
    print(f"     Query   : {DIM}{query[:80]}{RESET}")
    print(f"     Reply   : {reply_preview}...")
    print(f"     Latency : {YELLOW}{elapsed_ms:.0f} ms{RESET}  |  Sources: {res.sources[0] if res.sources else '—'}  |  Products: {products_found}")
    if res.suggested_product_url:
        print(f"     Shop URL: {CYAN}{res.suggested_product_url}{RESET}")
    print()


# ── 5. Summary table ─────────────────────────────────────────────────────────
section("5 · Performance Summary")

latencies = [r["latency_ms"] for r in results]
avg  = sum(latencies) / len(latencies)
best = min(latencies)
worst = max(latencies)

print(f"  {'Query':<22} {'Latency':>10}  {'Sources':>8}  {'Products':>9}")
hr()
for r in results:
    bar_len = int(r["latency_ms"] / 100)
    bar = "█" * min(bar_len, 30)
    colour = GREEN if r["latency_ms"] < 3000 else YELLOW if r["latency_ms"] < 6000 else RED
    print(f"  {r['label']:<22} {colour}{r['latency_ms']:>7.0f} ms{RESET}  {r['sources']:>8}  {r['products']:>9}  {colour}{bar}{RESET}")

hr()
print(f"  {'Average':<22} {BOLD}{avg:>7.0f} ms{RESET}")
print(f"  {'Best':<22} {GREEN}{best:>7.0f} ms{RESET}")
print(f"  {'Worst':<22} {RED}{worst:>7.0f} ms{RESET}")
print()
print(f"  Model     : {BOLD}{settings.OPENROUTER_MODEL}{RESET}")
print(f"  Provider  : {BOLD}{agent.provider}{RESET}")
print(f"  Chunks DB : {vectordb.count()} vectors in ChromaDB")
print(f"  BM25 Idx  : {len(chunks)} chunks")
print(f"\n  {GREEN}All queries completed successfully.{RESET}\n")
