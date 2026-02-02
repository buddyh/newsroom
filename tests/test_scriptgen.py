"""Tests for script generation and parsing."""

from newsroom.models import Format
from newsroom.scriptgen import normalize_speaker, parse_script
from tests.conftest import SAMPLE_DEBATE_TEXT, SAMPLE_NEWS_TEXT, SAMPLE_PODCAST_TEXT


class TestNormalizeSpeaker:
    def test_basic_roles(self):
        assert normalize_speaker("HOST") == "host"
        assert normalize_speaker("ANCHOR") == "anchor"
        assert normalize_speaker("NARRATOR") == "narrator"

    def test_hyphenated_roles(self):
        assert normalize_speaker("CO-HOST") == "cohost"
        assert normalize_speaker("SIDE-A") == "sidea"
        assert normalize_speaker("SIDE-B") == "sideb"

    def test_unknown_passthrough(self):
        assert normalize_speaker("GUEST") == "guest"


class TestParseScript:
    def test_podcast_segments(self):
        script = parse_script(SAMPLE_PODCAST_TEXT, Format.PODCAST, "AI Agents")
        assert len(script.segments) == 6
        assert script.segments[0].speaker == "host"
        assert script.segments[0].emotion_tag == "enthusiastic"
        assert script.segments[1].speaker == "cohost"
        assert script.segments[1].emotion_tag == "curious"

    def test_tags_preserved_in_text(self):
        script = parse_script(SAMPLE_PODCAST_TEXT, Format.PODCAST, "AI Agents")
        # Tags stay in the text for ElevenLabs v3
        assert "[enthusiastic]" in script.segments[0].text
        assert "[curious]" in script.segments[1].text

    def test_no_tag_line_has_empty_emotion_tag(self):
        script = parse_script(SAMPLE_PODCAST_TEXT, Format.PODCAST, "AI Agents")
        # Last line has no tag
        last = script.segments[-1]
        assert last.emotion_tag == ""

    def test_news_single_speaker(self):
        script = parse_script(SAMPLE_NEWS_TEXT, Format.NEWS, "Quantum")
        assert all(s.speaker == "anchor" for s in script.segments)
        assert len(script.segments) == 3

    def test_debate_three_speakers(self):
        script = parse_script(SAMPLE_DEBATE_TEXT, Format.DEBATE, "Remote Work")
        speakers = script.speakers
        assert speakers == {"moderator", "sidea", "sideb"}

    def test_no_emotion_tag(self):
        raw = "HOST: Just a plain line without tags.\n"
        script = parse_script(raw, Format.PODCAST, "Test")
        assert len(script.segments) == 1
        assert script.segments[0].emotion_tag == ""
        assert script.segments[0].text == "Just a plain line without tags."

    def test_empty_input(self):
        script = parse_script("", Format.NEWS, "Empty")
        assert len(script.segments) == 0

    def test_preamble_ignored(self):
        raw = "Some preamble text\nHOST: [curious] Hello\nMore text\n"
        script = parse_script(raw, Format.PODCAST, "Test")
        assert len(script.segments) == 1
        assert "[curious]" in script.segments[0].text

    def test_inline_tags_mid_sentence(self):
        raw = "HOST: I was thinking [sigh] maybe we should try something new.\n"
        script = parse_script(raw, Format.PODCAST, "Test")
        seg = script.segments[0]
        assert "[sigh]" in seg.text
        # Leading tag is empty since [sigh] is mid-sentence
        assert seg.emotion_tag == ""
