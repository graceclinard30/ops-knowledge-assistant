from rag_app.evaluate import doc_id_map, parse_scenarios, run

SAMPLE = """SCENARIO 1
Question: Is a receipt a payment?
Expected answer: No. Cite KB-003.

SCENARIO 2
Question: Can I upload PHI?
Expected answer: No. Cite KB-002 and KB-007.
"""


def test_parse_scenarios_extracts_questions_and_ids():
    s = parse_scenarios(SAMPLE)
    assert [x.question for x in s] == ["Is a receipt a payment?", "Can I upload PHI?"]
    assert s[1].expected_ids == ["KB-002", "KB-007"]


def test_run_scores_hits(tmp_path):
    data = tmp_path / "raw"
    data.mkdir()
    (data / "a.txt").write_text("DOCUMENT ID: KB-003\nreceipts", encoding="utf-8")
    (data / "b.txt").write_text("DOCUMENT ID: KB-009\nother", encoding="utf-8")
    assert doc_id_map(data) == {"a.txt": "KB-003", "b.txt": "KB-009"}
    scen = tmp_path / "s.txt"
    scen.write_text(SAMPLE, encoding="utf-8")

    def fake_search(q, k):  # Q1 finds KB-003 (hit); Q2 finds only KB-009 (miss)
        return [{"source": "a.txt" if "receipt" in q else "b.txt"}]

    assert run(scen, data, 5, fake_search) == 0.5
