"""CLI: `python -m rag_app ingest` and `python -m rag_app ask "question"`."""
import argparse

from .config import settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="rag_app")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help=f"Index files in {settings.data_dir}")
    ask = sub.add_parser("ask", help="Ask a question over the indexed documents")
    ask.add_argument("question")
    ask.add_argument("-k", type=int, default=settings.top_k, help="chunks to retrieve")
    args = parser.parse_args()

    if args.command == "ingest":
        from .loaders import load_chunks
        from .store import add_chunks

        chunks = load_chunks(settings.data_dir, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            print(f"No .txt/.md/.pdf files found in {settings.data_dir}")
            return
        add_chunks(chunks)
        print(f"Indexed {len(chunks)} chunks from {len({c.source for c in chunks})} files.")
    else:
        from .generate import answer
        from .store import search

        hits = search(args.question, args.k)
        if not hits:
            print("Index is empty - run `python -m rag_app ingest` first.")
            return
        answer(args.question, hits)
        print("\nSources:")
        for i, h in enumerate(hits, start=1):
            print(f"  [{i}] {h['source']}")


if __name__ == "__main__":
    main()
