import pytest

from rag_app.loaders import load_chunks, split_text


def test_short_text_is_one_chunk():
    assert split_text("hello world", chunk_size=100, overlap=10) == ["hello world"]


def test_long_text_is_split_with_bounded_size():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = split_text(text, chunk_size=200, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_overlap_must_be_smaller_than_chunk():
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=10, overlap=10)


def test_load_chunks_reads_supported_files(tmp_path):
    (tmp_path / "a.md").write_text("Alpha doc", encoding="utf-8")
    (tmp_path / "skip.csv").write_text("x,y", encoding="utf-8")
    chunks = load_chunks(tmp_path, chunk_size=100, overlap=10)
    assert [c.source for c in chunks] == ["a.md"]
    assert chunks[0].id == "a.md::0"
