"""Load documents from disk and split them into overlapping chunks."""
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

SUPPORTED = {".txt", ".md", ".pdf"}


@dataclass
class Chunk:
    id: str
    text: str
    source: str


def read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Character-based splitter that prefers to break on paragraph/sentence boundaries."""
    if overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    text = text.strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            window = text[start:end]
            for sep in ("\n\n", "\n", ". ", " "):
                cut = window.rfind(sep)
                if cut > chunk_size // 2:
                    end = start + cut + len(sep)
                    break
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def load_chunks(data_dir: Path, chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        rel = path.relative_to(data_dir).as_posix()
        for i, piece in enumerate(split_text(read_file(path), chunk_size, overlap)):
            chunks.append(Chunk(id=f"{rel}::{i}", text=piece, source=rel))
    return chunks
