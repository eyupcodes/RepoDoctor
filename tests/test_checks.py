from repodoctor.checks import evaluate_repository
from repodoctor.models import CheckStatus
from repodoctor.scanner import scan_repository
from tests.helpers import make_healthy_repository


def test_all_checks_pass_for_healthy_repository(tmp_path):
    make_healthy_repository(tmp_path)

    checks = evaluate_repository(scan_repository(tmp_path))

    assert [check.id for check in checks] == [
        "readme",
        "license",
        "gitignore",
        "tests",
        "ci",
        "secret-risk",
    ]
    assert all(check.status is CheckStatus.PASS for check in checks)


def test_missing_structure_checks_fail(tmp_path):
    checks = evaluate_repository(scan_repository(tmp_path))

    assert all(check.status is CheckStatus.FAIL for check in checks[:5])
    assert checks[-1].status is CheckStatus.PASS


def test_secret_risk_reports_location_without_value(tmp_path):
    make_healthy_repository(tmp_path)
    secret_value = "synthetic-nonproduction-value-123456"
    (tmp_path / ".env").write_text(f"API_KEY={secret_value}\n", encoding="utf-8")

    checks = evaluate_repository(scan_repository(tmp_path))
    secret_check = checks[-1]

    assert secret_check.status is CheckStatus.FAIL
    assert secret_check.paths == (".env:1 (credential assignment)",)
    assert secret_value not in secret_check.summary
    assert secret_value not in repr(secret_check)


def test_scans_extensionless_files_and_common_credential_names(tmp_path):
    make_healthy_repository(tmp_path)
    (tmp_path / "Dockerfile").write_text(
        "GITHUB_TOKEN=synthetic-nonproduction-value-123456\n", encoding="utf-8"
    )

    secret_check = evaluate_repository(scan_repository(tmp_path))[-1]

    assert secret_check.status is CheckStatus.FAIL
    assert secret_check.paths == ("Dockerfile:1 (credential assignment)",)


def test_backup_names_do_not_satisfy_readme_or_license(tmp_path):
    (tmp_path / "README-backup.txt").write_text("backup", encoding="utf-8")
    (tmp_path / "LICENSE-old").write_text("backup", encoding="utf-8")

    checks = evaluate_repository(scan_repository(tmp_path))

    assert checks[0].status is CheckStatus.FAIL
    assert checks[1].status is CheckStatus.FAIL


def test_placeholder_credentials_are_not_risks(tmp_path):
    make_healthy_repository(tmp_path)
    (tmp_path / ".env.example").write_text(
        "API_KEY=your_api_key_here\n", encoding="utf-8"
    )

    checks = evaluate_repository(scan_repository(tmp_path))

    assert checks[-1].status is CheckStatus.PASS
