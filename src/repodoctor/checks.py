import re

from repodoctor.models import CheckResult, CheckStatus, RepositorySnapshot

_README_NAMES = frozenset({"README", "README.MD", "README.TXT", "README.RST"})
_LICENSE_NAMES = frozenset(
    {
        "LICENSE",
        "LICENCE",
        "LICENSE.MD",
        "LICENCE.MD",
        "LICENSE.TXT",
        "LICENCE.TXT",
    }
)


def _is_readme(path: str) -> bool:
    if "/" in path:
        return False
    return path.upper() in _README_NAMES


def _is_license(path: str) -> bool:
    if "/" in path:
        return False
    return path.upper() in _LICENSE_NAMES


STRUCTURAL_CHECKS = (
    (
        "readme",
        "README file",
        lambda snapshot: any(_is_readme(p) for p in snapshot.files),
    ),
    (
        "license",
        "license file",
        lambda snapshot: any(_is_license(p) for p in snapshot.files),
    ),
    ("gitignore", ".gitignore file", lambda snapshot: ".gitignore" in snapshot.files),
    (
        "tests",
        "test directory",
        lambda snapshot: any(
            path in {"tests", "test", "__tests__"} for path in snapshot.directories
        ),
    ),
    (
        "ci",
        "CI workflow",
        lambda snapshot: any(
            path.startswith(".github/workflows/")
            and path.lower().endswith((".yml", ".yaml"))
            for path in snapshot.files
        ),
    ),
)
# Match assignments like KEY=VALUE, KEY: VALUE, optionally prefixed with `export`,
# where KEY contains a high-signal secret indicator. Broadened from the original
# narrow list to cover GITHUB_TOKEN, AWS_SECRET_ACCESS_KEY, CLIENT_SECRET, etc.
CREDENTIAL_PATTERN = re.compile(
    r"^\s*(?:export\s+)?[A-Z0-9_.-]*?(?:API_KEY|SECRET|TOKEN|PASSWORD|ACCESS_KEY|PRIVATE_KEY|DATABASE_URL)\b\s*[:=]\s*[\"']?([^\"'\s#;]+)",
    re.IGNORECASE,
)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")
# Provider token formats distinctive enough to flag wherever they appear on a line.
KNOWN_TOKEN_PATTERN = re.compile(
    r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"
    r"|\bgithub_pat_[A-Za-z0-9_]{50,}\b"
    r"|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"
    r"|\bxox[abprs]-[A-Za-z0-9-]{10,}"
    r"|\b[sr]k_live_[A-Za-z0-9]{16,}\b"
    r"|\bAIza[0-9A-Za-z_-]{35}\b"
    r"|\bsk-(?:ant-)?[A-Za-z0-9_-]{32,}"
)
PLACEHOLDERS = re.compile(
    r"^(?:example|changeme|placeholder|your[_-].*|<.*>|\$\{?\w+\}?)$", re.IGNORECASE
)


def _structural_results(snapshot: RepositorySnapshot) -> tuple[CheckResult, ...]:
    results = []
    for identifier, label, predicate in STRUCTURAL_CHECKS:
        is_present = predicate(snapshot)
        results.append(
            CheckResult(
                id=identifier,
                status=CheckStatus.PASS if is_present else CheckStatus.FAIL,
                summary=f"Found {label}." if is_present else f"Missing {label}.",
            )
        )
    return tuple(results)


def _secret_result(snapshot: RepositorySnapshot) -> CheckResult:
    findings: list[str] = []
    for content in snapshot.contents:
        for line_number, line in enumerate(content.lines, start=1):
            private_key = PRIVATE_KEY_PATTERN.search(line)
            known_token = KNOWN_TOKEN_PATTERN.search(line)
            credential = CREDENTIAL_PATTERN.search(line)
            if private_key:
                findings.append(f"{content.path}:{line_number} (private key)")
            elif known_token:
                findings.append(f"{content.path}:{line_number} (known token format)")
            elif credential and not PLACEHOLDERS.match(credential.group(1)):
                findings.append(f"{content.path}:{line_number} (credential assignment)")

    if findings:
        return CheckResult(
            id="secret-risk",
            status=CheckStatus.FAIL,
            summary=f"Found {len(findings)} potential secret risk(s).",
            paths=tuple(sorted(set(findings))),
        )
    if snapshot.diagnostics:
        return CheckResult(
            id="secret-risk",
            status=CheckStatus.WARNING,
            summary="Some files could not be inspected.",
            paths=snapshot.diagnostics,
        )
    return CheckResult(
        id="secret-risk", status=CheckStatus.PASS, summary="No secret risks found."
    )


def evaluate_repository(snapshot: RepositorySnapshot) -> tuple[CheckResult, ...]:
    return (*_structural_results(snapshot), _secret_result(snapshot))
