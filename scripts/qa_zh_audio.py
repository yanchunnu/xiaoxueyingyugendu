#!/usr/bin/env python3
"""Transcribe Mandarin clips and compare them with the Chinese script.

Full passages use language=zh. Word clips are checked the same way.
他/她/它 and 的/地/得 are folded before scoring, because they sound alike.
The raw transcript is kept so a real misread can still be inspected.
"""

from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import zhconv

import av

_open = av.open


def _open_compat(*args, **kwargs):
    kwargs.pop("metadata_errors", None)
    return _open(*args, **kwargs)


av.open = _open_compat

from faster_whisper import WhisperModel  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CLIPS = ROOT / "audio" / "zh" / "clips"
REPORT = ROOT / "qa" / "zh_audio_report.json"

FOLD = str.maketrans({
    "她": "他",
    "它": "他",
    "地": "的",
    "得": "的",
    "再": "在",
    "作": "做",
})


def digits_to_han(text: str) -> str:
    def one(number: int) -> str:
        digits = "零一二三四五六七八九"
        if number < 10:
            return digits[number]
        if number == 10:
            return "十"
        if number < 20:
            return "十" + digits[number % 10]
        tens, rest = divmod(number, 10)
        return digits[tens] + "十" + (digits[rest] if rest else "")

    def repl(match: re.Match[str]) -> str:
        return one(int(match.group(0)))

    return re.sub(r"\d+", repl, text)


def han(text: str) -> str:
    text = zhconv.convert(text or "", "zh-cn")
    text = digits_to_han(text)
    return re.sub(r"[^\u4e00-\u9fff]", "", text)


def norm(text: str) -> str:
    return han(text).translate(FOLD)


def transcribe(model: WhisperModel, path: Path) -> str:
    segments, _info = model.transcribe(
        str(path),
        language="zh",
        beam_size=5,
        vad_filter=False,
        condition_on_previous_text=False,
    )
    return "".join(seg.text.strip() for seg in segments)


def main() -> int:
    manifest = json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))
    model = WhisperModel("small", device="cpu", compute_type="int8")
    report = []
    flagged = 0
    for meta in manifest["topics"]:
        data = json.loads((ROOT / meta["file"]).read_text(encoding="utf-8"))
        number = int(meta["number"])
        folder = CLIPS / f"{number:03d}"
        issues = []
        full_path = folder / "full.mp3"
        heard = transcribe(model, full_path)
        expected = data["full_passage_zh"]
        ratio = SequenceMatcher(None, norm(expected), norm(heard)).ratio()
        weak = []
        for phrase in data["phrases"]:
            expected_sentence = norm(phrase["zh"])
            matched = sum(
                block.size
                for block in SequenceMatcher(None, expected_sentence, norm(heard)).get_matching_blocks()
            )
            cover = matched / max(1, len(expected_sentence))
            if cover < 0.84:
                weak.append({
                    "zh": phrase["zh"],
                    "cover": round(cover, 3),
                })
        if ratio < 0.94 or weak:
            issues.append({
                "kind": "passage",
                "ratio": round(ratio, 3),
                "weak": weak,
                "expected": expected,
                "heard": heard,
            })
        word_notes = []
        for index, word in enumerate(data["words"], 1):
            path = folder / f"w{index:02d}.mp3"
            heard_word = transcribe(model, path)
            if norm(word["zh"]) != norm(heard_word):
                word_notes.append({
                    "file": path.name,
                    "zh": word["zh"],
                    "heard": heard_word,
                })
        # Isolated words often pick up an extra particle. Keep only clear misses.
        real_words = []
        for note in word_notes:
            if norm(note["zh"]) not in norm(note["heard"]):
                real_words.append(note)
        if real_words:
            issues.append({"kind": "words", "items": real_words})
        if issues:
            flagged += 1
        report.append({
            "number": number,
            "topic_zh": data.get("topic_zh"),
            "ratio": round(ratio, 3),
            "issues": issues,
            "full_heard": heard,
        })
        mark = " !" if issues else ""
        print(f"{number:03d}{mark} {ratio:.3f} {data.get('topic_zh')}", flush=True)
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Flagged {flagged} / {len(report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
