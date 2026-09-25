"""Unit and integration tests for ConciergeAgent."""

import pytest
from src.agent import ConciergeAgent
from src.config import settings
from src.loader import KnowledgeLoader
from src.models import ChatRequest
from src.retriever import HybridRetriever


@pytest.fixture
def agent():
    loader = KnowledgeLoader(settings.CHUNKS_PATH)
    chunks = loader.load_chunks()
    retriever = HybridRetriever(chunks)
    return ConciergeAgent(retriever)


def test_language_detection(agent):
    assert agent.detect_language("Tell me about the fragrance collection") == "en"
    assert agent.detect_language("ما هي أسعار عطور منسم؟") == "ar"


def test_chat_english_response(agent):
    req = ChatRequest(message="What is the story of Mansam and Al-Kindi?")
    res = agent.chat(req)
    assert res.reply is not None
    assert len(res.reply) > 20
    assert res.language == "en"
    assert len(res.sources) > 0


def test_chat_arabic_response(agent):
    req = ChatRequest(message="حدثني عن عطر شذى بلادي")
    res = agent.chat(req)
    assert res.reply is not None
    assert len(res.reply) > 20
    assert res.language == "ar"
    assert len(res.sources) > 0


def test_chat_returns_suggested_product_url(agent):
    """When a product is mentioned, chat() returns its direct store URL."""
    req = ChatRequest(message="Tell me about Shatha Biladi")
    res = agent.chat(req)
    assert res.suggested_product_url is not None
    assert "mansamworld.com" in res.suggested_product_url
    assert res.whatsapp_link is None


def test_build_ticket_link(agent):
    """_build_ticket_link() still produces a valid WhatsApp VIP URL for the /api/ticket endpoint."""
    ticket_id, wa_link = agent._build_ticket_link()
    assert ticket_id.startswith("TICK-")
    assert "wa.me" in wa_link
    assert ticket_id in wa_link


def test_off_topic_filter_english(agent):
    """Off-topic non-perfume queries are politely declined and steered back to Mansam."""
    req = ChatRequest(message="Write a python script to solve quadratic equations", language="en")
    res = agent.chat(req)
    assert any(w in res.reply.lower() for w in ["fragrance", "perfume", "mansam", "specialize", "scent"])


def test_off_topic_filter_arabic(agent):
    """Arabic off-topic non-perfume queries are politely declined and steered back to Mansam."""
    req = ChatRequest(message="ما هي عاصمة إيطاليا؟", language="ar")
    res = agent.chat(req)
    assert any(w in res.reply for w in ["عطور", "مَنسم", "منسم", "أعتذر", "المستشار العطري"])

