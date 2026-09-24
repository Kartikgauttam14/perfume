"""Unit and integration tests for ChromaVectorDB and Hybrid Retrieval."""

import pytest
from pathlib import Path
from src.config import settings
from src.loader import KnowledgeLoader
from src.models import Chunk
from src.retriever import HybridRetriever
from src.vectordb import ChromaVectorDB


@pytest.fixture(scope="module")
def vectordb(tmp_path_factory):
    """Provides an isolated ChromaVectorDB instance populated with real test chunks."""
    temp_dir = tmp_path_factory.mktemp("chroma_test_db")
    db = ChromaVectorDB(
        persist_dir=temp_dir,
        collection_name="test_mansam_knowledge",
    )
    # Feed chunks from JSONL
    loader = KnowledgeLoader(settings.CHUNKS_PATH)
    chunks = loader.load_chunks()
    db.add_chunks(chunks)
    return db


def test_vectordb_contains_all_chunks(vectordb):
    """Ensures all 586 chunks are indexed in ChromaDB."""
    assert vectordb.count() == 586


def test_vectordb_english_semantic_query(vectordb):
    """Tests dense semantic search for English perfume query."""
    results = vectordb.query("What is the story of Al-Kindi and perfumery?", top_k=3)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert score > 0.0
    assert "Al-Kindi" in top_chunk.text or "Kindi" in top_chunk.text or "perfumery" in top_chunk.text.lower()


def test_vectordb_arabic_semantic_query(vectordb):
    """Tests dense semantic search for Arabic query."""
    results = vectordb.query("ما هو عطر شذى بلادي ومكوناته؟", top_k=5)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert score > 0.0
    # Dense search matches Arabic knowledge chunks (phrases/catalog)
    assert any(c.metadata.get("language") == "AR" or "Arabic" in c.text or "عطر" in c.text for c, _ in results)


def test_vectordb_metadata_filter(vectordb):
    """Tests querying with metadata filters (e.g. document or type)."""
    where_filter = {"type": "brand_booklet"}
    results = vectordb.query("fragrance belonging", top_k=5, where=where_filter)
    assert len(results) > 0
    for chunk, _ in results:
        assert chunk.type == "brand_booklet"


def test_vectordb_get_single_chunk(vectordb):
    """Tests fetching a chunk directly by ID."""
    sample_id = "pdf::Mansam Booklet Spreads-EN::p2"
    chunk = vectordb.get_chunk(sample_id)
    assert chunk is not None
    assert chunk.chunk_id == sample_id
    assert "Mansam symbolizes" in chunk.text


def test_hybrid_retriever_combines_dense_and_sparse(vectordb):
    """Tests HybridRetriever with both BM25 and ChromaVectorDB."""
    loader = KnowledgeLoader(settings.CHUNKS_PATH)
    chunks = loader.load_chunks()
    retriever = HybridRetriever(chunks, vectordb=vectordb)

    results = retriever.retrieve("Shatha Biladi sandalwood oud", top_k=5)
    assert len(results) == 5
    top_chunk, score = results[0]
    assert "Shatha Biladi" in top_chunk.text or "shatha biladi" in top_chunk.text.lower()


def test_hybrid_retriever_arabic(vectordb):
    """Tests HybridRetriever with Arabic query."""
    loader = KnowledgeLoader(settings.CHUNKS_PATH)
    chunks = loader.load_chunks()
    retriever = HybridRetriever(chunks, vectordb=vectordb)

    results = retriever.retrieve("شذى بلادي عطر العود", top_k=5)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert any(c in top_chunk.text for c in ["شذى", "بلادي", "العود", "Shatha"])

