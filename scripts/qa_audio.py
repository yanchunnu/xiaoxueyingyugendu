#!/usr/bin/env python3
"""Transcribe every topic MP3 and compare it with the spoken script.

Writes qa/audio_report.json. Prints phrases and vocabulary the transcript
does not support. Number words and British spellings are normalized before
the comparison, because the recognizer writes digits and American spelling.
"""

from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import av

_open = av.open


def _open_compat(*args, **kwargs):
    kwargs.pop("metadata_errors", None)
    return _open(*args, **kwargs)


av.open = _open_compat

from faster_whisper import WhisperModel  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contentlib import CONTENT, ROOT  # noqa: E402

AUDIO = ROOT / "audio"
REPORT = ROOT / "qa" / "audio_report.json"

NUMBERS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20",
}
STOP = {
    "a", "an", "the", "to", "and", "of", "is", "am", "are", "was", "were",
    "my", "i", "you", "we", "she", "he", "it", "they", "for", "with", "in",
    "on", "at", "too", "very", "this", "that", "our", "her", "his", "me",
    "do", "not", "can", "will", "be", "so", "as", "up", "by", "or",
}


def normalize(text: str) -> str:
    text = text.lower().replace("favourite", "favorite").replace("colour", "color")
    text = text.replace("'", "")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    for word, digit in NUMBERS.items():
        text = re.sub(rf"\b{word}\b", digit, text)
    return re.sub(r"\s+", " ", text).strip()


def content_words(text: str) -> list[str]:
    return [word for word in normalize(text).split() if word not in STOP and not word.isdigit()]


def phrase_supported(phrase: str, transcript: str) -> tuple[bool, list[str]]:
    words = content_words(phrase)
    if not words:
        return True, []
    present = set(transcript.split())
    # Also allow the phrase as a substring for multiword items already normalized.
    missing = [word for word in words if word not in present]
    # A short phrase is fine when at least two thirds of its content words survived.
    if not words:
        return True, []
    ok = (len(words) - len(missing)) / len(words) >= 0.67 and len(missing) <= 1
    if len(words) <= 2:
        ok = len(missing) == 0
    return ok, missing


def main() -> int:
    manifest = json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))
    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    report = []
    flagged = 0
    for meta in manifest["topics"]:
        data = json.loads((ROOT / meta["file"]).read_text(encoding="utf-8"))
        path = AUDIO / Path(meta["audio"]).name
        segments, _info = model.transcribe(str(path), beam_size=1, vad_filter=True)
        raw = " ".join(seg.text.strip() for seg in segments)
        transcript = normalize(raw)
        issues = []
        title = normalize(data.get("title_spoken") or data["topic"])
        if title and title not in transcript and SequenceMatcher(None, title, transcript[:80]).ratio() < 0.55:
            # Title words should still show up.
            missing_title = [w for w in title.split() if w not in STOP and w not in transcript.split()]
            if missing_title:
                issues.append({"kind": "title", "missing": missing_title, "title": title})
        for word in data["words"]:
            spoken = normalize(word.get("spoken") or word["en"])
            if spoken and spoken not in transcript:
                issues.append({"kind": "word", "word": word["en"], "spoken": spoken})
        for phrase in data["phrases"]:
            spoken = phrase.get("spoken") or phrase["en"]
            ok, missing = phrase_supported(spoken, transcript)
            if not ok:
                issues.append({"kind": "phrase", "en": phrase["en"], "missing": missing})
        # Pronunciation traps the recognizer spells differently when TTS is wrong.
        if re.search(r"\bread\b", raw, re.I) is None and re.search(r"\blike to read\b|\bread a\b|\bread it\b|\bread books\b", " ".join(
            p["en"] for p in data["phrases"]
        ), re.I):
            if re.search(r"\bred\b", raw, re.I):
                issues.append({"kind": "pronunciation", "note": "read heard as red", "raw": raw[:240]})
        if issues:
            flagged += 1
        report.append({
            "number": meta["number"],
            "topic": meta["topic"],
            "file": Path(meta["audio"]).name,
            "issues": issues,
            "transcript": raw,
        })
        mark = " !" if issues else ""
        print(f"{meta['number']:03d}{mark} {meta['topic']}", flush=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Flagged {flagged} / {len(report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
