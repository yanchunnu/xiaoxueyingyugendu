#!/usr/bin/env python3
"""Synthesize Mandarin clips with zh-CN-XiaoxiaoNeural at -20%.

Writes 48 kbps mono MP3 files:
    audio/zh/clips/NNN/w01.mp3
    audio/zh/clips/NNN/s01.mp3
    audio/zh/clips/NNN/full.mp3

Per-topic long files with built-in pauses are not written. The passage clip
full.mp3 is what the player uses.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
OUT = ROOT / "audio" / "zh" / "clips"
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-20%"


def jobs(only: set[int] | None) -> list[tuple[str, Path]]:
    manifest = json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))
    items: list[tuple[str, Path]] = []
    for meta in manifest["topics"]:
        number = int(meta["number"])
        if only and number not in only:
            continue
        data = json.loads((ROOT / meta["file"]).read_text(encoding="utf-8"))
        folder = OUT / f"{number:03d}"
        for index, word in enumerate(data["words"], 1):
            items.append((word["zh"], folder / f"w{index:02d}.mp3"))
        for index, phrase in enumerate(data["phrases"], 1):
            items.append((phrase["zh"], folder / f"s{index:02d}.mp3"))
        items.append((data["full_passage_zh"], folder / "full.mp3"))
    return items


async def synth(text: str, dest: Path, force: bool) -> str:
    if not force and dest.is_file() and dest.stat().st_size >= 400:
        return "skip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part.mp3")
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(tmp))
    if not tmp.is_file() or tmp.stat().st_size < 400:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"short clip for {text!r} -> {dest}")
    tmp.replace(dest)
    return "ok"


async def main_async(only: set[int] | None, force: bool, workers: int) -> int:
    pending = jobs(only)
    sem = asyncio.Semaphore(workers)
    done = {"ok": 0, "skip": 0}
    lock = asyncio.Lock()

    async def one(text: str, dest: Path) -> None:
        async with sem:
            for attempt in range(4):
                try:
                    status = await synth(text, dest, force)
                    break
                except Exception as exc:
                    if attempt == 3:
                        raise RuntimeError(f"{dest}: {exc}") from exc
                    await asyncio.sleep(1.5 * (attempt + 1))
            async with lock:
                done[status] += 1
                total = done["ok"] + done["skip"]
                if total % 100 == 0 or status == "ok" and done["ok"] <= 3:
                    print(f"{total}/{len(pending)} ok={done['ok']} skip={done['skip']}", flush=True)

    await asyncio.gather(*(one(text, dest) for text, dest in pending))
    print(f"finished {len(pending)} ok={done['ok']} skip={done['skip']} dir={OUT}")
    return 0


def parse_only(raw: str | None) -> set[int] | None:
    if not raw:
        return None
    return {int(part) for part in raw.split(",") if part.strip()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma-separated topic numbers")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(main_async(parse_only(args.only), args.force, args.workers)))
    except KeyboardInterrupt:
        sys.exit(130)
