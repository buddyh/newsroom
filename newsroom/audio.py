"""ElevenLabs TTS generation and ffmpeg mixing.

Uses ElevenLabs v3's native audio tag support for emotion/delivery control.
Tags like [laughing], [whisper], [excited] are passed inline in the text
and interpreted directly by the model - no VoiceSettings manipulation needed.
"""

import subprocess
from collections import defaultdict
from pathlib import Path

from elevenlabs.client import ElevenLabs

from newsroom.config import NewsroomConfig, resolve_voice_id
from newsroom.models import GeneratedAudio, Script, Segment

# Character limit per ElevenLabs request (leaving margin from 5000 hard limit)
CHUNK_LIMIT = 4000


def split_into_chunks(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    """Split text at sentence boundaries to stay under the character limit."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""

    for sentence in _split_sentences(text):
        if current and len(current) + len(sentence) > limit:
            chunks.append(current.strip())
            current = sentence
        else:
            current += sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks or [text[:limit]]


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-like chunks preserving delimiters."""
    parts: list[str] = []
    current = ""
    for char in text:
        current += char
        if char in ".!?" and len(current) > 1:
            parts.append(current)
            current = ""
    if current:
        parts.append(current)
    return parts


def _get_adjacent_text(
    segments: list[Segment], idx: int, voice_id: str, config: NewsroomConfig
) -> tuple[str, str]:
    """Get previous_text and next_text from adjacent same-speaker segments."""
    prev_text = ""
    next_text = ""

    # Look backward for same voice
    for i in range(idx - 1, max(idx - 4, -1), -1):
        seg = segments[i]
        seg_voice = resolve_voice_id(seg.speaker, "", config)
        if seg_voice == voice_id:
            prev_text = seg.text[-200:]
            break

    # Look forward for same voice
    for i in range(idx + 1, min(idx + 4, len(segments))):
        seg = segments[i]
        seg_voice = resolve_voice_id(seg.speaker, "", config)
        if seg_voice == voice_id:
            next_text = seg.text[:200]
            break

    return prev_text, next_text


def generate_audio(
    script: Script,
    config: NewsroomConfig,
    audio_dir: Path,
) -> list[GeneratedAudio]:
    """Generate audio for all segments with request stitching.

    Processes segments in script order (interleaved) for natural dialogue.
    Emotion/delivery tags in the text are handled natively by ElevenLabs v3.
    Uses previous_request_ids per voice for prosody continuity.
    """
    audio_dir.mkdir(parents=True, exist_ok=True)
    client = ElevenLabs()

    # Track request IDs per voice for stitching (max 3)
    voice_request_ids: dict[str, list[str]] = defaultdict(list)
    results: list[GeneratedAudio] = []

    for seg in script.segments:
        voice_id = resolve_voice_id(seg.speaker, script.format.value, config)
        prev_text, next_text = _get_adjacent_text(
            script.segments, seg.index, voice_id, config,
        )
        prev_ids = voice_request_ids[voice_id][-3:]

        chunks = split_into_chunks(seg.text)
        chunk_files: list[Path] = []

        for ci, chunk_text in enumerate(chunks):
            if len(chunks) > 1:
                out_path = audio_dir / f"{seg.index:03d}_{seg.speaker}_chunk{ci}.mp3"
            else:
                out_path = audio_dir / f"{seg.index:03d}_{seg.speaker}.mp3"

            # For multi-chunk: use previous chunk text as context
            chunk_prev = chunks[ci - 1][-200:] if ci > 0 else prev_text
            chunk_next = chunks[ci + 1][:200] if ci < len(chunks) - 1 else next_text

            request_id = _generate_segment(
                client=client,
                text=chunk_text,
                voice_id=voice_id,
                model_id=config.model,
                output_format=config.output_format,
                previous_text=chunk_prev or None,
                next_text=chunk_next or None,
                previous_request_ids=prev_ids or None,
                out_path=out_path,
            )

            chunk_files.append(out_path)
            if request_id:
                voice_request_ids[voice_id].append(request_id)

        # If multiple chunks, concatenate them into a single segment file
        if len(chunk_files) > 1:
            final_path = audio_dir / f"{seg.index:03d}_{seg.speaker}.mp3"
            _concat_files(chunk_files, final_path)
            for cf in chunk_files:
                cf.unlink(missing_ok=True)
        else:
            final_path = chunk_files[0]

        results.append(GeneratedAudio(
            segment_index=seg.index,
            file_path=final_path,
            request_id=voice_request_ids[voice_id][-1] if voice_request_ids[voice_id] else "",
            voice_id=voice_id,
        ))

        tag_display = f" [{seg.emotion_tag}]" if seg.emotion_tag else ""
        print(f"  [{seg.index + 1}/{len(script.segments)}] {seg.speaker}{tag_display} - {final_path.name}")

    return results


def _generate_segment(
    client: ElevenLabs,
    text: str,
    voice_id: str,
    model_id: str,
    output_format: str,
    previous_text: str | None,
    next_text: str | None,
    previous_request_ids: list[str] | None,
    out_path: Path,
) -> str:
    """Generate a single TTS segment, returning the request_id for stitching.

    The text is passed directly to ElevenLabs including any [tags] -
    v3 interprets these natively for emotion, delivery, and non-verbal sounds.
    """
    # ElevenLabs v3 does not yet support previous/next_text context
    if model_id == "eleven_v3":
        previous_text = None
        next_text = None
        previous_request_ids = None

    with client.text_to_speech.with_raw_response.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format=output_format,
        previous_text=previous_text,
        next_text=next_text,
        previous_request_ids=previous_request_ids,
    ) as response:
        request_id = response._response.headers.get("request-id", "")
        audio_data = b"".join(chunk for chunk in response.data)

    out_path.write_bytes(audio_data)
    return request_id


def _concat_files(files: list[Path], output: Path) -> None:
    """Concatenate MP3 files using ffmpeg."""
    concat_txt = output.parent / f"{output.stem}_concat.txt"
    concat_txt.write_text("\n".join(f"file '{f}'" for f in files))
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_txt), "-c", "copy", str(output)],
            capture_output=True,
            check=True,
        )
    finally:
        concat_txt.unlink(missing_ok=True)


def concat_final(audio_files: list[GeneratedAudio], output: Path) -> Path:
    """Concatenate all segment audio files into the final MP3."""
    sorted_files = sorted(audio_files, key=lambda a: a.segment_index)
    file_paths = [a.file_path for a in sorted_files if a.file_path.exists()]

    if not file_paths:
        raise RuntimeError("No audio files to concatenate")

    concat_txt = output.parent / "concat.txt"
    concat_txt.write_text("\n".join(f"file '{f}'" for f in file_paths))

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_txt), "-c", "copy", str(output)],
        capture_output=True,
        check=True,
    )

    return output
