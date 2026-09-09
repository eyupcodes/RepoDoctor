from pathlib import Path

from typer.testing import CliRunner

from repodoctor import __version__
from repodoctor.checks import evaluate_repository
from repodoctor.cli import app
from repodoctor.models import CheckStatus, RepositorySnapshot
from repodoctor.report import _escape_control_codes
from repodoctor.scanner import _sanitize_relative_path, scan_repository
from tests.helpers import make_healthy_repository

runner = CliRunner()


def test_private_key_detected_in_file(tmp_path):
    make_healthy_repository(tmp_path)
    key_content = (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg...\n"
        "-----END PRIVATE KEY-----\n"
    )
    (tmp_path / "server.key").write_text(key_content, encoding="utf-8")

    snapshot = scan_repository(tmp_path)
    checks = evaluate_repository(snapshot)
    secret_check = checks[-1]

    assert secret_check.status is CheckStatus.FAIL
    assert any("server.key:1 (private key)" in p for p in secret_check.paths)


def test_rsa_and_openssh_private_keys_detected(tmp_path):
    make_healthy_repository(tmp_path)
    (tmp_path / "id_rsa").write_text(
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "fake\n"
        "-----END RSA PRIVATE KEY-----\n",
        encoding="utf-8",
    )
    (tmp_path / "id_ed25519").write_text(
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "fake\n"
        "-----END OPENSSH PRIVATE KEY-----\n",
        encoding="utf-8",
    )

    snapshot = scan_repository(tmp_path)
    checks = evaluate_repository(snapshot)
    secret_check = checks[-1]

    assert secret_check.status is CheckStatus.FAIL
    assert any("id_rsa:1 (private key)" in p for p in secret_check.paths)
    assert any("id_ed25519:1 (private key)" in p for p in secret_check.paths)


def test_warning_when_diagnostics_present_without_secrets():
    snapshot = RepositorySnapshot(
        target=Path("/repo"),
        files=("unreadable.txt",),
        directories=(),
        contents=(),
        diagnostics=("unreadable.txt (file too large)",),
    )

    checks = evaluate_repository(snapshot)
    secret_check = checks[-1]

    assert secret_check.status is CheckStatus.WARNING
    assert secret_check.summary == "Some files could not be inspected."
    assert secret_check.paths == ("unreadable.txt (file too large)",)


def test_scanner_handles_non_utf8_text_file(tmp_path):
    (tmp_path / "corrupt.txt").write_bytes(b"\xff\xfe\xfa\xfb")

    snapshot = scan_repository(tmp_path)

    assert "corrupt.txt" in snapshot.files
    assert snapshot.contents == ()
    assert "corrupt.txt" in snapshot.diagnostics


def test_scanner_handles_file_stat_oserror(monkeypatch, tmp_path):
    file_path = tmp_path / "broken.txt"
    file_path.write_text("hello", encoding="utf-8")

    original_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        if self.name == "broken.txt":
            raise OSError("Permission denied")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", mock_stat)

    snapshot = scan_repository(tmp_path)
    assert "broken.txt" in snapshot.files
    assert "broken.txt" in snapshot.diagnostics


def test_scanner_handles_directory_error_callback(tmp_path):
    fake_target = tmp_path / "repo"
    fake_target.mkdir()
    sub = fake_target / "locked"
    sub.mkdir()

    error = OSError("Permission denied")
    error.filename = str(sub)

    import os

    original_walk = os.walk

    def mock_walk(top, **kwargs):
        onerror = kwargs.get("onerror")
        if onerror:
            onerror(error)
        return original_walk(top, **kwargs)

    original_os_walk = os.walk
    try:
        os.walk = mock_walk
        snapshot = scan_repository(fake_target)
        assert any("locked (directory access error)" in d for d in snapshot.diagnostics)
    finally:
        os.walk = original_os_walk


def test_nested_readme_and_license_do_not_satisfy_checks(tmp_path):
    nested = tmp_path / "subfolder"
    nested.mkdir()
    (nested / "README.md").write_text("# Nested", encoding="utf-8")
    (nested / "LICENSE").write_text("MIT", encoding="utf-8")
    (nested / ".gitignore").write_text("*.pyc", encoding="utf-8")

    snapshot = scan_repository(tmp_path)
    checks = evaluate_repository(snapshot)

    assert checks[0].status is CheckStatus.FAIL  # readme
    assert checks[1].status is CheckStatus.FAIL  # license
    assert checks[2].status is CheckStatus.FAIL  # gitignore


def test_path_sanitizer_escapes_c0_and_del():
    raw = "test\x1b[31m\x00\x07\x7fdir"
    sanitized = _sanitize_relative_path(raw)
    assert "\x1b" not in sanitized
    assert "\\x1b" in sanitized
    assert "\\x00" in sanitized
    assert "\\x07" in sanitized
    assert "\\x7f" in sanitized


def test_report_escape_control_codes():
    raw = "msg\x1b\x01\x1f\x7f"
    escaped = _escape_control_codes(raw)
    assert "\x1b" not in escaped
    assert "\\x1b" in escaped
    assert "\\x01" in escaped
    assert "\\x1f" in escaped
    assert "\\x7f" in escaped


def test_empty_repository_evaluation(tmp_path):
    snapshot = scan_repository(tmp_path)
    checks = evaluate_repository(snapshot)

    assert all(c.status is CheckStatus.FAIL for c in checks[:5])
    assert checks[-1].status is CheckStatus.PASS
    assert checks[-1].id == "secret-risk"


def test_mixed_newlines_handled(tmp_path):
    make_healthy_repository(tmp_path)
    (tmp_path / "crlf.txt").write_bytes(
        b"API_KEY=synthetic-val-1\r\nDATABASE_URL=postgres://user:pass@localhost:5432/db\n"
    )

    snapshot = scan_repository(tmp_path)
    checks = evaluate_repository(snapshot)
    secret_check = checks[-1]

    assert secret_check.status is CheckStatus.FAIL
    assert any("crlf.txt:1 (credential assignment)" in p for p in secret_check.paths)
    assert any("crlf.txt:2 (credential assignment)" in p for p in secret_check.paths)


def test_cli_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
