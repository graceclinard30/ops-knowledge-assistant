"""Answer a question with Claude, grounded in retrieved chunks."""
import sys
from collections.abc import Iterator

import anthropic

from .config import settings

SYSTEM_PROMPT = (
    "You answer questions using the provided documents. "
    "Base your answer on the documents and cite sources by their [n] number. "
    "If the documents don't contain the answer, say so plainly rather than guessing."
)


def build_context(hits: list[dict]) -> str:
    return "\n\n".join(
        f'<document index="{i}" source="{h["source"]}">\n{h["text"]}\n</document>'
        for i, h in enumerate(hits, start=1)
    )


REFUSAL_MESSAGE = "[The model declined to answer this request.]"


def stream_answer(
    question: str, hits: list[dict], client: anthropic.Anthropic | None = None
) -> Iterator[str]:
    """Yield the answer text piece by piece as Claude writes it (used by CLI and web UI)."""
    client = client or anthropic.Anthropic()
    user_content = f"<documents>\n{build_context(hits)}\n</documents>\n\nQuestion: {question}"

    # Server-side refusal fallback is enabled: if the primary model declines,
    # the API reroutes to a suitable fallback model within the same call.
    with client.beta.messages.stream(
        model=settings.model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        yield from stream.text_stream
        final = stream.get_final_message()

    if final.stop_reason == "refusal":
        yield "\n\n" + REFUSAL_MESSAGE


def answer(question: str, hits: list[dict], client: anthropic.Anthropic | None = None) -> str:
    """Print the answer to the terminal as it streams, and return the full text."""
    parts = []
    for text in stream_answer(question, hits, client):
        sys.stdout.write(text)
        sys.stdout.flush()
        parts.append(text)
    print()
    return "".join(parts)
