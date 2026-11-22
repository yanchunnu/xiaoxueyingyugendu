"""Helpers for the long-passage topic sources."""

from __future__ import annotations

import re

SECTIONS = [
    ("인물 묘사", "People", 1, 22),
    ("장소·풍경 묘사", "Places and Scenery", 23, 29),
    ("개인 물건", "My Things", 30, 43),
    ("취미·관심사", "Hobbies and Interests", 44, 54),
    ("학교생활", "School Life", 55, 69),
    ("일상생활", "Daily Life", 70, 87),
    ("건강과 음식", "Health and Food", 88, 94),
    ("사계절", "The Seasons", 95, 100),
]


def section_for(number: int) -> tuple[str, str]:
    for ko, en, start, end in SECTIONS:
        if start <= number <= end:
            return ko, en
    raise KeyError(number)


def appears(word: str, text: str) -> bool:
    esc = re.escape(word)
    if " " in word:
        pattern = rf"(?<!\w){esc}(?!\w)"
    else:
        pattern = rf"(?<!\w){esc}(?:s|es|ed|ing|d)?(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def T(
    n: int,
    slug: str,
    topic: str,
    topic_ko: str,
    words: list[tuple[str, str]],
    lines: list[tuple[str, str]],
    title_spoken: str | None = None,
) -> dict:
    if not 8 <= len(words) <= 10:
        raise ValueError(f"{n} {topic}: {len(words)} words")
    if not 10 <= len(lines) <= 12:
        raise ValueError(f"{n} {topic}: {len(lines)} sentences")
    blob = " ".join(en for en, _ko in lines)
    missing = [en for en, _ko in words if not appears(en, blob)]
    if missing:
        raise ValueError(f"{n} {topic}: missing words {missing}")
    for en, ko in lines:
        if not en.strip() or not ko.strip():
            raise ValueError(f"{n} {topic}: empty line")
        if re.search(r"\d", en):
            raise ValueError(f"{n} {topic}: digit in {en!r}")
        if "(" in en or ")" in en:
            raise ValueError(f"{n} {topic}: parentheses in {en!r}")
    spoken = title_spoken or topic
    if "(" in spoken or ")" in spoken:
        raise ValueError(f"{n} {topic}: parentheses in title_spoken {spoken!r}")
    return {
        "n": n,
        "slug": slug,
        "topic": topic,
        "topic_ko": topic_ko,
        "title_spoken": spoken,
        "words": words,
        "lines": lines,
    }
