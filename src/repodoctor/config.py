from dataclasses import dataclass
from os import PathLike
from pathlib import Path


class ConfigError(ValueError):
    """Raised when repository configuration is invalid."""


@dataclass(frozen=True, slots=True)
class RepoDoctorConfig:
    target: Path

    @classmethod
    def from_target(cls, target: str | PathLike[str] | None) -> "RepoDoctorConfig":
        if isinstance(target, str) and not target.strip():
            raise ConfigError("Target path must not be empty.")
        if target is not None and not isinstance(target, (str, PathLike)):
            raise ConfigError("Target path must be a path-like value.")

        resolved_target = Path.cwd() if target is None else Path(target)
        resolved_target = resolved_target.expanduser().resolve()

        if not resolved_target.exists():
            raise ConfigError(f"Target path does not exist: {resolved_target}")
        if not resolved_target.is_dir():
            raise ConfigError(f"Target path is not a directory: {resolved_target}")

        return cls(target=resolved_target)
