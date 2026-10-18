# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `secret-risk` flags well-known token formats (GitHub, AWS, Slack, Stripe, Google, `sk-` LLM keys) anywhere on a line, reported as `(known token format)`; obvious placeholders like `ghp_xxxx…` are ignored (#9).
- MIT license, declared in package metadata (#7).

### Changed

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
