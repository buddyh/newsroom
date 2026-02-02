"""Shared data models for the newsroom pipeline."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class Format(str, Enum):
    NEWS = "news"
    PODCAST = "podcast"
    DEBATE = "debate"
    NARRATIVE = "narrative"


class Length(str, Enum):
    SHORT = "short"      # ~2 min, ~300 words
    MEDIUM = "medium"    # ~5 min, ~750 words
    LONG = "long"        # ~10 min, ~1500 words

    @property
    def word_guidance(self) -> str:
        return {
            Length.SHORT: "Keep it under 300 words (~2 minutes spoken).",
            Length.MEDIUM: "Aim for roughly 750 words (~5 minutes spoken).",
            Length.LONG: "Write approximately 1500 words (~10 minutes spoken).",
        }[self]


class Segment(BaseModel):
    """A single speaker turn in a script.

    The `text` field contains the full text including any [emotion] tags
    that ElevenLabs v3 interprets natively for voice steering.
    """
    index: int
    speaker: str
    text: str
    emotion_tag: str = ""
    raw_text: str = ""


class Script(BaseModel):
    """A complete parsed script ready for audio generation."""
    format: Format
    topic: str
    segments: list[Segment] = Field(default_factory=list)

    @property
    def word_count(self) -> int:
        return sum(len(s.text.split()) for s in self.segments)

    @property
    def speakers(self) -> set[str]:
        return {s.speaker for s in self.segments}


class GeneratedAudio(BaseModel):
    """Metadata for a generated audio segment."""
    segment_index: int
    file_path: Path
    request_id: str = ""
    voice_id: str = ""
