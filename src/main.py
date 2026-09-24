"""FastAPI entry point and route controller for Mansam Concierge Suite."""

import logging
import re
from pathlib import Path
from typing import Dict, List
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from src.agent import ConciergeAgent
from src.config import settings
from src.loader import KnowledgeLoader
from src.models import ChatRequest, ChatResponse, GalaxyCategory, TicketRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mansam.main")

# Initialize app and components
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.retriever import HybridRetriever
from src.vectordb import ChromaVectorDB

loader = KnowledgeLoader(settings.CHUNKS_PATH)
chunks = loader.load_chunks()
vectordb = ChromaVectorDB()
# Automatically feed chunks on startup if collection is empty
if vectordb.count() == 0:
    vectordb.feed_from_jsonl()

search_engine = HybridRetriever(chunks, vectordb=vectordb)
agent = ConciergeAgent(search_engine)
galaxy_data = loader.load_galaxy_categories()

# Static assets directory
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root_index() -> FileResponse:
    """Serves the main luxury client interface."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="UI index.html not found.")
    return FileResponse(str(index_file))


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Handles bilingual conversational queries with RAG grounding."""
    try:
        return agent.chat(request)
    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/galaxy", response_model=List[GalaxyCategory])
async def galaxy_endpoint() -> List[GalaxyCategory]:
    """Returns the 7-mood Galaxy emotional classification data."""
    return galaxy_data


@app.post("/api/ticket")
async def create_ticket(req: TicketRequest) -> Dict[str, str]:
    """Generates a lead handover ticket and advisor dispatch link."""
    import uuid
    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    wa_number = settings.KSA_WHATSAPP.replace("+", "").replace(" ", "")
    wa_link = f"https://wa.me/{wa_number}?text=Mansam%20VIP%20Ticket%20{ticket_id}%20for%20{req.customer_name}"
    return {
        "ticket_id": ticket_id,
        "whatsapp_link": wa_link,
        "status": "created",
        "message": f"Ticket {ticket_id} created for {req.customer_name}. An advisor will reach out within 48h.",
    }


@app.get("/api/tts")
async def text_to_speech(text: str, lang: str = "ar") -> Response:
    """Provides high-fidelity streaming TTS audio for Arabic and English responses."""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text parameter is required.")

    # Clean markdown, URLs, and HTML tags
    clean = re.sub(r"<[^>]*>", "", text)
    clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
    clean = re.sub(r"https?://\S+", "", clean)
    clean = re.sub(r"[#_`~*]", "", clean).strip()

    tl = "ar" if lang.startswith("ar") else "en"
    
    # Split text into natural chunks for the TTS engine
    sentences = re.split(r"([.،؟!\n]+)", clean)
    parts: List[str] = []
    current = ""
    for segment in sentences:
        if len(current) + len(segment) < 180:
            current += segment
        else:
            if current.strip():
                parts.append(current.strip())
            current = segment
    if current.strip():
        parts.append(current.strip())

    audio_bytes = b""
    async with httpx.AsyncClient(timeout=10.0) as client:
        for p in parts[:5]:
            params = {"ie": "UTF-8", "q": p, "tl": tl, "client": "tw-ob"}
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                r = await client.get("https://translate.google.com/translate_tts", params=params, headers=headers)
                if r.status_code == 200:
                    audio_bytes += r.content
            except Exception as e:
                logger.warning("TTS chunk fetch warning: %s", e)

    if not audio_bytes:
        raise HTTPException(status_code=502, detail="Unable to generate TTS audio.")

    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.get("/api/health")
async def health_check() -> Dict[str, str]:
    """Reports system and index status."""
    return {
        "status": "healthy",
        "brand": settings.BRAND_EN,
        "bm25_chunks_indexed": str(len(chunks)),
        "chromadb_chunks_indexed": str(vectordb.count()),
        "chromadb_collection": vectordb.collection_name,
        "llm_provider": agent.provider,
        "llm_model": settings.OPENROUTER_MODEL if agent.provider == "openrouter" else "fallback",
    }


if __name__ == "__main__":
    uvicorn.run("src.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
