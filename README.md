# rag_app

A minimal retrieval-augmented generation (RAG) app: drop documents in `data/raw/`, index them into a local Chroma vector store, and ask questions answered by Claude with source citations.

## How it works

1. **Ingest**: `.txt`, `.md` and `.pdf` files in `data/raw/` are split into overlapping chunks ([loaders.py](src/rag_app/loaders.py)).
2. **Embed and store**: chunks go into a persistent Chroma collection in `storage/`, embedded with Chroma's built-in local model ([store.py](src/rag_app/store.py)).
3. **Retrieve and answer**: the top-k chunks for a question are passed to Claude, which answers and cites them ([generate.py](src/rag_app/generate.py)).

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
copy .env.example .env   # then add your ANTHROPIC_API_KEY
```

## Usage

```powershell
python -m rag_app ingest
python -m rag_app ask "What does the onboarding doc say about laptops?"
```

## Tests

```powershell
pytest
```

## Next steps

- Swap in a stronger embedding model (e.g. a hosted embeddings API) in `store.py`
- Add a reranking step after retrieval
- Build a small evaluation set of question/answer pairs to measure retrieval quality
- Add a web UI (Flask or Streamlit)
