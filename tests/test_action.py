"""The composite action's check step must report the score and gate the job."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="the step script is tested with POSIX shell tools"
)

ROOT = Path(__file__).resolve().parent.parent
ACTION = ROOT / "action.yml"
HEALTHY = ROOT / "examples" / "healthy-repository"


def _check_script() -> str:
    """The ``run`` block of the check step, dedented, read without a YAML parser."""
    lines = ACTION.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if "Check the repository" in ln)
    run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    block: list[str] = []
    for line in lines[run + 1 :]:
        if line.strip() and not line.startswith("        "):
            break
        block.append(line)
    return textwrap.dedent("\n".join(block))


def _run(
    tmp_path: Path, target: Path, *, min_score: str = "", sarif: str = "false"
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "repodoctor"
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m repodoctor "$@"\n')
    shim.chmod(0o755)
    runner_temp = tmp_path / "runner"
    runner_temp.mkdir()
    github_output = tmp_path / "github_output"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_OUTPUT": str(github_output),
        "TARGET": str(target),
        "MIN_SCORE": min_score,
        "WANT_SARIF": sarif,
    }
    done = subprocess.run(
        ["bash", "-e", "-c", _check_script()],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    text = github_output.read_text() if github_output.exists() else ""
    outputs = dict(line.split("=", 1) for line in text.splitlines())
    return done, outputs


def test_healthy_repository_passes_and_reports_the_score(tmp_path):
    done, outputs = _run(tmp_path, HEALTHY)
    assert done.returncode == 0, done.stderr
    assert outputs == {"score": "100", "sarif-file": ""}
    assert "Score: 100/100" in done.stdout


def test_failed_checks_fail_the_job_even_with_a_low_min_score(tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "README.md").write_text("# bare\n")
    done, outputs = _run(tmp_path, bare, min_score="10")
    assert done.returncode == 1
    assert int(outputs["score"]) < 100


def test_min_score_above_the_score_fails_the_job(tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    done, _ = _run(tmp_path, bare, min_score="100")
    assert done.returncode == 1


def test_sarif_input_writes_the_log_and_returns_its_path(tmp_path):
    done, outputs = _run(tmp_path, HEALTHY, sarif="true")
    assert done.returncode == 0, done.stderr
    sarif = Path(outputs["sarif-file"])
    assert sarif.name == "repodoctor.sarif"
    assert '"version": "2.1.0"' in sarif.read_text()


def test_a_missing_target_is_a_configuration_error(tmp_path):
    done, outputs = _run(tmp_path, tmp_path / "missing")
    assert done.returncode == 2
    assert "score" not in outputs
