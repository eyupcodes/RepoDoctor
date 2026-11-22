import re

from repodoctor.models import CheckResult, CheckStatus, RepositorySnapshot

_README_NAMES = frozenset({"README", "README.MD", "README.TXT", "README.RST"})
_LICENSE_BASES = ("LICENSE", "LICENCE", "COPYING", "UNLICENSE")
_LICENSE_NAMES = frozenset(
    f"{base}{ext}" for base in _LICENSE_BASES for ext in ("", ".MD", ".TXT")
) | frozenset(
    f"{base}{ext}"
    for base in ("LICENSE-MIT", "LICENSE-APACHE")
    for ext in ("", ".MD", ".TXT")
)


# Root-level configuration files of CI services other than GitHub Actions.
_CI_FILES = frozenset(
    {
        ".gitlab-ci.yml",
        ".circleci/config.yml",
        "azure-pipelines.yml",
        "Jenkinsfile",
        ".travis.yml",
        "bitbucket-pipelines.yml",
    }
)


def _has_ci(snapshot: RepositorySnapshot) -> bool:
    return any(
        path in _CI_FILES
        or (
            path.rpartition("/")[0] == ".github/workflows"
            and path.lower().endswith((".yml", ".yaml"))
        )
        for path in snapshot.files
    )


_ROOT_TEST_DIRECTORIES = frozenset({"tests", "test", "__tests__", "spec", "specs"})
# Names accepted at any depth; plain ``test`` is too often a fixture folder.
_NESTED_TEST_DIRECTORIES = frozenset({"tests", "__tests__"})


def _has_tests(snapshot: RepositorySnapshot) -> bool:
    return any(
        path in _ROOT_TEST_DIRECTORIES
        or path.rpartition("/")[2] in _NESTED_TEST_DIRECTORIES
        for path in snapshot.directories
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
        _has_tests,
    ),
    (
        "ci",
        "CI workflow",
        _has_ci,
    ),
)
# Match assignments like KEY=VALUE, KEY: VALUE, optionally prefixed with `export`,
# where KEY contains a high-signal secret indicator (``API_KEY`` and ``apiKey``
# alike). Broadened from the original narrow list to cover GITHUB_TOKEN,
# AWS_SECRET_ACCESS_KEY, CLIENT_SECRET, SECRET_KEY (Django/Flask), etc.
# The key may be quoted, as in JSON or a Python dict literal (``"api_key": "..."``),
# including a single-line object that opens with ``{`` or a YAML list item
# (``- KEY=v``). A declaration may start with modifiers (``const``, ``final``,
# ``private static``...), a ``String`` type or a PHP ``$``, and the key may carry a
# type annotation (``password: str = "..."``).
CREDENTIAL_PATTERN = re.compile(
    r"^\s*(?:-\s+)?(?:\{\s*|(?:(?:export|const|let|var|val|final|static|private|public|protected|readonly)\s+)*(?:(?:String|string|str)\s+)?)"
    r"\$?[\"']?[A-Z0-9_.-]*?(?:API_?KEY|SECRET_?KEY(?:_BASE)?|SECRET|TOKEN|PASSWORD|PASSWD|ACCESS_?KEY|PRIVATE_?KEY|DATABASE_URL)\b[\"']?"
    r"(?:\s*:\s*[A-Za-z_][\w.]*(?:\[[\w., ]*\])?(?=\s*=))?"
    r"\s*[:=]\s*(?:[fFrRbBuU]{0,2}[\"'])?([^\"'\s#;]+)",
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
    r"|\bhf_[A-Za-z0-9]{34,}\b"
    r"|\bnpm_[A-Za-z0-9]{36}\b"
    r"|\bglpat-[A-Za-z0-9_-]{20,}"
    r"|\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{50,}"
    r"|\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}\b"
    r"|\bgsk_[A-Za-z0-9]{40,}\b"
    r"|\bdo[por]_v1_[a-f0-9]{64}\b"
    r"|\bshp(?:at|ca|pa)_[a-f0-9]{32}\b"
    r"|\bdckr_pat_[A-Za-z0-9_-]{20,}"
)
# ``scheme://[user]:password@host`` with a literal password. The password may not
# contain ``/``, ``@`` or whitespace; ``user@host`` and ``host:port`` never match.
URL_PASSWORD_PATTERN = re.compile(
    r"\b[a-z][a-z0-9+.-]*://[^\s:/@]*:([^\s:/@]+)@", re.IGNORECASE
)
# Passwords in URLs that are templates (``${PW}``, ``$PW``, ``{pw}``, ``<pw>``,
# ``%s``, ``%(pw)s``) or the usual dummy words used in documentation.
URL_PASSWORD_PLACEHOLDER = re.compile(
    r"^(?:[$<{%].*|(?:password|passwd|pass|pwd|secret|changeme|example|x+|\*+)"
    r"|your[_-].*)$",
    re.IGNORECASE,
)
# A line carrying this marker (usually in a comment) was reviewed and is skipped.
IGNORE_MARKER = "repodoctor: ignore"
# Template expressions (``${{ secrets.X }}``, ``{{ vault_x }}``) and command
# substitutions (``$(cat file)``, backticks) compute the value instead of containing it.
PLACEHOLDERS = re.compile(
    r"^(?:example|changeme|placeholder|your[_-].*|<.*>|\$\{?\w+\}?"
    r"|\$?\{\{.*|\$\(.*|`.*"
    r"|\{\w*\}|%s|%\(\w+\)s|\*{3,}|x{3,})$",
    re.IGNORECASE,
)


# Unquoted right-hand sides that reference a secret instead of containing one:
# GitHub Actions expressions, calls and subscripts (``os.getenv(``, ``os.environ[``),
# ``process.env.X``, PHP/shell variables (``$_ENV[...]``), ``await``/``new`` and
# similar computed values, null/boolean literals and bare type annotations
# (``token: str = None``). Dotted attribute chains such as ``self.token`` or
# ``args.password`` count as references after ``=`` only (see ``_is_reference``);
# in YAML ``key: a.b.c`` can be a real value.
REFERENCE_VALUE = re.compile(
    r"\$\{\{|(?:process|import\.meta)\.env\.|(?:await|new|function|lambda)\b|\$[A-Za-z_]|[A-Za-z_][\w.]*\s*[(\[]|(?:none|null|nil|true|false|str|int|bool|bytes)\b",
    re.IGNORECASE,
)


ATTRIBUTE_CHAIN = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+(?![\w.])")


def _is_reference(line: str, credential: re.Match[str]) -> bool:
    """True when the assigned value is a code/config reference rather than a literal."""
    start = credential.start(1)
    if start > 0 and line[start - 1] in "\"'":
        return False
    if REFERENCE_VALUE.match(line, start) is not None:
        return True
    return "=" in line[:start] and ATTRIBUTE_CHAIN.match(line, start) is not None


def _is_placeholder_token(token: str) -> bool:
    """Treat tokens with almost no character variety (``ghp_xxxx...``) as examples."""
    return len(set(token)) < 10


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
    findings: set[tuple[str, int, str]] = set()
    for content in snapshot.contents:
        for line_number, line in enumerate(content.lines, start=1):
            if IGNORE_MARKER in line:
                continue
            private_key = PRIVATE_KEY_PATTERN.search(line)
            known_token = next(
                (
                    m
                    for m in KNOWN_TOKEN_PATTERN.finditer(line)
                    if not _is_placeholder_token(m.group())
                ),
                None,
            )
            credential = CREDENTIAL_PATTERN.search(line)
            url_password = next(
                (
                    m
                    for m in URL_PASSWORD_PATTERN.finditer(line)
                    if not URL_PASSWORD_PLACEHOLDER.match(m.group(1))
                ),
                None,
            )
            if private_key:
                findings.add((content.path, line_number, "private key"))
            elif known_token:
                findings.add((content.path, line_number, "known token format"))
            elif (
                credential
                and not PLACEHOLDERS.match(credential.group(1))
                and not _is_reference(line, credential)
            ):
                findings.add((content.path, line_number, "credential assignment"))
            elif url_password:
                findings.add((content.path, line_number, "url credential"))

    if findings:
        return CheckResult(
            id="secret-risk",
            status=CheckStatus.FAIL,
            summary=f"Found {len(findings)} potential secret risk(s).",
            paths=tuple(
                f"{path}:{line_number} ({kind})"
                for path, line_number, kind in sorted(findings)
            ),
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
