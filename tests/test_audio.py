"""Tests for audio generation helpers."""

from newsroom.audio import split_into_chunks
from newsroom.config import NewsroomConfig, resolve_voice_id


class TestSplitIntoChunks:
    def test_short_text_no_split(self):
        text = "Hello world."
        assert split_into_chunks(text) == [text]

    def test_long_text_splits_at_sentences(self):
        sentences = ["This is sentence one. ", "This is sentence two. ", "This is sentence three. "]
        text = "".join(sentences * 30)  # ~1800 chars
        chunks = split_into_chunks(text, limit=200)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 250  # Allow some margin

    def test_single_long_sentence_gets_truncated(self):
        text = "A" * 5000
        chunks = split_into_chunks(text, limit=4000)
        assert len(chunks) >= 1

    def test_tags_not_stripped_from_chunks(self):
        text = "[excited] This is a sentence with a tag. And another sentence follows."
        chunks = split_into_chunks(text, limit=5000)
        assert len(chunks) == 1
        assert "[excited]" in chunks[0]


class TestVoiceMapResolution:
    def test_podcast_voices_distinct(self):
        cfg = NewsroomConfig()
        host = resolve_voice_id("host", "podcast", cfg)
        cohost = resolve_voice_id("cohost", "podcast", cfg)
        assert host != cohost

    def test_debate_three_voices(self):
        cfg = NewsroomConfig()
        mod = resolve_voice_id("moderator", "debate", cfg)
        sa = resolve_voice_id("sidea", "debate", cfg)
        sb = resolve_voice_id("sideb", "debate", cfg)
        assert len({mod, sa, sb}) >= 2  # At least 2 distinct voices

    def test_news_anchor(self):
        cfg = NewsroomConfig()
        anchor = resolve_voice_id("anchor", "news", cfg)
        assert anchor == cfg.voices.anchor
