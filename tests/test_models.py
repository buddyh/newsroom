"""Tests for data models."""

from newsroom.models import Format, GeneratedAudio, Length, Script, Segment


class TestEnums:
    def test_format_values(self):
        assert set(Format) == {Format.NEWS, Format.PODCAST, Format.DEBATE, Format.NARRATIVE}

    def test_length_word_guidance(self):
        assert "300" in Length.SHORT.word_guidance
        assert "750" in Length.MEDIUM.word_guidance
        assert "1500" in Length.LONG.word_guidance


class TestSegment:
    def test_defaults(self):
        seg = Segment(index=0, speaker="host", text="Hello")
        assert seg.emotion_tag == ""
        assert seg.raw_text == ""

    def test_with_emotion_tag(self):
        seg = Segment(index=1, speaker="anchor", text="[serious] Breaking news", emotion_tag="serious")
        assert seg.emotion_tag == "serious"
        assert "[serious]" in seg.text

    def test_tags_stay_in_text(self):
        seg = Segment(index=0, speaker="host", text="[laughing] That's hilarious!", emotion_tag="laughing")
        assert seg.text == "[laughing] That's hilarious!"


class TestScript:
    def test_word_count(self, sample_podcast_script):
        assert sample_podcast_script.word_count > 0

    def test_speakers(self, sample_podcast_script):
        assert sample_podcast_script.speakers == {"host", "cohost"}

    def test_empty_script(self):
        s = Script(format=Format.NEWS, topic="Empty")
        assert s.word_count == 0
        assert s.speakers == set()


class TestGeneratedAudio:
    def test_construction(self, tmp_path):
        ga = GeneratedAudio(
            segment_index=0,
            file_path=tmp_path / "test.mp3",
            request_id="req_123",
            voice_id="voice_abc",
        )
        assert ga.segment_index == 0
        assert ga.request_id == "req_123"
