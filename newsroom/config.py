"""Configuration loading with YAML + Pydantic defaults."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

CONFIG_PATH = Path.home() / ".config" / "newsroom" / "config.yaml"
DATA_DIR = Path.home() / ".clawd" / "skills" / "newsroom"


class VoiceConfig(BaseModel):
    """Voice ID assignments per speaker role."""
    anchor: str = "cjVigY5qzO86Huf0OWal"     # Eric
    host: str = "cjVigY5qzO86Huf0OWal"        # Eric
    cohost: str = "TX3LPaxmHKxFdv7VOQHJ"      # Liam
    moderator: str = "cjVigY5qzO86Huf0OWal"   # Eric
    sidea: str = "TX3LPaxmHKxFdv7VOQHJ"       # Liam
    sideb: str = "EXAVITQu4vr4xnSAxGW1"       # Bella
    narrator: str = "nPczCjz82KWdKScP46A1"     # Domi


class NewsroomConfig(BaseModel):
    """Top-level newsroom configuration."""
    voices: VoiceConfig = Field(default_factory=VoiceConfig)
    model: str = "eleven_v3"
    output_format: str = "mp3_44100_128"
    openai_model: str = "gpt-5-mini"
    data_dir: Path = DATA_DIR


# Speaker role -> voice config field mapping per format
VOICE_MAP: dict[str, dict[str, str]] = {
    "news": {"anchor": "anchor"},
    "podcast": {"host": "host", "cohost": "cohost"},
    "debate": {"moderator": "moderator", "sidea": "sidea", "sideb": "sideb"},
    "narrative": {"narrator": "narrator"},
}

# Script speaker labels -> normalized role names
SPEAKER_ALIASES: dict[str, str] = {
    "anchor": "anchor",
    "host": "host",
    "co-host": "cohost",
    "cohost": "cohost",
    "moderator": "moderator",
    "side-a": "sidea",
    "sidea": "sidea",
    "side-b": "sideb",
    "sideb": "sideb",
    "narrator": "narrator",
}


def load_config() -> NewsroomConfig:
    """Load config from YAML file, falling back to defaults."""
    if CONFIG_PATH.exists():
        raw = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        return NewsroomConfig(**raw)
    return NewsroomConfig()


def resolve_voice_id(role: str, format_name: str, config: NewsroomConfig) -> str:
    """Get the ElevenLabs voice ID for a speaker role in a given format."""
    normalized = SPEAKER_ALIASES.get(role.lower(), role.lower())
    voice_field = VOICE_MAP.get(format_name, {}).get(normalized)
    if voice_field:
        return getattr(config.voices, voice_field, config.voices.anchor)
    # Fallback: try direct attribute lookup
    return getattr(config.voices, normalized, config.voices.anchor)


def init_config() -> Path:
    """Generate a default config.yaml if one doesn't exist."""
    if CONFIG_PATH.exists():
        return CONFIG_PATH
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    defaults = NewsroomConfig()
    data = {
        "voices": defaults.voices.model_dump(),
        "model": defaults.model,
        "output_format": defaults.output_format,
        "openai_model": defaults.openai_model,
    }
    CONFIG_PATH.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return CONFIG_PATH
