# Newsroom

Turn any topic into a professional audio broadcast. Generates news briefings, podcasts, debates, and narratives using ElevenLabs v3 with native audio tag support for expressive voice control.

Built as a [Clawd](https://github.com/steipete/clawd) skill for the ElevenLabs + Clawdbot hackathon.

## Quick Start

```bash
pip install -e .
export ELEVENLABS_API_KEY=your_key

# Write a script and render it
newsroom generate "AI Agents" --script my_script.txt --format podcast

# Or let it auto-generate (requires OPENAI_API_KEY)
newsroom generate "AI Agents" --format podcast
```

## Requirements

- Python 3.11+
- ffmpeg
- `ELEVENLABS_API_KEY` (required)
- `OPENAI_API_KEY` (optional, for standalone script generation)
- `BRAVE_API_KEY` (optional, for topic research)

## How It Works

1. **Write a script** with ElevenLabs v3 audio tags for emotion and delivery control
2. **Newsroom parses** speaker turns and preserves tags inline
3. **Each segment** is sent to ElevenLabs v3 with request stitching for prosody continuity
4. **ffmpeg** concatenates the interleaved segments into a final MP3

### Script Format

One line per speaker turn. Audio tags are interpreted natively by ElevenLabs v3:

```
HOST: [excited] Welcome to the show! Today we're talking about AI agents.
CO-HOST: [laughing] Oh no, not again! [sigh] Just kidding, this is fascinating.
HOST: [thoughtful] So the big question is... can they actually replace us?
CO-HOST: [whisper] I hope not.
```

### Audio Tags

Tags can appear anywhere in the text - start of line, mid-sentence, or between sentences.

| Category | Tags |
|----------|------|
| Emotions | `[excited]` `[sad]` `[angry]` `[surprised]` `[thoughtful]` `[happy]` `[annoyed]` |
| Delivery | `[whisper]` `[sarcastic]` `[dramatic]` `[serious]` |
| Non-verbal | `[laughing]` `[sigh]` `[clears throat]` `[short pause]` `[long pause]` `[chuckles]` |

## Formats

| Format | Speakers | Style |
|--------|----------|-------|
| `news` | ANCHOR | Professional single anchor |
| `podcast` | HOST, CO-HOST | Two hosts with banter |
| `debate` | MODERATOR, SIDE-A, SIDE-B | Moderator + opposing sides |
| `narrative` | NARRATOR | Cinematic storytelling |

## CLI

```bash
newsroom generate "Topic" --script script.txt --format podcast  # Render a script
newsroom generate "Topic" --format news                          # Auto-generate
newsroom generate "Topic" --format debate --length long          # ~10 min debate
newsroom generate "Topic" --dry-run                              # Script only
newsroom voices                                                  # Show voice config
newsroom config                                                  # Show/init config
```

## Configuration

Voice assignments and model settings live in `~/.config/newsroom/config.yaml`. Run `newsroom config` to generate defaults.

```yaml
voices:
  anchor: cjVigY5qzO86Huf0OWal     # Eric
  host: cjVigY5qzO86Huf0OWal       # Eric
  cohost: TX3LPaxmHKxFdv7VOQHJ     # Liam
  moderator: cjVigY5qzO86Huf0OWal  # Eric
  sidea: TX3LPaxmHKxFdv7VOQHJ      # Liam
  sideb: EXAVITQu4vr4xnSAxGW1      # Bella
  narrator: nPczCjz82KWdKScP46A1    # Domi
model: eleven_v3
output_format: mp3_44100_128
```

## Request Stitching

Segments are generated in script order. Each voice tracks its last 3 request IDs, passed to subsequent ElevenLabs calls so the model matches prosody and style across the conversation.

## Tests

```bash
pip install -e .
pytest tests/ -v
```

## License

MIT
