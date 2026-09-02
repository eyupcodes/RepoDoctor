from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from repodoctor.config import ConfigError, RepoDoctorConfig


def test_defaults_target_to_current_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    config = RepoDoctorConfig.from_target(None)

    assert config.target == tmp_path.resolve()


def test_resolves_relative_directory(monkeypatch, tmp_path):
    target = tmp_path / "nested repo"
    target.mkdir()
    monkeypatch.chdir(tmp_path)

    config = RepoDoctorConfig.from_target(Path("nested repo"))

    assert config.target == target.resolve()


def test_rejects_missing_target(tmp_path):
    target = tmp_path / "missing"

    with pytest.raises(ConfigError, match="does not exist"):
        RepoDoctorConfig.from_target(target)


def test_rejects_file_target(tmp_path):
    target = tmp_path / "README.md"
    target.write_text("test", encoding="utf-8")

    with pytest.raises(ConfigError, match="not a directory"):
        RepoDoctorConfig.from_target(target)


def test_rejects_empty_target():
    with pytest.raises(ConfigError, match="must not be empty"):
        RepoDoctorConfig.from_target("")


def test_config_is_immutable(tmp_path):
    config = RepoDoctorConfig.from_target(tmp_path)

    with pytest.raises(FrozenInstanceError):
        config.target = Path.cwd()  # type: ignore[misc]
