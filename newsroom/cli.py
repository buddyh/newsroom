"""Typer CLI for the newsroom audio pipeline."""

import asyncio
import re
from pathlib import Path
from typing import Annotated, Optional

import typer

from newsroom.config import (
    VOICE_MAP,
    NewsroomConfig,
    init_config,
    load_config,
)
from newsroom.models import Format, Length

app = typer.Typer(
    name="newsroom",
    help="AI Newsroom: Generate professional audio from any topic.",
    no_args_is_help=True,
)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", text.lower().replace(" ", "-"))


@app.command()
def generate(
    topic: Annotated[str, typer.Argument(help="Topic or description for the broadcast")],
    format: Annotated[Format, typer.Option("--format", "-f", help="Output format")] = Format.NEWS,
    length: Annotated[Length, typer.Option("--length", "-l", help="Script length (for auto-gen only)")] = Length.MEDIUM,
    script: Annotated[Optional[Path], typer.Option("--script", "-s", help="Pre-written script file to render")] = None,
    model: Annotated[Optional[str], typer.Option("--model", help="OpenAI model override (for auto-gen only)")] = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Custom output directory")] = None,
    skip_research: Annotated[bool, typer.Option("--skip-research", help="Skip Brave Search research")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Generate script only, no audio")] = False,
) -> None:
    """Generate an audio broadcast from a topic or pre-written script."""
    config = load_config()
    slug = _slugify(topic)

    if output:
        run_dir = output
    else:
        run_dir = config.data_dir / slug / format.value

    run_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Newsroom: {format.value} | {topic}")
    typer.echo(f"Output: {run_dir}")
    typer.echo("")

    asyncio.run(_run_pipeline(
        topic=topic,
        fmt=format,
        length=length,
        config=config,
        run_dir=run_dir,
        script_path=script,
        openai_model=model or config.openai_model,
        skip_research=skip_research,
        dry_run=dry_run,
    ))


async def _run_pipeline(
    topic: str,
    fmt: Format,
    length: Length,
    config: NewsroomConfig,
    run_dir: Path,
    script_path: Path | None,
    openai_model: str,
    skip_research: bool,
    dry_run: bool,
) -> None:
    from newsroom.scriptgen import parse_script
    from newsroom.audio import concat_final, generate_audio

    # If a script file is provided, skip research and generation entirely
    if script_path:
        typer.echo("[1/2] Using provided script")
        raw_script = script_path.read_text()
        # Save a copy in the run dir
        (run_dir / "script.txt").write_text(raw_script)
        parsed = parse_script(raw_script, fmt, topic)
    else:
        # Standalone mode: use Brave + OpenAI
        from newsroom.research import gather_research
        from newsroom.scriptgen import generate_script

        if skip_research:
            typer.echo("[1/3] Skipping research")
            research_md = f"Topic: {topic}\nNo research gathered."
        else:
            typer.echo("[1/3] Researching...")
            summary_path = await gather_research(topic, run_dir)
            research_md = summary_path.read_text()

        typer.echo("[2/3] Generating script...")
        parsed = await generate_script(
            topic=topic,
            fmt=fmt,
            length=length,
            research_md=research_md,
            run_dir=run_dir,
            model=openai_model,
        )

    typer.echo(f"  {len(parsed.segments)} segments, {parsed.word_count} words")
    typer.echo(f"  Speakers: {', '.join(sorted(parsed.speakers))}")

    if dry_run:
        typer.echo("\n[dry-run] Script ready. Skipping audio.")
        typer.echo(f"Script: {run_dir / 'script.txt'}")
        return

    # Audio generation
    step = "[2/2]" if script_path else "[3/3]"
    typer.echo(f"{step} Generating audio...")
    audio_dir = run_dir / "audio"
    audio_files = generate_audio(parsed, config, audio_dir)

    # Final mix
    final_path = run_dir / "final.mp3"
    concat_final(audio_files, final_path)
    typer.echo(f"\nDone: {final_path}")
    # Protocol for Clawdbot to auto-upload
    typer.echo(f"MEDIA: {final_path}")


@app.command()
def voices() -> None:
    """Show configured voice assignments."""
    config = load_config()
    typer.echo("Voice Assignments")
    typer.echo("=" * 40)
    for fmt_name, roles in VOICE_MAP.items():
        typer.echo(f"\n{fmt_name.upper()}:")
        for role, field in roles.items():
            vid = getattr(config.voices, field)
            typer.echo(f"  {role:<12} {vid}")


@app.command()
def config() -> None:
    """Show or initialize the config file."""
    path = init_config()
    typer.echo(f"Config: {path}")
    typer.echo("")
    typer.echo(path.read_text())
