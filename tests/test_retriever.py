"""Unit tests for the HybridRetriever."""

import pytest
from src.loader import KnowledgeLoader
from src.retriever import HybridRetriever
from src.config import settings


@pytest.fixture
def retriever():
    loader = KnowledgeLoader(settings.CHUNKS_PATH)
    chunks = loader.load_chunks()
    return HybridRetriever(chunks)


def test_retriever_english_query(retriever):
    results = retriever.retrieve("Shatha Biladi oud sandalwood", top_k=3)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert "Shatha Biladi" in top_chunk.text or "shatha biladi" in top_chunk.text.lower()


def test_retriever_arabic_query(retriever):
    results = retriever.retrieve("شذى بلادي عطر العود", top_k=3)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert any(c in top_chunk.text for c in ["شذى", "بلادي", "العود", "Shatha"])


def test_retriever_boutiques_query(retriever):
    results = retriever.retrieve("boutiques Riyadh Jeddah Makkah Madinah", top_k=5)
    assert len(results) > 0
    assert any("Boutiques" in c.text or "boutique" in c.text.lower() for c, _ in results)
