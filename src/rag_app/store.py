"""Vector store wrapper. Uses Chroma's built-in local embedding model (no extra API key)."""
import chromadb

from .config import settings
from .loaders import Chunk


def get_collection():
    client = chromadb.PersistentClient(path=str(settings.storage_dir))
    return client.get_or_create_collection(settings.collection)


def add_chunks(chunks: list[Chunk], batch_size: int = 100) -> None:
    collection = get_collection()
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.upsert(
            ids=[c.id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[{"source": c.source} for c in batch],
        )


def search(query: str, k: int | None = None) -> list[dict]:
    result = get_collection().query(query_texts=[query], n_results=k or settings.top_k)
    return [
        {"text": doc, "source": meta["source"], "distance": dist}
        for doc, meta, dist in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]
