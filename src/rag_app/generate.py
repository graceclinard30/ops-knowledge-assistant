"""Answer a question with Claude, grounded in retrieved chunks."""
import sys

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


def answer(question: str, hits: list[dict], client: anthropic.Anthropic | None = None) -> str:
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
        for text in stream.text_stream:
            sys.stdout.write(text)
            sys.stdout.flush()
        final = stream.get_final_message()
    print()

    if final.stop_reason == "refusal":
        return "[The model declined to answer this request.]"
    return "".join(b.text for b in final.content if b.type == "text")
