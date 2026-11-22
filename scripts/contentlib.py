"""Load topic JSON and check that passages match the word list."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

VOICE = "en-US-JennyNeural"
RATE = "-20%"

# Abbreviations that TTS reads awkwardly. Do not match the word "am".
BANNED = re.compile(
    r"(?<!\w)(?:[ap]\.m\.)(?!\w)|\b(?:Mr|Mrs|Ms|Dr)\.|\b(?:TV|PE)\b|\(\s*\d+\s*\)",
    re.IGNORECASE,
)


def appears(word: str, text: str) -> bool:
    """True if `word` appears, allowing a simple English inflection on one word."""
    esc = re.escape(word)
    if " " in word:
        pattern = rf"(?<!\w){esc}(?!\w)"
    else:
        pattern = rf"(?<!\w){esc}(?:s|es|ed|ing|d)?(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def passage_text(lines: list[dict]) -> str:
    return " ".join(line["en"] for line in lines)


def highlights_for(text: str, words: list[str]) -> list[str]:
    return [word for word in words if appears(word, text)]


def build_record(topic: dict, section_ko: str, section_en: str) -> dict:
    word_pairs = [{"en": en, "ko": ko} for en, ko in topic["words"]]
    word_ens = [en for en, _ko in topic["words"]]
    phrases = []
    full_lines = []
    for line in topic["lines"]:
        for en, ko in line["parts"]:
            phrases.append({"en": en, "ko": ko, "highlights": highlights_for(en, word_ens)})
        full_lines.append(
            {
                "en": line["en"],
                "ko": line["ko"],
                "highlights": highlights_for(line["en"], word_ens),
            }
        )
    return {
        "slug": topic["slug"],
        "topic": topic["topic"],
        "topic_ko": topic["topic_ko"],
        "number": topic["n"],
        "section_ko": section_ko,
        "section_en": section_en,
        "voice": VOICE,
        "rate": RATE,
        "title_spoken": topic["title_spoken"],
        "words_intro": "Words. Listen and repeat.",
        "passage_intro": "Now, let's read. Listen and repeat.",
        "closing_spoken": "Great job!",
        "closing_en": "Great job!",
        "closing_ko": "참 잘했어요!",
        "word_repeat": 3,
        "word_pause_sec": 2.0,
        "phrase_pause_multiplier": 1.5,
        "phrase_pause_min_sec": 2.5,
        "words": word_pairs,
        "phrases": phrases,
        "full_passage_lines": full_lines,
        "full_passage_spoken": " ".join(line["en"] for line in topic["lines"]),
    }


def validate_record(data: dict, *, allow_title_parens: bool = True) -> list[str]:
    errors: list[str] = []
    n = data.get("number")
    label = f"{n:03d} {data.get('topic')}" if isinstance(n, int) else data.get("topic", "?")
    words = [w["en"] for w in data["words"]]
    if not 8 <= len(words) <= 10:
        errors.append(f"{label}: expected 8–10 words, got {len(words)}")
    if len(set(w.lower() for w in words)) != len(words):
        errors.append(f"{label}: duplicate word")
    lines = data["full_passage_lines"]
    if not 6 <= len(lines) <= 9:
        errors.append(f"{label}: expected 6–9 sentences, got {len(lines)}")
    if not data["phrases"]:
        errors.append(f"{label}: no phrases")
    blob = passage_text(lines)
    for word in words:
        if not appears(word, blob):
            errors.append(f"{label}: word {word!r} never appears in the passage")
    for line in lines:
        if not line["en"].strip() or not line["ko"].strip():
            errors.append(f"{label}: empty sentence")
        if re.search(r"\d", line["en"]):
            errors.append(f"{label}: digit in sentence {line['en']!r}")
        if BANNED.search(line["en"]):
            errors.append(f"{label}: banned token in {line['en']!r}")
    for phrase in data["phrases"]:
        if not phrase["en"].strip() or not phrase["ko"].strip():
            errors.append(f"{label}: empty phrase")
        if "(" in phrase["en"] or ")" in phrase["en"]:
            errors.append(f"{label}: parentheses in phrase {phrase['en']!r}")
        for h in phrase["highlights"]:
            if not appears(h, phrase["en"]):
                errors.append(f"{label}: highlight {h!r} not in {phrase['en']!r}")
    spoken = data.get("title_spoken") or ""
    if "(" in spoken or ")" in spoken:
        errors.append(f"{label}: title_spoken has parentheses: {spoken!r}")
    if data.get("voice") != VOICE or data.get("rate") != RATE:
        errors.append(f"{label}: unexpected voice/rate")
    return errors


def load_topic(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_topic_files() -> list[Path]:
    return sorted(CONTENT.glob("[0-9][0-9][0-9]_*.json"))
