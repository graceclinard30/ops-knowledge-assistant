import pytest

from rag_app.feedback import add_report, list_reports, set_status


def _report(db, **overrides):
    fields = dict(
        reporter="Sam",
        question="What are the release gates?",
        answer="Gate 1 is ...",
        sources=["05_test_strategy_and_release_gates.txt"],
        issue_type="Outdated",
        affected=["05_test_strategy_and_release_gates.txt"],
        description="Gate 3 was removed in the Q3 process update.",
        db_path=db,
    )
    fields.update(overrides)
    return add_report(**fields)


def test_add_and_list_roundtrip(tmp_path):
    db = tmp_path / "fb.db"
    rid = _report(db)
    [r] = list_reports(db_path=db)
    assert r["id"] == rid
    assert r["status"] == "open"
    assert r["affected"] == ["05_test_strategy_and_release_gates.txt"]
    assert r["description"].startswith("Gate 3")


def test_search_only_report_has_no_answer(tmp_path):
    db = tmp_path / "fb.db"
    _report(db, answer=None)
    assert list_reports(db_path=db)[0]["answer"] is None


def test_status_filter_and_update(tmp_path):
    db = tmp_path / "fb.db"
    first = _report(db)
    _report(db, description="Another issue")
    set_status(first, "resolved", db_path=db)
    assert [r["id"] for r in list_reports("resolved", db_path=db)] == [first]
    assert len(list_reports("open", db_path=db)) == 1


@pytest.mark.parametrize(
    "overrides", [{"description": "  "}, {"reporter": ""}, {"issue_type": "Typo"}]
)
def test_invalid_reports_rejected(tmp_path, overrides):
    with pytest.raises(ValueError):
        _report(tmp_path / "fb.db", **overrides)
