# RepoDoctor

Deterministic repository health, structure, and security hygiene analyzer CLI.

[![CI](https://github.com/eyupcodes/RepoDoctor/actions/workflows/ci.yml/badge.svg)](https://github.com/eyupcodes/RepoDoctor/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

---

## 1. What does RepoDoctor do?

RepoDoctor inspects local Git repositories and codebases from your terminal to verify essential structural files, test suites, continuous integration configurations, and secret hygiene before publishing or deploying code.

It scores repositories on a deterministic scale (0 to 100) and produces structured terminal reports with actionable failure locations.

## 2. Why does it exist?

Small projects, MVPs, and rapid prototypes frequently miss foundational quality safeguards—such as licenses, `.gitignore` entries, test directories, or CI pipelines—and accidentally leak environment files, API keys, or private SSH/TLS keys.

RepoDoctor automates these baseline audits into a single zero-network, read-only terminal command.

## 3. 30-Second Quickstart

### Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
```

### Run Check

```bash
# Check current directory
repodoctor check .

# Check specific repository path
repodoctor check path/to/repo

# Display version
repodoctor --version
```

## 4. Example Output

### Healthy Repository (Score: 100/100, Exit code: 0)

```text
Repository: examples/healthy-repository
Score: 100/100
PASS  readme — Found README file.
PASS  license — Found license file.
PASS  gitignore — Found .gitignore file.
PASS  tests — Found test directory.
PASS  ci — Found CI workflow.
PASS  secret-risk — No secret risks found.
Summary: 6 passed, 0 warnings, 0 failed
```

### Risky Repository (Score: 0/100, Exit code: 1)

```text
Repository: examples/risky-repository
Score: 0/100
PASS  readme — Found README file.
FAIL  license — Missing license file.
FAIL  gitignore — Missing .gitignore file.
FAIL  tests — Missing test directory.
FAIL  ci — Missing CI workflow.
FAIL  secret-risk — Found 1 potential secret risk(s).
       config.txt:1 (credential assignment)
Summary: 1 passed, 0 warnings, 5 failed
```

Add `--json` to print the result as a single JSON object (score, summary counts and every check) for scripts and CI. Exit codes do not change, and like the terminal report it only contains `<path>:<line> (<risk class>)`, never the matched value:

```bash
repodoctor check . --json
```

```json
{"target": "/path/to/repo", "score": 85, "summary": {"passed": 5, "warnings": 0, "failed": 1}, "checks": [{"id": "readme", "status": "PASS", "summary": "Found README file.", "paths": []}]}
```

Add `--sarif` to print a [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html) log instead, for example to upload to GitHub code scanning. Each check is a rule; warnings and failures become results, and `secret-risk` findings carry the file and line (never the matched value). It cannot be combined with `--json` (exit code 2); other exit codes do not change:

```bash
repodoctor check . --sarif > repodoctor.sarif
```

Run the built-in examples directly:

```bash
repodoctor check examples/healthy-repository
repodoctor check examples/risky-repository
```

---

## Checks & Scoring

| Check ID | Description | Pass Condition | Failure Penalty |
|----------|-------------|----------------|-----------------|
| `readme` | Project documentation | Exact root file: `README`, `README.md`, `README.txt`, `README.rst` | -15 |
| `license` | Open source / project license | Exact root file: `LICENSE`, `LICENCE`, `LICENSE.md`, `LICENSE.txt` | -15 |
| `gitignore` | VCS ignore patterns | Root `.gitignore` exists | -15 |
| `tests` | Automated test suite | Root directory `tests/`, `test/`, or `__tests__/` exists | -15 |
| `ci` | Continuous integration | Active workflow in `.github/workflows/*.yml` or `*.yaml` | -15 |
| `secret-risk` | Secret & credential hygiene | Zero matched private keys, secret-named assignments with a literal value (references such as `${{ secrets.X }}`, `os.environ[...]` or `os.getenv(...)` are ignored), or well-known token formats (GitHub, AWS, Slack, Stripe, Google, LLM API keys); uninspected files trigger warnings (-5) | -40 |

**Score calculation:** `max(0, 100 - sum(penalties))`.

### Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| `0` | All checks passed (healthy repository, score: 100) |
| `1` | One or more warnings or check failures detected |
| `2` | Configuration error, missing target, or target is not a directory |

---

## Safety & Hardening Architecture

RepoDoctor is strictly **read-only** and bounded against common static analysis attack vectors and resource exhaustion:

- **No Value Leakage:** Matched credentials or private keys are never stored, logged, or printed. Output only notes `<path>:<line> (<risk class>)`.
- **ANSI & Control Character Sanitization:** File paths and summary lines sanitize terminal escape sequences (`\x1b`) and C0 control codes to prevent terminal injection attacks.
- **Symlink Protection:** Directory and file symlinks are never traversed, preventing infinite recursion loops and out-of-boundary file reads.
- **Resource Bounds:**
  - Max file size: 1 MiB per file (oversized files flagged as diagnostics)
  - Max text lines: 10,000 lines inspected per file
  - Max cumulative bytes: 8 MiB per scan to prevent RAM exhaustion
  - Max files: 10,000 files indexed
- **Binary File Skipping:** Files containing NUL bytes (`\x00`) are safely skipped without Unicode decode exceptions.
- **Excluded Directories:** Standard dependency and cache folders (`.git`, `node_modules`, `.venv`, `dist`, `__pycache__`, etc.) are skipped by default.

---

## Development & Testing

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Lint and format checks
ruff check .
ruff format --check .

# Run test suite with branch coverage enforcement (>= 80%)
pytest --cov=repodoctor --cov-branch --cov-fail-under=80
```

---

## License

RepoDoctor is released under the [MIT License](LICENSE).
