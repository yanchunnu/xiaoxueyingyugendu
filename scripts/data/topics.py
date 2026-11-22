"""All generated topics (2–100) plus section metadata.

Topic 1 lives in content/001_about_me.json and is not redefined here.
"""

from __future__ import annotations

from .daily_seasons import TOPICS as DAILY
from .hobbies_school import TOPICS as SCHOOL
from .people import TOPICS as PEOPLE
from .places_things import TOPICS as PLACES

# (korean section, english section, first number, last number)
SECTIONS: list[tuple[str, str, int, int]] = [
    ("인물 묘사", "People", 1, 22),
    ("장소·풍경 묘사", "Places and Scenery", 23, 29),
    ("개인 물건", "My Things", 30, 43),
    ("취미·관심사", "Hobbies and Interests", 44, 54),
    ("학교생활", "School Life", 55, 69),
    ("일상생활", "Daily Life", 70, 87),
    ("건강과 음식", "Health and Food", 88, 94),
    ("사계절", "The Seasons", 95, 100),
]

TOPICS = PEOPLE + PLACES + SCHOOL + DAILY


def section_for(number: int) -> tuple[str, str]:
    for ko, en, start, end in SECTIONS:
        if start <= number <= end:
            return ko, en
    raise KeyError(number)
