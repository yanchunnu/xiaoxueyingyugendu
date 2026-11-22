#!/usr/bin/env python3
"""Copy per-word, per-sentence, and full-passage clips from the TTS cache.

Output (48 kbps mono, same Edge TTS takes used in the full MP3):
    audio/clips/NNN/w01.mp3
    audio/clips/NNN/s01.mp3
    audio/clips/NNN/full.mp3
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contentlib import CONTENT, ROOT  # noqa: E402

CACHE = ROOT / "build" / "tts-cache"
OUT = ROOT / "audio" / "clips"


def cache_key(text: str, voice: str, rate: str) -> str:
    raw = f"{voice}|{rate}|{text}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:20]


def spoken(item: dict, key: str = "en") -> str:
    return (item.get("spoken") or item.get(key) or "").strip()


def copy_clip(text: str, voice: str, rate: str, dest: Path) -> None:
    src = CACHE / f"{cache_key(text, voice, rate)}.mp3"
    if not src.is_file() or src.stat().st_size < 200:
        raise SystemExit(f"missing TTS clip for {text!r} -> {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)


def main() -> int:
    manifest = json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))
    n_files = 0
    for item in manifest["topics"]:
        data = json.loads((ROOT / item["file"]).read_text(encoding="utf-8"))
        voice = data["voice"]
        rate = data["rate"]
        folder = OUT / f"{item['number']:03d}"
        for index, word in enumerate(data["words"], 1):
            copy_clip(spoken(word), voice, rate, folder / f"w{index:02d}.mp3")
            n_files += 1
        for index, phrase in enumerate(data["phrases"], 1):
            copy_clip(spoken(phrase), voice, rate, folder / f"s{index:02d}.mp3")
            n_files += 1
        full = (data.get("full_passage_spoken") or "").strip()
        copy_clip(full, voice, rate, folder / "full.mp3")
        n_files += 1
    print(f"Wrote {n_files} clips under {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
