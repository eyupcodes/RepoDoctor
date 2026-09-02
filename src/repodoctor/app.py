from dataclasses import dataclass
from pathlib import Path

from repodoctor.config import RepoDoctorConfig


@dataclass(frozen=True, slots=True)
class RunResult:
    target: Path
    passed_checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()


def run(config: RepoDoctorConfig) -> RunResult:
    """Prepare a validated repository target for future scans."""
    return RunResult(target=config.target)
