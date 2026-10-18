from rich.console import Console
from rich.text import Text

from repodoctor.models import CheckStatus, RunResult

STATUS_STYLES = {
    CheckStatus.PASS: "green",
    CheckStatus.WARNING: "yellow",
    CheckStatus.FAIL: "red",
}


def _escape_control_codes(text: str) -> str:
    escaped: list[str] = []
    for char in str(text):
        code = ord(char)
        if char == "\x1b":
            escaped.append("\\x1b")
        elif 0 <= code < 32 or code == 127:
            escaped.append(f"\\x{code:02x}")
        else:
            escaped.append(char)
    return "".join(escaped)


def render_report(result: RunResult, console: Console) -> None:
    repository = Text("Repository: ", style="bold")
    repository.append(_escape_control_codes(str(result.target)))
    console.print(repository, soft_wrap=True)
    console.print(f"Score: {result.score}/100", style="bold")

    for check in result.checks:
        line = Text(
            f"{check.status.value:<5} {check.id}", style=STATUS_STYLES[check.status]
        )
        line.append(f" — {_escape_control_codes(check.summary)}")
        console.print(line)
        for path in check.paths:
            console.print(Text(f"       {_escape_control_codes(path)}"), soft_wrap=True)

    console.print(
        f"Summary: {len(result.passed_checks)} passed, "
        f"{len(result.warnings)} warnings, {len(result.failures)} failed"
    )


def result_to_dict(result: RunResult) -> dict[str, object]:
    """Return a JSON-serializable view of a run, without any matched secret values."""
    return {
        "target": str(result.target),
        "score": result.score,
        "summary": {
            "passed": len(result.passed_checks),
            "warnings": len(result.warnings),
            "failed": len(result.failures),
        },
        "checks": [
            {
                "id": check.id,
                "status": check.status.value,
                "summary": check.summary,
                "paths": list(check.paths),
            }
            for check in result.checks
        ],
    }
