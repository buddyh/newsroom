"""Shared fixtures for newsroom tests."""

import pytest

from newsroom.models import Format, Script, Segment


SAMPLE_PODCAST_TEXT = """\
HOST: [enthusiastic] Welcome to the show! Today we're diving into AI agents.
CO-HOST: [curious] I've been reading about this all week. Where do we even start?
HOST: [thoughtful] Well, let's start with the basics. An AI agent is a system that can take actions.
CO-HOST: [surprised] Wait, so it's not just a chatbot?
HOST: [laughing] Definitely not! Think of it more like a digital employee.
CO-HOST: That sounds a bit overhyped though, doesn't it?
"""

SAMPLE_NEWS_TEXT = """\
ANCHOR: [serious] Good evening. Tonight's top story: advances in quantum computing.
ANCHOR: [serious] Researchers at MIT have achieved a breakthrough in error correction.
ANCHOR: This could accelerate the timeline for practical quantum computers by years.
"""

SAMPLE_DEBATE_TEXT = """\
MODERATOR: Welcome to tonight's debate on remote work.
SIDE-A: [excited] Remote work has proven to increase productivity across industries.
SIDE-B: [sarcastic] The data is far more nuanced than that claim suggests.
MODERATOR: [thoughtful] Let's dig into those numbers.
SIDE-A: Studies from Stanford show a 13% performance increase.
SIDE-B: But that study was limited to call center workers, hardly representative.
"""


@pytest.fixture
def sample_podcast_script() -> Script:
    return Script(
        format=Format.PODCAST,
        topic="AI Agents",
        segments=[
            Segment(index=0, speaker="host", text="[enthusiastic] Welcome to the show!", emotion_tag="enthusiastic"),
            Segment(index=1, speaker="cohost", text="[curious] Where do we even start?", emotion_tag="curious"),
            Segment(index=2, speaker="host", text="[thoughtful] Let's start with the basics.", emotion_tag="thoughtful"),
        ],
    )


@pytest.fixture
def sample_news_script() -> Script:
    return Script(
        format=Format.NEWS,
        topic="Quantum Computing",
        segments=[
            Segment(index=0, speaker="anchor", text="[serious] Good evening.", emotion_tag="serious"),
            Segment(index=1, speaker="anchor", text="Researchers at MIT made a breakthrough."),
        ],
    )
