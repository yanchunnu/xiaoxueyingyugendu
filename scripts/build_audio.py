#!/usr/bin/env python3
"""Build listen-and-repeat MP3s from topic JSON.

The timeline matches make_readalong.py:

  * title, then a short hold
  * "Words. Listen and repeat.", then a short hold
  * each word spoken 3 times, with a pause after every reading
  * "Now, let's read. Listen and repeat.", then a short hold
  * each phrase once, then a pause of about 1.5x the phrase (at least 2.5s)
  * the full passage read straight through
  * "Great job!"

Speech is edge-tts, en-US-JennyNeural, rate -20%.
MP3s are mono, 24 kHz, 48 kbps: audio/NNN_slug.mp3
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import edge_tts

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contentlib import CONTENT, ROOT, iter_topic_files, load_topic  # noqa: E402

AUDIO_DIR = ROOT / "audio"
CACHE = ROOT / "build" / "tts-cache"
RATE_HZ = 24000
MP3_BITRATE = "48k"


def spoken(item: dict, key: str = "en") -> str:
    return (item.get("spoken") or item.get(key) or "").strip()


def cache_key(text: str, voice: str, rate: str) -> str:
    raw = f"{voice}|{rate}|{text}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:20]


def write_silence(path: Path, seconds: float, rate: int = RATE_HZ) -> None:
    n = max(1, int(round(seconds * rate)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * n)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def mp3_to_wav(src: Path, dest: Path) -> None:
    import subprocess

    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(src),
            "-ar", str(RATE_HZ),
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(dest),
        ],
        check=True,
    )


def concat_wavs(paths: list[Path], dest: Path) -> None:
    frames: list[bytes] = []
    for path in paths:
        with wave.open(str(path), "rb") as handle:
            if handle.getnchannels() != 1 or handle.getframerate() != RATE_HZ or handle.getsampwidth() != 2:
                raise RuntimeError(f"unexpected wav format: {path}")
            frames.append(handle.readframes(handle.getnframes()))
    with wave.open(str(dest), "w") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE_HZ)
        for chunk in frames:
            out.writeframes(chunk)


def encode_mp3(wav_path: Path, mp3_path: Path) -> None:
    import subprocess

    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(wav_path),
            "-ac", "1",
            "-ar", str(RATE_HZ),
            "-c:a", "libmp3lame",
            "-b:a", MP3_BITRATE,
            str(mp3_path),
        ],
        check=True,
    )


async def synth_all(jobs: list[tuple[str, str, str, Path]]) -> None:
    """jobs: (text, voice, rate, mp3_path) for clips that are not cached yet."""
    sem = asyncio.Semaphore(8)

    async def one(text: str, voice: str, rate: str, dest: Path) -> None:
        async with sem:
            last = None
            for attempt in range(4):
                try:
                    await edge_tts.Communicate(text, voice, rate=rate).save(str(dest))
                    if dest.stat().st_size < 200:
                        raise RuntimeError("tts file too small")
                    return
                except Exception as exc:  # noqa: BLE001
                    last = exc
                    await asyncio.sleep(0.8 * (attempt + 1))
            raise RuntimeError(f"TTS failed for {text!r}: {last}") from last

    await asyncio.gather(*(one(*job) for job in jobs))


def ensure_wavs(mp3s: list[Path]) -> None:
    missing = [(mp3, mp3.with_suffix(".wav")) for mp3 in mp3s if not mp3.with_suffix(".wav").exists()]
    if not missing:
        return
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda pair: mp3_to_wav(*pair), missing))


def timeline_for(data: dict, work: Path) -> list[Path]:
    voice = data["voice"]
    rate = data["rate"]
    repeat = int(data.get("word_repeat", 3))
    word_pause = float(data.get("word_pause_sec", 2.0))
    mul = float(data.get("phrase_pause_multiplier", 1.5))
    min_pause = float(data.get("phrase_pause_min_sec", 2.5))

    def clip(text: str) -> Path:
        key = cache_key(text, voice, rate)
        return CACHE / f"{key}.wav"

    parts: list[Path] = []

    def add_speech(text: str) -> Path:
        wav = clip(text)
        parts.append(wav)
        return wav

    def add_silence(seconds: float, name: str) -> None:
        path = work / f"{name}.wav"
        write_silence(path, seconds)
        parts.append(path)

    add_speech(data.get("title_spoken") or data["topic"])
    add_silence(1.8, "sil_title")

    add_speech(data.get("words_intro") or "Words. Listen and repeat.")
    add_silence(1.0, "sil_words_intro")

    for index, word in enumerate(data["words"]):
        wav = clip(spoken(word))
        sil = work / f"sil_word_{index}.wav"
        write_silence(sil, word_pause)
        for _ in range(repeat):
            parts.append(wav)
            parts.append(sil)

    add_speech(data.get("passage_intro") or "Now, let's read. Listen and repeat.")
    add_silence(1.0, "sil_passage_intro")

    for index, phrase in enumerate(data["phrases"]):
        wav = clip(spoken(phrase))
        pause = max(min_pause, wav_duration(wav) * mul)
        sil = work / f"sil_phrase_{index}.wav"
        write_silence(sil, pause)
        parts.append(wav)
        parts.append(sil)

    full = (data.get("full_passage_spoken") or "").strip()
    if full:
        add_silence(0.6, "sil_full_pre")
        add_speech(full)
        add_silence(1.6, "sil_full_post")

    closing = (data.get("closing_spoken") or "").strip()
    if closing:
        add_speech(closing)
        add_silence(1.8, "sil_close")
    return parts


def collect_texts(topics: list[dict]) -> list[tuple[str, str, str]]:
    seen: set[tuple[str, str, str]] = set()
    ordered: list[tuple[str, str, str]] = []

    def add(text: str, voice: str, rate: str) -> None:
        text = text.strip()
        if not text:
            return
        item = (text, voice, rate)
        if item not in seen:
            seen.add(item)
            ordered.append(item)

    for data in topics:
        voice = data["voice"]
        rate = data["rate"]
        add(data.get("title_spoken") or data["topic"], voice, rate)
        add(data.get("words_intro") or "Words. Listen and repeat.", voice, rate)
        add(data.get("passage_intro") or "Now, let's read. Listen and repeat.", voice, rate)
        add(data.get("closing_spoken") or "", voice, rate)
        add(data.get("full_passage_spoken") or "", voice, rate)
        for word in data["words"]:
            add(spoken(word), voice, rate)
        for phrase in data["phrases"]:
            add(spoken(phrase), voice, rate)
    return ordered


def build_one(data: dict, number: int, audio_rel: str | None = None) -> Path:
    slug = data["slug"]
    work = ROOT / "build" / "work" / f"{number:03d}_{slug}"
    work.mkdir(parents=True, exist_ok=True)
    parts = timeline_for(data, work)
    wav_all = work / "all.wav"
    concat_wavs(parts, wav_all)
    dest = ROOT / audio_rel if audio_rel else AUDIO_DIR / f"{number:03d}_{slug}.mp3"
    encode_mp3(wav_all, dest)
    return dest


def manifest_numbers() -> dict[str, int]:
    manifest = json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))
    return {item["file"]: item["number"] for item in manifest["topics"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build listen-and-repeat MP3s.")
    parser.add_argument("--only", help="Comma-separated topic numbers, e.g. 1,50")
    args = parser.parse_args()
    wanted = None
    if args.only:
        wanted = {int(part) for part in args.only.split(",") if part.strip()}

    manifest = json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))
    by_file = {item["file"]: item for item in manifest["topics"]}
    topics: list[tuple[int, dict, str]] = []
    for path in iter_topic_files():
        item = by_file[f"content/{path.name}"]
        number = item["number"]
        if wanted is not None and number not in wanted:
            continue
        topics.append((number, load_topic(path), item["audio"]))

    texts = collect_texts([data for _, data, _audio in topics])
    CACHE.mkdir(parents=True, exist_ok=True)
    pending = []
    for text, voice, rate in texts:
        mp3 = CACHE / f"{cache_key(text, voice, rate)}.mp3"
        if not mp3.exists() or mp3.stat().st_size < 200:
            pending.append((text, voice, rate, mp3))
    print(f"TTS clips: {len(texts)} unique, {len(pending)} to synthesize")
    if pending:
        asyncio.run(synth_all(pending))

    mp3s = [CACHE / f"{cache_key(text, voice, rate)}.mp3" for text, voice, rate in texts]
    print("Converting clips to wav…")
    ensure_wavs(mp3s)

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for number, data, audio_rel in topics:
        dest = build_one(data, number, audio_rel)
        all_wav = ROOT / "build" / "work" / f"{number:03d}_{data['slug']}" / "all.wav"
        print(f"{dest.name}  {dest.stat().st_size / 1024:.0f} KB  {wav_duration(all_wav):.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
