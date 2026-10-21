import json

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
    assert "does not exist" in result.stderr
    assert result.stdout == ""


def test_check_rejects_file(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("content", encoding="utf-8")

    result = runner.invoke(app, ["check", str(target)])

    assert result.exit_code == 2
    assert "not a directory" in result.stderr
    assert result.stdout == ""


def test_json_output_for_healthy_repository(tmp_path):
    make_healthy_repository(tmp_path)

    result = runner.invoke(app, ["check", str(tmp_path), "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["score"] == 100
    assert data["summary"] == {"passed": 6, "warnings": 0, "failed": 0}
    assert [check["id"] for check in data["checks"]][-1] == "secret-risk"
    assert "Score:" not in result.stdout


def test_json_output_keeps_exit_code_and_hides_secret_values(tmp_path):
    (tmp_path / "config.txt").write_text("API_KEY=hunter2hunter2\n", encoding="utf-8")

    result = runner.invoke(app, ["check", str(tmp_path), "--json"])

    assert result.exit_code == 1
    data = json.loads(result.stdout)
    secret = next(c for c in data["checks"] if c["id"] == "secret-risk")
    assert secret["status"] == "FAIL"
    assert secret["paths"] == ["config.txt:1 (credential assignment)"]
    assert "hunter2" not in result.stdout


def test_json_flag_does_not_hide_config_errors(tmp_path):
    result = runner.invoke(app, ["check", str(tmp_path / "missing"), "--json"])

    assert result.exit_code == 2
    assert "does not exist" in result.stderr
    assert result.stdout == ""


def test_sarif_output_reports_secret_location_without_value(tmp_path):
    (tmp_path / "config.txt").write_text("API_KEY=hunter2hunter2\n", encoding="utf-8")

    result = runner.invoke(app, ["check", str(tmp_path), "--sarif"])

    assert result.exit_code == 1
    log = json.loads(result.stdout)
    assert log["version"] == "2.1.0"
    located = [r for r in log["runs"][0]["results"] if r["ruleId"] == "secret-risk"]
    region = located[0]["locations"][0]["physicalLocation"]["region"]
    assert region["startLine"] == 1
    assert "hunter2" not in result.stdout
    assert "Score:" not in result.stdout


def test_sarif_output_for_healthy_repository_has_no_results(tmp_path):
    make_healthy_repository(tmp_path)

    result = runner.invoke(app, ["check", str(tmp_path), "--sarif"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["runs"][0]["results"] == []


def test_sarif_and_json_are_mutually_exclusive(tmp_path):
    result = runner.invoke(app, ["check", str(tmp_path), "--json", "--sarif"])

    assert result.exit_code == 2
    assert "mutually exclusive" in result.stderr
    assert result.stdout == ""
