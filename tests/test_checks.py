import pytest

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


def _ci_status(root):
    return next(c for c in evaluate_repository(scan_repository(root)) if c.id == "ci")


@pytest.mark.parametrize("ci_file", ["ci.yml", "ci.yaml"])
def test_ci_check_accepts_direct_github_workflows(tmp_path, ci_file):
    path = tmp_path / ".github" / "workflows" / ci_file
    path.parent.mkdir(parents=True)
    path.write_text("name: CI\n", encoding="utf-8")

    assert _ci_status(tmp_path).status is CheckStatus.PASS


@pytest.mark.parametrize("ci_file", ["archive/ci.yml", "archive/nested/ci.yaml"])
def test_ci_check_ignores_nested_github_workflows(tmp_path, ci_file):
    path = tmp_path / ".github" / "workflows" / ci_file
    path.parent.mkdir(parents=True)
    path.write_text("name: Archived CI\n", encoding="utf-8")

    assert _ci_status(tmp_path).status is CheckStatus.FAIL


@pytest.mark.parametrize(
    "ci_file",
    [
        ".gitlab-ci.yml",
        ".circleci/config.yml",
        "azure-pipelines.yml",
        "Jenkinsfile",
        ".travis.yml",
        "bitbucket-pipelines.yml",
    ],
)
def test_ci_check_accepts_other_ci_services(tmp_path, ci_file):
    path = tmp_path / ci_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stages: []\n", encoding="utf-8")

    assert _ci_status(tmp_path).status is CheckStatus.PASS


@pytest.mark.parametrize("ci_file", ["docs/.gitlab-ci.yml", "sub/Jenkinsfile"])
def test_ci_check_ignores_ci_files_outside_the_root(tmp_path, ci_file):
    path = tmp_path / ci_file
    path.parent.mkdir(parents=True)
    path.write_text("stages: []\n", encoding="utf-8")

    assert _ci_status(tmp_path).status is CheckStatus.FAIL


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


def test_secret_risk_line_numbers_ignore_form_feeds_and_unicode_separators(tmp_path):
    make_healthy_repository(tmp_path)
    (tmp_path / "config.txt").write_bytes(
        "# header\x0c\u2028\nAPI_KEY=synthetic-nonproduction-value-123456\n".encode()
    )

    checks = evaluate_repository(scan_repository(tmp_path))

    assert checks[-1].paths == ("config.txt:2 (credential assignment)",)


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


def _fake_tokens() -> dict[str, str]:
    """Token-shaped test values, assembled at runtime so no literal is committed."""
    body = "aB3dE5gH7jK9mN1pQ3sT5vW7yZ9bD1fG3hJ5"
    return {
        "github": "gh" + "p_" + body,
        "github_fine_grained": "github" + "_pat_" + (body * 2)[:60],
        "aws": "AK" + "IA" + "Q3W5E7R9T1Y3U5I7",
        "slack": "xo" + "xb-" + "1234567890-abcdefghij",
        "stripe": "sk" + "_live_" + body[:24],
        "google": "AI" + "za" + body[:35],
        "llm": "s" + "k-" + body,
    }


@pytest.mark.parametrize("kind", sorted(_fake_tokens()))
def test_known_token_formats_are_flagged_without_value(tmp_path, kind):
    make_healthy_repository(tmp_path)
    token = _fake_tokens()[kind]
    (tmp_path / "client.py").write_text(
        f'headers = {{"Authorization": "Bearer {token}"}}\n', encoding="utf-8"
    )

    secret_check = evaluate_repository(scan_repository(tmp_path))[-1]

    assert secret_check.status is CheckStatus.FAIL
    assert secret_check.paths == ("client.py:1 (known token format)",)
    assert token not in repr(secret_check)


def test_token_on_an_assignment_line_is_reported_once(tmp_path):
    make_healthy_repository(tmp_path)
    token = _fake_tokens()["github"]
    (tmp_path / ".env").write_text(f"GITHUB_TOKEN={token}\n", encoding="utf-8")

    secret_check = evaluate_repository(scan_repository(tmp_path))[-1]

    assert secret_check.paths == (".env:1 (known token format)",)


def test_ordinary_text_is_not_mistaken_for_a_token(tmp_path):
    make_healthy_repository(tmp_path)
    (tmp_path / "notes.md").write_text(
        "Use a sk-learn style pipeline.\n"
        "The task-force-review-meeting-notes-for-march-2024-are-linked.\n"
        "commit 0123456789abcdef0123456789abcdef01234567\n",
        encoding="utf-8",
    )

    assert evaluate_repository(scan_repository(tmp_path))[-1].status is CheckStatus.PASS


def test_placeholder_tokens_are_not_risks(tmp_path):
    make_healthy_repository(tmp_path)
    (tmp_path / "docs.md").write_text(
        "Example: gh" + "p_" + "x" * 36 + "\nSample id AK" + "IA" + "0" * 16 + "\n",
        encoding="utf-8",
    )

    assert evaluate_repository(scan_repository(tmp_path))[-1].status is CheckStatus.PASS


def test_real_token_after_a_placeholder_on_the_same_line_is_still_flagged(tmp_path):
    make_healthy_repository(tmp_path)
    placeholder = "gh" + "p_" + "x" * 36
    (tmp_path / "docs.md").write_text(
        f"{placeholder} {_fake_tokens()['github']}\n", encoding="utf-8"
    )

    secret_check = evaluate_repository(scan_repository(tmp_path))[-1]

    assert secret_check.paths == ("docs.md:1 (known token format)",)


def _secret_paths(tmp_path, name: str, line: str) -> tuple[str, ...]:
    make_healthy_repository(tmp_path)
    (tmp_path / name).write_text(line + "\n", encoding="utf-8")
    return evaluate_repository(scan_repository(tmp_path))[-1].paths


@pytest.mark.parametrize(
    "line",
    [
        "DB_PASSWORD=hunter2",
        'password = "abc123xyz"',
        'password = "get_password()"',
        "client_secret: s3cr3tvalue",
        '{"api_key": "abcd1234efgh"}',
        '  "password": "hunter2hunter2",',
        "'client_secret': 'abcd1234',",
    ],
)
def test_hardcoded_credentials_are_still_risks(tmp_path, line):
    assert _secret_paths(tmp_path, "settings.txt", line) == (
        "settings.txt:1 (credential assignment)",
    )


@pytest.mark.parametrize(
    "line",
    [
        "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}",
        'api_key = os.environ["API_KEY"]',
        'password = os.getenv("PW")',
        "token = get_token()",
        "token: str = None",
        "password=None",
        '  "token": null,',
        '{"api_key": "${API_KEY}"}',
        '  "password": os.getenv("PW"),',
        '  "max_tokens": 100,',
    ],
)
def test_secret_references_are_not_risks(tmp_path, line):
    assert _secret_paths(tmp_path, "settings.txt", line) == ()


@pytest.mark.parametrize(
    "line",
    [
        'password = "abc123xyz"  # repodoctor: ignore',
        "DB_PASSWORD=hunter2 # repodoctor: ignore",
        "-----BEGIN RSA PRIVATE KEY----- # repodoctor: ignore",
    ],
)
def test_marked_lines_are_not_risks(tmp_path, line):
    assert _secret_paths(tmp_path, "settings.txt", line) == ()


def test_marker_only_covers_its_own_line(tmp_path):
    content = 'password = "abc123xyz"  # repodoctor: ignore\nDB_PASSWORD=hunter2\n'

    assert _secret_paths(tmp_path, "settings.txt", content) == (
        "settings.txt:2 (credential assignment)",
    )
