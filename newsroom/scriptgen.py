"""OpenAI script generation and parsing."""

import re
from pathlib import Path

from openai import AsyncOpenAI

from newsroom.models import Format, Length, Script, Segment
from newsroom.config import SPEAKER_ALIASES


# Format-specific system prompts.
# Emotion/delivery tags are kept in the text because ElevenLabs v3 interprets
# them natively as audio tags: [laughing], [whisper], [excited], [sigh], etc.
_NO_TV = (
    "This is AUDIO ONLY, not television. Never use TV-isms like "
    "'thanks for watching', 'you're watching X', 'tune in next time', "
    "'good evening I'm X', or any visual references. "
    "Jump straight into the content. No show names, no sign-offs, no self-introductions."
)

SYSTEM_PROMPTS: dict[Format, str] = {
    Format.NEWS: (
        "You are a professional news anchor scriptwriter. "
        "Write a broadcast script for a single ANCHOR. "
        "Be professional, concise, and informative. "
        f"{_NO_TV} "
        "Use ElevenLabs v3 audio tags inline to control delivery: "
        "[serious], [excited], [whisper], [sigh], [thoughtful], etc. "
        "Format each line as: ANCHOR: [tag] text... with tags woven into the dialogue naturally."
    ),
    Format.PODCAST: (
        "You are a professional podcast producer. "
        "Write a script for two hosts: HOST and CO-HOST. "
        "Include natural banter, interruptions, and diverse intonation. "
        f"{_NO_TV} "
        "Use ElevenLabs v3 audio tags inline to control delivery: "
        "[laughing], [surprised], [excited], [whisper], [sigh], [thoughtful], etc. "
        "Tags can appear anywhere in the text, not just at the start. "
        "Format each line as: SPEAKER: text with [tags] woven in naturally."
    ),
    Format.DEBATE: (
        "You are a debate show producer. "
        "Write a script for MODERATOR and two debaters SIDE-A and SIDE-B. "
        "Arguments should be sharp but civil with clear opposing viewpoints. "
        f"{_NO_TV} "
        "Use ElevenLabs v3 audio tags inline to control delivery: "
        "[angry], [sarcastic], [thoughtful], [excited], [annoyed], [surprised], etc. "
        "Tags can appear anywhere in the text. "
        "Format each line as: SPEAKER: text with [tags] woven in naturally."
    ),
    Format.NARRATIVE: (
        "You are a documentary scriptwriter. "
        "Write a script for a single NARRATOR. "
        "The style is cinematic and gripping, building tension and atmosphere. "
        f"{_NO_TV} "
        "Use ElevenLabs v3 audio tags inline to control delivery: "
        "[whisper], [excited], [sad], [sigh], [long pause], [dramatic], etc. "
        "Tags can appear anywhere in the text for natural pacing. "
        "Format each line as: NARRATOR: text with [tags] woven in naturally."
    ),
}

# Regex: SPEAKER: rest-of-line (tags stay in the text, not extracted)
_LINE_RE = re.compile(
    r"^(?P<speaker>[A-Z][A-Z0-9 _-]+?):\s*(?P<text>.+)",
    re.MULTILINE,
)

# Optional: capture a leading [tag] if present (for metadata only)
_LEADING_TAG_RE = re.compile(r"^\[(?P<tag>[^\]]+)\]\s*")


def normalize_speaker(raw: str) -> str:
    """Normalize a speaker label to a canonical role name."""
    cleaned = raw.strip().lower().replace("_", "-")
    return SPEAKER_ALIASES.get(cleaned, cleaned)


def parse_script(text: str, fmt: Format, topic: str) -> Script:
    """Parse a raw script string into structured Segment objects.

    Emotion/delivery tags like [laughing] are kept in the segment text
    so ElevenLabs v3 can interpret them directly.
    """
    segments: list[Segment] = []
    idx = 0

    for match in _LINE_RE.finditer(text):
        speaker = normalize_speaker(match.group("speaker"))
        line_text = match.group("text").strip()

        if not line_text:
            continue

        # Extract leading tag for metadata (but keep it in the text)
        tag_match = _LEADING_TAG_RE.match(line_text)
        emotion_tag = tag_match.group("tag") if tag_match else ""

        segments.append(Segment(
            index=idx,
            speaker=speaker,
            text=line_text,
            emotion_tag=emotion_tag,
            raw_text=match.group(0),
        ))
        idx += 1

    return Script(format=fmt, topic=topic, segments=segments)


async def generate_script(
    topic: str,
    fmt: Format,
    length: Length,
    research_md: str,
    run_dir: Path,
    model: str = "gpt-5-mini",
) -> Script:
    """Generate a script via OpenAI and parse it."""
    system = SYSTEM_PROMPTS[fmt] + f"\n\n{length.word_guidance}"

    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Research:\n{research_md}\n\n"
        "Write the script now. Output ONLY the dialogue lines in the format:\n"
        "SPEAKER: [optional tag] text with more [tags] inline as needed\n\n"
        "One line per speaker turn. No stage directions, no headers, no markdown."
    )

    client = AsyncOpenAI()
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_script = resp.choices[0].message.content or ""

    # Save raw script
    script_path = run_dir / "script.txt"
    script_path.write_text(raw_script)
    print(f"  Script saved: {script_path}")

    return parse_script(raw_script, fmt, topic)
