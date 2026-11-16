"""Streamlit web UI for rag_app. Run with:  streamlit run app.py"""
import pandas as pd
import streamlit as st

from rag_app import feedback
from rag_app.config import settings
from rag_app.generate import stream_answer
from rag_app.loaders import SUPPORTED, load_chunks
from rag_app.store import add_chunks, count, reset_collection, search

st.set_page_config(page_title="Document Q&A", page_icon="📄", layout="wide")


def rebuild_index() -> tuple[int, int]:
    chunks = load_chunks(settings.data_dir, settings.chunk_size, settings.chunk_overlap)
    reset_collection()
    if chunks:
        add_chunks(chunks)
    return len(chunks), len({c.source for c in chunks})


# ---------- Sidebar: documents and index ----------
with st.sidebar:
    st.header("Documents")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(
        p for p in settings.data_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED
    )
    if files:
        for p in files:
            st.write(f"• {p.relative_to(settings.data_dir).as_posix()}")
    else:
        st.info(f"No documents yet in `{settings.data_dir}`.")

    uploads = st.file_uploader(
        "Add documents", type=[s.lstrip(".") for s in SUPPORTED], accept_multiple_files=True
    )
    if uploads and st.button("Save uploaded files"):
        for f in uploads:
            (settings.data_dir / f.name).write_bytes(f.getbuffer())
        st.success(f"Saved {len(uploads)} file(s). Rebuild the index to search them.")
        st.rerun()

    st.divider()
    st.header("Index")
    try:
        n = count()
        st.caption(f"{n} passages indexed" if n else "Index is empty.")
    except Exception as e:  # index folder unreadable/corrupt
        st.caption(f"Could not read index: {e}")
    if st.button("Rebuild index", type="primary"):
        with st.spinner("Indexing documents..."):
            n_chunks, n_files = rebuild_index()
        st.success(f"Indexed {n_chunks} passages from {n_files} files.")
        st.rerun()

    st.divider()
    top_k = st.slider("Passages to retrieve", 1, 15, settings.top_k)

    # Search-only mode skips Claude and just shows matching passages (free, offline).
    search_only = st.toggle(
        "Search only (no LLM)",
        key="search_only",
        help="Show the matching passages without sending anything to Claude. Free and offline.",
    )


# ---------- Main ----------
st.title("Ask your documents")
ask_tab, reports_tab = st.tabs(["Ask", "Reported issues"])


def report_form(last: dict) -> None:
    """Let an employee flag the last answer as incorrect/outdated; saved to SQLite."""
    st.subheader("Report a problem with this response")
    sources = list(dict.fromkeys(h["source"] for h in last["hits"]))
    with st.form("report_form", clear_on_submit=True):
        reporter = st.text_input("Your name")
        issue_type = st.segmented_control(
            "What's wrong?", feedback.ISSUE_TYPES, default=feedback.ISSUE_TYPES[0]
        )
        affected = st.multiselect("Which document(s) are affected? (optional)", sources)
        description = st.text_area(
            "Describe what was incorrect or outdated",
            placeholder="e.g. The answer says 3 release gates, but gate 3 was removed in Q3.",
        )
        if st.form_submit_button("Submit report", type="primary"):
            if not reporter.strip() or not description.strip() or not issue_type:
                st.error("Please fill in your name, the issue type and a description.")
            else:
                rid = feedback.add_report(
                    reporter=reporter,
                    question=last["question"],
                    answer=last["answer"],
                    sources=[h["source"] for h in last["hits"]],
                    issue_type=issue_type,
                    affected=affected,
                    description=description,
                )
                st.success(f"Thanks! Report #{rid} was saved.")


with ask_tab:
    question = st.text_input(
        "Question", placeholder="e.g. How should a rejected 837 claim be triaged?"
    )
    ask = st.button("Ask")
    just_streamed = False

    if ask and question.strip():
        hits = search(question, top_k)
        if not hits:
            st.warning("The index is empty. Click **Rebuild index** in the sidebar first.")
            st.stop()
        answer_text = None
        if not search_only:
            st.subheader("Answer")
            try:
                answer_text = st.write_stream(stream_answer(question, hits))
            except Exception as e:
                st.error(f"Error calling Claude: {e}")
                st.stop()
            just_streamed = True
        # Keep the result so it stays on screen while the report form is used.
        st.session_state.last = {"question": question, "answer": answer_text, "hits": hits}
    elif ask:
        st.warning("Type a question first.")

    last = st.session_state.get("last")
    if last:
        if last["answer"] is None:
            # Search-only results
            st.info(
                "Showing the passages that best match your question. No LLM was used.",
                title="Search-only mode",
            )
            st.subheader("Matching passages")
            for i, h in enumerate(last["hits"], start=1):
                with st.container(border=True):
                    st.markdown(f"**[{i}] {h['source']}**")
                    st.caption(f"Distance: {h['distance']:.3f} (lower = closer match)")
                    st.text(h["text"])
        else:
            if not just_streamed:
                st.caption(f"Question: {last['question']}")
                st.subheader("Answer")
                st.markdown(last["answer"])
            st.subheader("Sources")
            for i, h in enumerate(last["hits"], start=1):
                with st.expander(f"[{i}] {h['source']}"):
                    st.text(h["text"])

        st.divider()
        report_form(last)


with reports_tab:
    show = st.segmented_control(
        "Show", ["all", *feedback.STATUSES], default="open", key="report_filter"
    )
    reports = feedback.list_reports(None if show in (None, "all") else show)
    if not reports:
        st.info("No reports to show.")
    else:
        df = pd.DataFrame(reports)[
            ["id", "created_at", "status", "issue_type", "reporter", "question",
             "description", "affected", "answer"]
        ]
        df["affected"] = df["affected"].map(", ".join)
        st.dataframe(
            df,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("#", width="small"),
                "created_at": "Submitted (UTC)",
                "issue_type": "Type",
                "affected": "Documents",
            },
        )
        st.download_button(
            "Download as CSV", df.to_csv(index=False), "reported_issues.csv", "text/csv"
        )

        with st.container(border=True):
            st.markdown("**Update a report's status**")
            with st.container(horizontal=True, vertical_alignment="bottom"):
                rid = st.selectbox("Report #", [r["id"] for r in reports], key="status_id")
                new_status = st.selectbox("New status", feedback.STATUSES, key="status_value")
                if st.button("Update"):
                    feedback.set_status(rid, new_status)
                    st.rerun()
