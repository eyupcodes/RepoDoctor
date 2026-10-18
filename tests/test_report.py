from io import StringIO
from pathlib import Path

from rich.console import Console

from repodoctor.app import run
from repodoctor.config import RepoDoctorConfig
from repodoctor.models import CheckResult, CheckStatus, RunResult
from repodoctor.report import render_report, result_to_dict
from tests.helpers import make_healthy_repository


def test_report_contains_score_checks_and_summary(tmp_path):
    make_healthy_repository(tmp_path)
    output = StringIO()

    render_report(
        run(RepoDoctorConfig.from_target(tmp_path)),
        Console(file=output, color_system=None, width=120),
    )

    report = output.getvalue()
    assert "Score: 100/100" in report
    assert "PASS  readme" in report
    assert "6 passed, 0 warnings, 0 failed" in report


def test_report_escapes_control_characters_in_paths():
    result = RunResult(
        target=Path("/repo"),
        checks=(
            CheckResult(
                id="secret-risk",
                status=CheckStatus.FAIL,
                summary="Found 1 potential secret risk(s).",
                paths=("bad\x1bname.env:1 (credential assignment)",),
            ),
        ),
        score=60,
    )
    output = StringIO()

    render_report(result, Console(file=output, color_system=None, width=120))

    report = output.getvalue()
    assert "\x1b" not in report
    assert "\\x1b" in report


def test_result_to_dict_lists_checks_and_summary_counts():
    result = RunResult(
        target=Path("/repo"),
        checks=(
            CheckResult(id="readme", status=CheckStatus.PASS, summary="Found."),
            CheckResult(
                id="secret-risk",
                status=CheckStatus.FAIL,
                summary="Found 1 potential secret risk(s).",
                paths=("config.txt:1 (credential assignment)",),
            ),
        ),
        score=60,
    )

    data = result_to_dict(result)

    assert data["score"] == 60
    assert data["summary"] == {"passed": 1, "warnings": 0, "failed": 1}
    assert data["checks"][1] == {
        "id": "secret-risk",
        "status": "FAIL",
        "summary": "Found 1 potential secret risk(s).",
        "paths": ["config.txt:1 (credential assignment)"],
    }
    assert data["target"] == str(Path("/repo"))
