"""Vector store wrapper. Uses Chroma's built-in local embedding model (no extra API key)."""
import chromadb

from .config import settings
from .loaders import Chunk


def _client():
    return chromadb.PersistentClient(path=str(settings.storage_dir))


def get_collection():
    return _client().get_or_create_collection(settings.collection)


def reset_collection() -> None:
    """Delete the whole index so a rebuild doesn't keep passages from removed/edited files."""
    client = _client()
    if settings.collection in [c if isinstance(c, str) else c.name for c in client.list_collections()]:
        client.delete_collection(settings.collection)


def count() -> int:
    return get_collection().count()


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
