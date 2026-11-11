import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("RAG_MODEL", "claude-opus-5-5")
    data_dir: Path = Path(os.getenv("RAG_DATA_DIR", "data/raw"))
    storage_dir: Path = Path(os.getenv("RAG_STORAGE_DIR", "storage"))
    collection: str = os.getenv("RAG_COLLECTION", "documents")
    top_k: int = int(os.getenv("RAG_TOP_K", "5"))
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))


settings = Settings()
