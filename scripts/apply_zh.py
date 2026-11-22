#!/usr/bin/env python3
"""Write Simplified Chinese and pinyin into topic JSON, the manifest, and index.html.

English and Korean fields are left unchanged.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "data"))
sys.path.insert(0, str(ROOT / "scripts"))

from zh_1 import DATA as D1  # noqa: E402
from zh_2 import DATA as D2  # noqa: E402
from zh_3 import DATA as D3  # noqa: E402
from zh_pinyin import to_pinyin  # noqa: E402

DATA = D1 + D2 + D3
CONTENT = ROOT / "content"
INDEX = ROOT / "index.html"


def main() -> int:
    if len(DATA) != 100:
        raise SystemExit(f"expected 100 Chinese topics, got {len(DATA)}")
    manifest = json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))
    by_number = {item["number"]: item for item in manifest["topics"]}
    for number in range(1, 101):
        item = by_number[number]
        data = json.loads((ROOT / item["file"]).read_text(encoding="utf-8"))
        zh = DATA[number - 1]
        if len(zh["words"]) != len(data["words"]) or len(zh["sents"]) != len(data["phrases"]):
            raise SystemExit(f"count mismatch on topic {number}")
        data["topic_zh"] = zh["title"]
        data["topic_pinyin"] = to_pinyin(zh["title"])
        data["voice_zh"] = "zh-CN-XiaoxiaoNeural"
        for word, text in zip(data["words"], zh["words"]):
            word["zh"] = text
            word["py"] = to_pinyin(text)
        for phrase, text in zip(data["phrases"], zh["sents"]):
            phrase["zh"] = text
            phrase["py"] = to_pinyin(text)
        data["full_passage_zh"] = "".join(zh["sents"])
        data["full_passage_pinyin"] = to_pinyin(data["full_passage_zh"])
        (ROOT / item["file"]).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        item["topic_zh"] = data["topic_zh"]
        item["topic_pinyin"] = data["topic_pinyin"]
        print(f"{number:03d} {data['topic_zh']} | {data['topic_pinyin']}")
    (CONTENT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    update_index(manifest)
    return 0


def update_index(manifest: dict) -> None:
    page = INDEX.read_text(encoding="utf-8")
    note = "<p>중국어로 들으려면 각 주제의 中文 을 누르세요. 주소에 lang=zh 를 붙여도 됩니다.</p>"
    needle = "<p>초등 영어 듣고 따라 읽기 · 민아 13살 6학년 · 100가지 주제</p>"
    if note not in page:
        page = page.replace(needle, needle + note, 1)
    for item in manifest["topics"]:
        num = f"{item['number']:03d}"
        label = f"{item['number']:02d}"
        opener = f'<a href="player.html?t={num}">따라 읽기 열기</a>'
        choice = (
            f'<a href="player.html?t={num}&lang=en">English</a>'
            f' · <a href="player.html?t={num}&lang=zh">中文</a>'
        )
        if opener in page:
            page = page.replace(opener, choice, 1)
        elif choice not in page:
            raise SystemExit(f"index opener missing for {num}")
        shown = html.escape(item["topic"], quote=True)
        title_re = re.compile(
            rf'(<a href="player\.html\?t={num}">{label}\. {re.escape(shown)}</a></strong><span>{re.escape(item["topic_ko"])})(?: · [^<]*)?(</span>)'
        )
        page, count = title_re.subn(rf'\1 · {item["topic_zh"]}\2', page, count=1)
        if count != 1:
            raise SystemExit(f"index title missing for {num}")
    old_footer = "각 주제 QR은 raw.githubusercontent.com 의 MP3입니다. 저장소가 비공개이면 로그인하지 않은 휴대폰에서는 재생되지 않습니다. 이 페이지는 같은 폴더의 audio 파일을 재생합니다."
    new_footer = "각 주제 QR은 플레이어로 연결됩니다. 플레이어 위쪽에서 English / 中文 을 고를 수 있고, 주소에 lang=zh 또는 lang=en 을 붙일 수 있습니다. 이 페이지의 듣기는 영어 전체 음원입니다."
    if old_footer in page:
        page = page.replace(old_footer, new_footer, 1)
    elif new_footer not in page:
        raise SystemExit("index footer missing")
    INDEX.write_text(page, encoding="utf-8")
    print("updated index.html")


if __name__ == "__main__":
    raise SystemExit(main())
