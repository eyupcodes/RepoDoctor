from typer.testing import CliRunner

from repodoctor.cli import app
from tests.helpers import make_healthy_repository

runner = CliRunner()


def test_help_describes_repository_check():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "repository" in result.stdout.lower()


def test_check_reports_healthy_repository(tmp_path):
    make_healthy_repository(tmp_path)

    result = runner.invoke(app, ["check", str(tmp_path)])

    assert result.exit_code == 0
    assert "Score: 100/100" in result.stdout
    assert "6 passed, 0 warnings, 0 failed" in result.stdout


def test_check_returns_one_for_findings(tmp_path):
    result = runner.invoke(app, ["check", str(tmp_path)])

    assert result.exit_code == 1
    assert "Score: 25/100" in result.stdout
    assert "5 failed" in result.stdout


def test_check_preserves_markup_like_characters_in_target(tmp_path):
    target = tmp_path / "[red]repository"
    target.mkdir()

    result = runner.invoke(app, ["check", str(target)])

    assert str(target.resolve()) in result.stdout


def test_check_rejects_missing_directory(tmp_path):
    result = runner.invoke(app, ["check", str(tmp_path / "missing")])
    assert result.exit_code == 2
    assert "does not exist" in result.stdout


def test_check_rejects_file(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("content", encoding="utf-8")

    result = runner.invoke(app, ["check", str(target)])

    assert result.exit_code == 2
    assert "not a directory" in result.stdout
