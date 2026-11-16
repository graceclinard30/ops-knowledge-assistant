"""Retrieval evaluation: does the expected document appear in the top-k results?

Uses the KB-008 scenario file (kept OUT of the index to avoid answer leakage).
Runs fully locally - no LLM calls.
"""
import re
from dataclasses import dataclass
from pathlib import Path

DOC_ID = re.compile(r"KB-\d{3}")


@dataclass
class Scenario:
    question: str
    expected_ids: list[str]


def parse_scenarios(text: str) -> list[Scenario]:
    """Pull each 'Question:' and the KB ids cited on its 'Expected answer:' line."""
    scenarios = []
    question = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Question:"):
            question = line.removeprefix("Question:").strip()
        elif line.startswith("Expected answer:") and question:
            scenarios.append(Scenario(question, DOC_ID.findall(line)))
            question = None
    return scenarios


def doc_id_map(data_dir: Path) -> dict[str, str]:
    """Map source file name (as stored in the index) -> its 'DOCUMENT ID: KB-xxx' header."""
    ids = {}
    for path in data_dir.rglob("*.txt"):
        m = re.search(r"DOCUMENT ID:\s*(KB-\d{3})", path.read_text(encoding="utf-8", errors="ignore"))
        if m:
            ids[path.relative_to(data_dir).as_posix()] = m.group(1)
    return ids


def run(scenario_file: Path, data_dir: Path, k: int, search) -> float:
    """Print a per-question report and return Hit@k (share of questions with an expected doc in top k)."""
    scenarios = parse_scenarios(scenario_file.read_text(encoding="utf-8"))
    id_of = doc_id_map(data_dir)
    if any(sid == "KB-008" for sid in id_of.values()):
        print("WARNING: KB-008 (the answer key) is in the index - results are not valid.\n")
    hits = 0
    stale: set[str] = set()
    for i, s in enumerate(scenarios, start=1):
        results = search(s.question, k)
        stale |= {h["source"] for h in results if h["source"] not in id_of}
        retrieved = list(dict.fromkeys(id_of.get(h["source"], h["source"]) for h in results))
        hit = any(e in retrieved for e in s.expected_ids)
        hits += hit
        print(f"[{'HIT ' if hit else 'MISS'}] Q{i}: {s.question}")
        print(f"        expected {', '.join(s.expected_ids)} | retrieved {', '.join(retrieved)}")
    score = hits / len(scenarios) if scenarios else 0.0
    print(f"\nHit@{k}: {hits}/{len(scenarios)} = {score:.0%}")
    if stale:
        print(
            f"WARNING: the index returned files not in {data_dir} ({', '.join(sorted(stale))}). "
            "The index is stale - run `python -m rag_app ingest` and re-evaluate."
        )
    return score
