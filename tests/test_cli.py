"""CLI smoke tests using Typer's CliRunner."""

from unittest.mock import patch

from typer.testing import CliRunner

from newsroom.cli import app
from newsroom.models import Format, Script, Segment

runner = CliRunner()


class TestVoicesCommand:
    def test_shows_voice_assignments(self):
        result = runner.invoke(app, ["voices"])
        assert result.exit_code == 0
        assert "Voice Assignments" in result.output
        assert "NEWS" in result.output
        assert "PODCAST" in result.output

    def test_shows_voice_ids(self):
        result = runner.invoke(app, ["voices"])
        assert "cjVigY5qzO86Huf0OWal" in result.output


class TestConfigCommand:
    def test_shows_config(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        with patch("newsroom.cli.init_config", return_value=cfg_file):
            cfg_file.write_text("model: eleven_v3\n")
            result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "eleven_v3" in result.output


class TestGenerateCommand:
    def test_script_file_dry_run(self, tmp_path):
        """Primary flow: clawdbot provides a script file."""
        script_file = tmp_path / "script.txt"
        script_file.write_text(
            "HOST: [excited] Welcome to the show!\n"
            "CO-HOST: [laughing] Great to be here!\n"
        )
        out_dir = tmp_path / "out"

        result = runner.invoke(app, [
            "generate", "AI Agents",
            "--format", "podcast",
            "--script", str(script_file),
            "--dry-run",
            "--output", str(out_dir),
        ])

        assert result.exit_code == 0
        assert "Using provided script" in result.output
        assert "2 segments" in result.output
        assert "dry-run" in result.output
        # Script should be copied to run dir
        assert (out_dir / "script.txt").exists()

    def test_standalone_dry_run(self, tmp_path):
        """Standalone flow: auto-generate via OpenAI."""
        mock_script = Script(
            format=Format.NEWS,
            topic="Test Topic",
            segments=[
                Segment(index=0, speaker="anchor", text="[serious] Hello world."),
            ],
        )

        async def mock_gather(topic, run_dir):
            summary = run_dir / "research" / "summary.md"
            summary.parent.mkdir(parents=True, exist_ok=True)
            summary.write_text("# Research")
            return summary

        async def mock_gen_script(**kwargs):
            script_path = kwargs["run_dir"] / "script.txt"
            script_path.write_text("ANCHOR: [serious] Hello world.")
            return mock_script

        with (
            patch("newsroom.cli.load_config") as mock_cfg,
            patch("newsroom.research.gather_research", side_effect=mock_gather),
            patch("newsroom.scriptgen.generate_script", side_effect=mock_gen_script),
        ):
            mock_cfg.return_value.data_dir = tmp_path
            mock_cfg.return_value.openai_model = "gpt-4o"
            result = runner.invoke(app, [
                "generate", "Test Topic",
                "--format", "news",
                "--dry-run",
                "--output", str(tmp_path / "out"),
            ])

        assert result.exit_code == 0
        assert "dry-run" in result.output

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Usage" in result.output or "help" in result.output.lower()
