# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Files exceeding the per-file line scan limit now produce an incomplete-scan warning instead of silently reporting a clean secret check; findings in inspected lines are still reported.
- SARIF finding locations percent-encode file paths so spaces, reserved URI characters and Unicode filenames link to the correct file.
- `repodoctor check` prints invalid-target errors to stderr instead of stdout, so `--json` output stays machine-readable; exit code 2 is unchanged (#15).
- `secret-risk` no longer flags secret references as credential assignments: GitHub Actions `${{ ... }}` expressions, calls and subscripts like `os.getenv(...)` / `os.environ[...]`, `None`/`null`/boolean literals and bare type annotations. Quoted and literal values are still reported (#13).

### Added

- The `ci` check also passes for a root `.gitlab-ci.yml`, `.circleci/config.yml`, `azure-pipelines.yml`, `Jenkinsfile`, `.travis.yml` or `bitbucket-pipelines.yml`, not only GitHub Actions workflows (#22).
- `secret-risk` skips a line that contains `repodoctor: ignore`, so reviewed findings such as fake credentials in test fixtures can be suppressed one line at a time (#20).
- `repodoctor check --sarif` prints a SARIF 2.1.0 log (one rule per check, file and line for `secret-risk` findings, no matched values); it cannot be combined with `--json` (#17).
- `repodoctor check --json` prints the score, summary counts and every check as one JSON object; exit codes are unchanged (#11).
- `secret-risk` flags well-known token formats (GitHub, AWS, Slack, Stripe, Google, `sk-` LLM keys) anywhere on a line, reported as `(known token format)`; obvious placeholders like `ghp_xxxx…` are ignored (#9).
- MIT license, declared in package metadata (#7).

### Changed

- Added regression tests ensuring file and byte scan limits stop further directory traversal and file reads.
- Added tests for scanner failure handling (unreadable files and directories, byte limit, non-UTF-8 and binary files) and the `python -m repodoctor` entry point; removed a redundant diagnostic branch (#5).

## [0.1.0] - 2026-09-09

### Added

- Initial release of `repodoctor` CLI.
- Core repository scanner with bounded traversal:
  - 1 MiB maximum file size limit with diagnostic reporting.
  - 10,000 lines limit per text file.
  - 10,000 maximum total files indexed.
  - 8 MiB maximum cumulative byte scan limit.
  - Binary file detection via NUL byte (`\x00`).
  - Directory and file symlink protection.
  - Control character and ANSI escape sequence sanitization.
- Six core health and hygiene checks:
  - `readme`: Root README presence check.
  - `license`: Root license presence check.
  - `gitignore`: VCS `.gitignore` check.
  - `tests`: Test directory check (`tests/`, `test/`, `__tests__/`).
  - `ci`: GitHub Actions workflow detection (`.github/workflows/*.yml|*.yaml`).
  - `secret-risk`: Secret, credential, and private key hygiene check with matched value redaction.
- Deterministic health score algorithm (0 to 100).
- Rich terminal report with status indicators and actionable finding paths.
- Command-line interface with `--version` and `check` commands.
- Exit codes: `0` (clean), `1` (findings/warnings), `2` (invalid config/target).
- Test suite with 42 unit and integration tests achieving >91% branch coverage.
- Built-in healthy and risky repository test fixtures and reference outputs.
