from typer.testing import CliRunner

from repodoctor.cli import app

runner = CliRunner()


def test_help_describes_repository_check():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "repository" in result.stdout.lower()


def test_check_accepts_directory(tmp_path):
    result = runner.invoke(app, ["check", str(tmp_path)])

    assert result.exit_code == 0
    assert "Foundation ready" in result.stdout
    assert str(tmp_path.resolve()) in result.stdout


def test_check_preserves_markup_like_characters_in_target(tmp_path):
    target = tmp_path / "[red]repository"
    target.mkdir()

    result = runner.invoke(app, ["check", str(target)])

    assert result.exit_code == 0
    assert str(target.resolve()) in result.stdout


def test_check_rejects_missing_directory(tmp_path):
    target = tmp_path / "missing"

    result = runner.invoke(app, ["check", str(target)])

    assert result.exit_code != 0
    assert "does not exist" in result.stdout


def test_check_rejects_file(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("content", encoding="utf-8")

    result = runner.invoke(app, ["check", str(target)])

    assert result.exit_code != 0
    assert "not a directory" in result.stdout
