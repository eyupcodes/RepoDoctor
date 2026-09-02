from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class CheckStatus(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class FileContent:
    path: str
    lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    target: Path
    files: tuple[str, ...]
    directories: tuple[str, ...]
    contents: tuple[FileContent, ...]
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CheckResult:
    id: str
    status: CheckStatus
    summary: str
    paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RunResult:
    target: Path
    checks: tuple[CheckResult, ...]
    score: int

    @property
    def passed_checks(self) -> tuple[str, ...]:
        return tuple(
            check.id for check in self.checks if check.status is CheckStatus.PASS
        )

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(
            check.id for check in self.checks if check.status is CheckStatus.WARNING
        )

    @property
    def failures(self) -> tuple[str, ...]:
        return tuple(
            check.id for check in self.checks if check.status is CheckStatus.FAIL
        )
