#!/usr/bin/env python3
"""Write content/NNN_slug.json and content/manifest.json from the topic sources.

Topic 1 is copied through unchanged from content/001_about_me.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contentlib import CONTENT, build_record, validate_record  # noqa: E402
from data.topics import SECTIONS, TOPICS, section_for  # noqa: E402

TOPIC1 = CONTENT / "001_about_me.json"


def dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    topic1 = json.loads(TOPIC1.read_text(encoding="utf-8"))
    errors: list[str] = []
    manifest = []

    section_ko, section_en = section_for(1)
    manifest.append(
        {
            "number": 1,
            "slug": topic1["slug"],
            "topic": topic1["topic"],
            "topic_ko": topic1["topic_ko"],
            "section_ko": section_ko,
            "section_en": section_en,
            "title_spoken": topic1.get("title_spoken", topic1["topic"]),
            "file": "content/001_about_me.json",
            "audio": "audio/001_about_me.mp3",
        }
    )

    numbers = [t["n"] for t in TOPICS]
    if numbers != list(range(2, 101)):
        print("Topic numbers are not 2..100 in order", file=sys.stderr)
        return 1

    for topic in TOPICS:
        ko, en = section_for(topic["n"])
        record = build_record(topic, ko, en)
        errors.extend(validate_record(record))
        filename = f"{topic['n']:03d}_{topic['slug']}.json"
        dump(CONTENT / filename, record)
        manifest.append(
            {
                "number": topic["n"],
                "slug": topic["slug"],
                "topic": topic["topic"],
                "topic_ko": topic["topic_ko"],
                "section_ko": ko,
                "section_en": en,
                "title_spoken": topic["title_spoken"],
                "file": f"content/{filename}",
                "audio": f"audio/{topic['n']:03d}_{topic['slug']}.mp3",
            }
        )

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    dump(
        CONTENT / "manifest.json",
        {"title": "Listen and Repeat", "title_ko": "초등 영어 듣고 따라 읽기", "sections": [
            {"ko": ko, "en": en, "start": start, "end": end} for ko, en, start, end in SECTIONS
        ], "topics": manifest},
    )
    print(f"Wrote {len(manifest)} topics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
