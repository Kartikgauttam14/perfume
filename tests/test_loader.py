"""Unit tests for knowledge loader and chunk deduplication."""

import pytest
from src.loader import KnowledgeLoader
from src.config import settings


def test_knowledge_loader_loads_chunks():
    loader = KnowledgeLoader(settings.CHUNKS_PATH)
    chunks = loader.load_chunks()
    assert len(chunks) == 586
    assert all(c.chunk_id for c in chunks)
    assert all(c.text for c in chunks)


def test_chunk_ids_are_unique():
    loader = KnowledgeLoader(settings.CHUNKS_PATH)
    chunks = loader.load_chunks()
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)), "Deduplication failed: Duplicate chunk IDs exist"


def test_galaxy_categories_count():
    loader = KnowledgeLoader(settings.CHUNKS_PATH)
    categories = loader.load_galaxy_categories()
    assert len(categories) == 7
    expected_ids = {"nobility", "pride", "pleasure", "passion", "generosity", "happiness", "desire"}
    assert set(c.id for c in categories) == expected_ids
