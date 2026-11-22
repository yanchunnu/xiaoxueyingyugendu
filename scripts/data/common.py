"""Small helpers shared by the topic source files."""

from __future__ import annotations


def S(en: str, ko: str) -> dict:
    """One short sentence, spoken as a single phrase."""
    return {"en": en, "ko": ko, "parts": ((en, ko),)}


def P(full_en: str, full_ko: str, *parts: tuple[str, str]) -> dict:
    """A sentence split into natural phrases.

    `parts` are (english, korean) pairs. Joined English must match `full_en`.
    """
    joined = " ".join(part[0] for part in parts)
    if joined != full_en:
        raise ValueError(f"phrase join mismatch:\n  {joined!r}\n  {full_en!r}")
    return {"en": full_en, "ko": full_ko, "parts": parts}


def T(
    n: int,
    slug: str,
    topic: str,
    topic_ko: str,
    words: list[tuple[str, str]],
    lines: list[dict],
    title_spoken: str | None = None,
) -> dict:
    return {
        "n": n,
        "slug": slug,
        "topic": topic,
        "topic_ko": topic_ko,
        "title_spoken": title_spoken or topic,
        "words": words,
        "lines": lines,
    }
