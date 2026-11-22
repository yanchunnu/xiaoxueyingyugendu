#!/usr/bin/env python3
"""Write content JSON for topics 2–100. Topic 1 is kept as the supplied file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contentlib import CONTENT, appears  # noqa: E402
from data.topics import SECTIONS, TOPICS, section_for  # noqa: E402

AUDIO_BASE = "https://raw.githubusercontent.com/yanchunnu/xiaoxueyingyugendu/main/audio/"
TOPIC1 = CONTENT / "001_about_me.json"


def highlights_for(text: str, words: list[str]) -> list[str]:
    return [word for word in words if appears(word, text)]


def build_record(topic: dict) -> dict:
    section_ko, section_en = section_for(topic["n"])
    word_ens = [en for en, _ko in topic["words"]]
    phrases = []
    for en, ko in topic["lines"]:
        phrases.append({"en": en, "ko": ko, "highlights": highlights_for(en, word_ens)})
    filename = f"{topic['n']:03d}_{topic['slug']}.mp3"
    return {
        "slug": topic["slug"],
        "topic": topic["topic"],
        "topic_ko": topic["topic_ko"],
        "topic_number": topic["n"],
        "topic_total": 100,
        "category_en": section_en,
        "category_ko": section_ko,
        "voice": "en-US-JennyNeural",
        "rate": "-20%",
        "title_spoken": topic["title_spoken"],
        "words_intro": "Words. Listen and repeat.",
        "passage_intro": "Now, let's read. Listen and repeat.",
        "closing_spoken": "Great job!",
        "closing_en": "Great job!",
        "closing_ko": "참 잘했어요!",
        "word_repeat": 3,
        "word_pause_sec": 2.0,
        "phrase_pause_multiplier": 1.3,
        "phrase_pause_min_sec": 3.0,
        "qr_url": AUDIO_BASE + filename,
        "words": [{"en": en, "ko": ko} for en, ko in topic["words"]],
        "phrases": phrases,
        "full_passage_lines": phrases,
        "full_passage_spoken": " ".join(en for en, _ko in topic["lines"]),
    }


def main() -> int:
    topic1 = json.loads(TOPIC1.read_text(encoding="utf-8"))
    if topic1["topic"] != "About Me" or len(topic1["phrases"]) != 12:
        print("Topic 1 file is not the long About Me sample", file=sys.stderr)
        return 1
    numbers = [t["n"] for t in TOPICS]
    if numbers != list(range(2, 101)):
        print("Topic numbers are not 2..100", file=sys.stderr)
        return 1

    manifest_topics = [{
        "number": 1,
        "slug": "about_me",
        "topic": topic1["topic"],
        "topic_ko": topic1["topic_ko"],
        "section_ko": topic1["category_ko"],
        "section_en": topic1["category_en"],
        "title_spoken": topic1["title_spoken"],
        "file": "content/001_about_me.json",
        "audio": "audio/001_about_me.mp3",
    }]
    for topic in TOPICS:
        record = build_record(topic)
        filename = f"{topic['n']:03d}_{topic['slug']}.json"
        path = CONTENT / filename
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ko, en = section_for(topic["n"])
        manifest_topics.append({
            "number": topic["n"],
            "slug": topic["slug"],
            "topic": topic["topic"],
            "topic_ko": topic["topic_ko"],
            "section_ko": ko,
            "section_en": en,
            "title_spoken": topic["title_spoken"],
            "file": f"content/{filename}",
            "audio": f"audio/{topic['n']:03d}_{topic['slug']}.mp3",
        })

    manifest = {
        "title": "Listen and Repeat",
        "title_ko": "초등 영어 듣고 따라 읽기",
        "sections": [{"ko": ko, "en": en, "start": start, "end": end} for ko, en, start, end in SECTIONS],
        "topics": manifest_topics,
    }
    (CONTENT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(manifest_topics)} topics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
