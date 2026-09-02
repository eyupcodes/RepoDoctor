from io import StringIO
from pathlib import Path

from rich.console import Console

from repodoctor.app import run
from repodoctor.config import RepoDoctorConfig
from repodoctor.models import CheckResult, CheckStatus, RunResult
from repodoctor.report import render_report
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
