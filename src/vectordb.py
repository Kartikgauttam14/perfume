"""ChromaDB Vector Database implementation for Mansam RAG."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import chromadb
from chromadb.api.models.Collection import Collection

from src.config import settings
from src.loader import KnowledgeLoader
from src.models import Chunk

logger = logging.getLogger(__name__)


class ChromaVectorDB:
    """Manages persistent ChromaDB vector storage, chunk ingestion, and similarity search."""

    def __init__(
        self,
        persist_dir: Optional[Union[str, Path]] = None,
        collection_name: Optional[str] = None,
        distance_metric: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        self.persist_dir = Path(persist_dir or settings.CHROMA_PERSIST_DIRECTORY)
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.distance_metric = distance_metric or settings.CHROMA_DISTANCE_METRIC

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.embedding_function = embedding_function

        # Initialize or retrieve collection
        metadata = {"hnsw:space": self.distance_metric}
        if self.embedding_function is not None:
            self.collection: Collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata=metadata,
                embedding_function=self.embedding_function,
            )
        else:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata=metadata,
            )
        logger.info(
            "ChromaDB initialized at '%s' (collection: '%s', count: %d)",
            self.persist_dir,
            self.collection_name,
            self.collection.count(),
        )

    def _sanitize_metadata(self, chunk: Chunk) -> Dict[str, Union[str, int, float, bool]]:
        """Converts chunk metadata into ChromaDB-compatible primitive types."""
        loc = chunk.location or {}
        meta = chunk.metadata or {}

        # Safely extract primitive values for direct query filtering
        page = int(loc["page"]) if loc.get("page") is not None and isinstance(loc.get("page"), (int, float)) else -1
        row = int(loc["row"]) if loc.get("row") is not None and isinstance(loc.get("row"), (int, float)) else -1
        language = str(meta.get("language", "auto"))
        document = str(meta.get("document", ""))

        sanitized: Dict[str, Union[str, int, float, bool]] = {
            "source": str(chunk.source or "unknown"),
            "type": str(chunk.type or "general"),
            "language": language,
            "document": document,
            "page": page,
            "row": row,
            "location_json": json.dumps(loc, ensure_ascii=False),
            "metadata_json": json.dumps(meta, ensure_ascii=False),
        }
        return sanitized

    def _deserialize_chunk(self, doc_id: str, document: str, meta: Optional[Dict[str, Any]]) -> Chunk:
        """Reconstructs a rich Chunk object from ChromaDB record."""
        meta = meta or {}
        location = json.loads(meta.get("location_json", "{}")) if "location_json" in meta else {}
        metadata = json.loads(meta.get("metadata_json", "{}")) if "metadata_json" in meta else {}

        return Chunk(
            chunk_id=doc_id,
            source=meta.get("source", "unknown"),
            type=meta.get("type", "general"),
            text=document or "",
            location=location,
            metadata=metadata,
        )

    def add_chunks(self, chunks: List[Chunk], batch_size: int = 100) -> int:
        """Feeds and upserts a list of chunks into ChromaDB in batches."""
        if not chunks:
            return 0

        total_upserted = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            ids = [c.chunk_id for c in batch]
            documents = [c.text for c in batch]
            metadatas = [self._sanitize_metadata(c) for c in batch]

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            total_upserted += len(batch)
            logger.info("Upserted batch %d-%d of %d chunks to ChromaDB", i + 1, i + len(batch), len(chunks))

        return total_upserted

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Searches ChromaDB for chunks semantically similar to query_text."""
        if self.count() == 0 or not query_text.strip():
            return []

        kwargs: Dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": min(top_k, self.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        if where_document:
            kwargs["where_document"] = where_document

        res = self.collection.query(**kwargs)

        results: List[Tuple[Chunk, float]] = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0]

        for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
            chunk = self._deserialize_chunk(doc_id, doc, meta)
            # For cosine distance (range 0 to 2), cosine similarity = 1 - (dist / 2) or 1 - dist
            similarity = max(0.0, 1.0 - float(dist)) if dist is not None else 1.0
            results.append((chunk, similarity))

        return results

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Retrieves a single chunk by ID."""
        res = self.collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        ids = res.get("ids", [])
        if not ids:
            return None
        doc = res.get("documents", [""])[0]
        meta = res.get("metadatas", [{}])[0]
        return self._deserialize_chunk(ids[0], doc, meta)

    def count(self) -> int:
        """Returns the total number of chunks currently indexed in ChromaDB."""
        return self.collection.count()

    def delete_chunks(self, chunk_ids: List[str]) -> None:
        """Deletes chunks by their IDs."""
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)

    def reset(self) -> None:
        """Empties the current collection."""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": self.distance_metric},
        )
        logger.info("ChromaDB collection '%s' reset successfully.", self.collection_name)

    def feed_from_jsonl(self, file_path: Optional[Path] = None, force_reload: bool = False) -> int:
        """Reads chunks from JSONL file and ingests them into ChromaDB."""
        path = file_path or settings.CHUNKS_PATH
        loader = KnowledgeLoader(path)
        chunks = loader.load_chunks()

        if force_reload:
            self.reset()

        # If already populated and not force_reload, skip unless counts differ
        if not force_reload and self.count() >= len(chunks):
            logger.info("ChromaDB already contains %d chunks. Skipping ingestion.", self.count())
            return self.count()

        logger.info("Feeding %d chunks from %s into ChromaDB...", len(chunks), path)
        count = self.add_chunks(chunks)
        logger.info("Successfully fed %d chunks into ChromaDB.", count)
        return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = ChromaVectorDB()
    fed = db.feed_from_jsonl(force_reload=True)
    print(f"Total chunks in ChromaDB: {db.count()}")
    sample_query = "What is the story of Mansam and Al-Kindi?"
    matches = db.query(sample_query, top_k=3)
    print(f"\nSample Query: {sample_query}")
    for idx, (c, score) in enumerate(matches, 1):
        print(f"{idx}. [{c.chunk_id}] (Score: {score:.4f}): {c.text[:120]}...")
