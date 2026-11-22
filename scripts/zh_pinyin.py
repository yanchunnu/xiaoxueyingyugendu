# -*- coding: utf-8 -*-
"""Tone-marked pinyin for the lesson text, with polyphone fixes."""

from __future__ import annotations

import re

from pypinyin import Style, lazy_pinyin

# Longer phrases must be listed first. Readings are space-separated syllables.
PHRASES: list[tuple[str, str]] = [
    ("一步一步地", "yī bù yī bù de"),
    ("教我们", "jiāo wǒ men"),
    ("快乐地", "kuài lè de"),
    ("每一只", "měi yī zhī"),
    ("教我", "jiāo wǒ"),
    ("黑头发", "hēi tóu fa"),
    ("长头发", "cháng tóu fa"),
    ("长耳朵", "cháng ěr duo"),
    ("数一数", "shǔ yī shǔ"),
    ("数自己", "shǔ zì jǐ"),
    ("弹钢琴", "tán gāng qín"),
    ("慢慢地", "màn màn de"),
    ("公平地", "gōng píng de"),
    ("安静地", "ān jìng de"),
    ("种玫瑰", "zhòng méi gui"),
    ("比我长", "bǐ wǒ cháng"),
    ("太长", "tài cháng"),
    ("长出来", "zhǎng chū lái"),
    ("长成", "zhǎng chéng"),
    ("长出", "zhǎng chū"),
    ("做得", "zuò de"),
    ("吃得", "chī de"),
    ("只挑", "zhǐ tiāo"),
    ("背着", "bēi zhe"),
    ("背在", "bēi zài"),
    ("背上", "bèi shang"),
    ("长椅", "cháng yǐ"),
    ("很长", "hěn cháng"),
    ("更长", "gèng cháng"),
    ("又长", "yòu cháng"),
    ("长长", "cháng cháng"),
    ("长大", "zhǎng dà"),
    ("成长", "chéng zhǎng"),
    ("种种子", "zhòng zhǒng zi"),
    ("种可以", "zhòng kě yǐ"),
    ("种菜", "zhòng cài"),
    ("种在", "zhòng zài"),
    ("种子", "zhǒng zi"),
    ("头发", "tóu fa"),
    ("每只", "měi zhī"),
    ("两只", "liǎng zhī"),
    ("一只", "yī zhī"),
    ("数到", "shǔ dào"),
    ("跑得", "pǎo de"),
    ("变得", "biàn de"),
    ("写得", "xiě de"),
    ("睡得", "shuì de"),
    ("骑得", "qí de"),
    ("跳得", "tiào de"),
    ("长得", "zhǎng de"),
    ("说得", "shuō de"),
    ("飞得", "fēi de"),
    ("踢得", "tī de"),
    ("坐得", "zuò de"),
    ("起得", "qǐ de"),
]

_PHRASES = sorted(PHRASES, key=lambda item: len(item[0]), reverse=True)
_PUNCT = set("，。！？、；：（）《》…—·,.!?;:()[]「」『』")


def to_pinyin(text: str) -> str:
    syllables: list[str] = []
    i = 0
    raw: list[str] = []

    def flush() -> None:
        if raw:
            syllables.extend(lazy_pinyin("".join(raw), style=Style.TONE))
            raw.clear()

    while i < len(text):
        matched = None
        for phrase, reading in _PHRASES:
            if text.startswith(phrase, i):
                matched = (phrase, reading)
                break
        if matched:
            flush()
            syllables.extend(matched[1].split())
            i += len(matched[0])
        else:
            raw.append(text[i])
            i += 1
    flush()

    parts: list[str] = []
    for syllable in syllables:
        if not syllable:
            continue
        if syllable in _PUNCT or re.fullmatch(r"\W+", syllable):
            if parts:
                parts[-1] = parts[-1] + syllable
            else:
                parts.append(syllable)
        else:
            parts.append(syllable)
    return " ".join(parts)
