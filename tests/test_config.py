"""Tests for configuration loading."""

from pathlib import Path
from unittest.mock import patch

import yaml

from newsroom.config import (
    CONFIG_PATH,
    SPEAKER_ALIASES,
    VOICE_MAP,
    NewsroomConfig,
    VoiceConfig,
    init_config,
    load_config,
    resolve_voice_id,
)


class TestDefaults:
    def test_default_config(self):
        cfg = NewsroomConfig()
        assert cfg.model == "eleven_v3"
        assert cfg.openai_model == "gpt-5-mini"
        assert cfg.output_format == "mp3_44100_128"

    def test_default_voices(self):
        v = VoiceConfig()
        assert v.anchor == "cjVigY5qzO86Huf0OWal"
        assert v.narrator == "nPczCjz82KWdKScP46A1"


class TestLoadConfig:
    def test_loads_from_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump({
            "model": "eleven_flash_v2_5",
            "voices": {"anchor": "custom_id"},
        }))
        with patch("newsroom.config.CONFIG_PATH", cfg_file):
            cfg = load_config()
        assert cfg.model == "eleven_flash_v2_5"
        assert cfg.voices.anchor == "custom_id"
        # Non-overridden fields keep defaults
        assert cfg.voices.narrator == "nPczCjz82KWdKScP46A1"

    def test_missing_file_returns_defaults(self):
        with patch("newsroom.config.CONFIG_PATH", Path("/nonexistent/config.yaml")):
            cfg = load_config()
        assert cfg.model == "eleven_v3"


class TestResolveVoiceId:
    def test_podcast_host(self):
        cfg = NewsroomConfig()
        vid = resolve_voice_id("HOST", "podcast", cfg)
        assert vid == cfg.voices.host

    def test_debate_sideb(self):
        cfg = NewsroomConfig()
        vid = resolve_voice_id("SIDE-B", "debate", cfg)
        assert vid == cfg.voices.sideb

    def test_unknown_role_fallback(self):
        cfg = NewsroomConfig()
        vid = resolve_voice_id("UNKNOWN_SPEAKER", "podcast", cfg)
        assert vid == cfg.voices.anchor  # falls back to anchor


class TestSpeakerAliases:
    def test_cohost_alias(self):
        assert SPEAKER_ALIASES["co-host"] == "cohost"

    def test_sidea_alias(self):
        assert SPEAKER_ALIASES["side-a"] == "sidea"


class TestVoiceMap:
    def test_all_formats_present(self):
        assert set(VOICE_MAP.keys()) == {"news", "podcast", "debate", "narrative"}

    def test_podcast_roles(self):
        assert set(VOICE_MAP["podcast"].keys()) == {"host", "cohost"}


class TestInitConfig:
    def test_creates_file(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        with patch("newsroom.config.CONFIG_PATH", cfg_file):
            result = init_config()
        assert result == cfg_file
        assert cfg_file.exists()
        data = yaml.safe_load(cfg_file.read_text())
        assert data["model"] == "eleven_v3"

    def test_does_not_overwrite(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("custom: true\n")
        with patch("newsroom.config.CONFIG_PATH", cfg_file):
            init_config()
        assert "custom: true" in cfg_file.read_text()
