"""Topics 2–100. Topic 1 is content/001_about_me.json."""

from .common import SECTIONS, section_for
from .daily_seasons import TOPICS as DAILY
from .hobbies_school import TOPICS as SCHOOL
from .people import TOPICS as PEOPLE
from .places_things import TOPICS as PLACES

TOPICS = PEOPLE + PLACES + SCHOOL + DAILY

__all__ = ["SECTIONS", "TOPICS", "section_for"]
