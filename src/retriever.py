"""Hybrid search and retrieval engine for Mansam RAG (Dense ChromaDB + Sparse BM25)."""

import re
import logging
from typing import Dict, List, Optional, Tuple
from rank_bm25 import BM25Okapi
from src.models import Chunk
from src.vectordb import ChromaVectorDB

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines ChromaDB vector semantic search with BM25 lexical ranking."""

    def __init__(self, chunks: List[Chunk], vectordb: Optional[ChromaVectorDB] = None):
        self.chunks = chunks
        self.vectordb = vectordb
        self.tokenized_corpus = [self._tokenize(c.text) for c in chunks]
        self.bm25 = BM25Okapi(self.tokenized_corpus) if self.tokenized_corpus else None
        self._chunk_map: Dict[str, Chunk] = {c.chunk_id: c for c in chunks}
        logger.info(
            "Initialized HybridRetriever with %d BM25 chunks and VectorDB %s",
            len(chunks),
            "enabled" if vectordb else "disabled",
        )

    def _tokenize(self, text: str) -> List[str]:
        """Normalizes Arabic and English text into query tokens."""
        cleaned = re.sub(r"[إأآا]", "ا", text)
        cleaned = re.sub(r"[ىي]", "ي", cleaned)
        cleaned = re.sub(r"ة", "ه", cleaned)
        cleaned = re.sub(r"[^\w\s]", " ", cleaned.lower())
        tokens = [t for t in cleaned.split() if len(t) > 1]
        return tokens

    def retrieve_sparse(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """BM25 lexical retrieval."""
        if not self.bm25 or not self.chunks:
            return []
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [(c, 0.0) for c in self.chunks[:top_k]]

        doc_scores = self.bm25.get_scores(query_tokens)
        top_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:top_k]

        results = [(self.chunks[i], float(doc_scores[i])) for i in top_indices if doc_scores[i] > 0]
        if not results:
            results = [(self.chunks[i], float(doc_scores[i])) for i in top_indices]
        return results

    def retrieve_dense(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Tuple[Chunk, float]]:
        """ChromaDB vector semantic retrieval."""
        if not self.vectordb or self.vectordb.count() == 0:
            return []
        return self.vectordb.query(query, top_k=top_k, where=where)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        dense_weight: float = 0.5,
        where: Optional[Dict] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Hybrid retrieval combining dense vector similarity with sparse BM25 lexical ranking."""
        # If no vector DB available, use BM25
        if not self.vectordb or self.vectordb.count() == 0:
            return self.retrieve_sparse(query, top_k=top_k)

        # Retrieve candidates from both sources
        fetch_k = max(top_k * 3, 20)
        dense_results = self.retrieve_dense(query, top_k=fetch_k, where=where)
        sparse_results = self.retrieve_sparse(query, top_k=fetch_k)

        # Build lookup and score mappings
        chunk_lookup: Dict[str, Chunk] = {}
        dense_dict: Dict[str, float] = {}
        sparse_dict: Dict[str, float] = {}

        for chunk, score in dense_results:
            chunk_lookup[chunk.chunk_id] = chunk
            dense_dict[chunk.chunk_id] = score

        max_sparse = max([s for _, s in sparse_results], default=1.0)
        if max_sparse <= 0:
            max_sparse = 1.0
        for chunk, score in sparse_results:
            chunk_lookup[chunk.chunk_id] = chunk
            sparse_dict[chunk.chunk_id] = max(0.0, score / max_sparse)

        all_ids = set(dense_dict.keys()) | set(sparse_dict.keys())
        sparse_weight = 1.0 - dense_weight
        combined_scores: Dict[str, float] = {}

        for cid in all_ids:
            d_score = dense_dict.get(cid, 0.0)
            s_score = sparse_dict.get(cid, 0.0)
            combined_scores[cid] = (dense_weight * d_score) + (sparse_weight * s_score)

        sorted_cids = sorted(combined_scores.keys(), key=lambda cid: combined_scores[cid], reverse=True)[:top_k]
        return [(chunk_lookup[cid], combined_scores[cid]) for cid in sorted_cids]

    def filter_by_type(self, chunk_type: str) -> List[Chunk]:
        """Returns all chunks of a specific type (e.g., 'brand_booklet', 'ssot_record')."""
        return [c for c in self.chunks if c.type == chunk_type]
