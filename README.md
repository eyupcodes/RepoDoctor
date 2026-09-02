# RepoDoctor

RepoDoctor is a Python CLI for checking repository health, structure, and security hygiene. It helps catch missing project essentials and risky files before publication.

> Current status: M2 core scanner.

## Requirements

- Python 3.12+

## Quick Start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
repodoctor check .
```

Example healthy output:

```text
Repository: /path/to/repository
Score: 100/100
PASS  readme — Found README file.
PASS  license — Found license file.
PASS  gitignore — Found .gitignore file.
PASS  tests — Found test directory.
PASS  ci — Found CI workflow.
PASS  secret-risk — No secret risks found.
Summary: 6 passed, 0 warnings, 0 failed
```

Try both included examples:

```bash
repodoctor check examples/healthy-repository
repodoctor check examples/risky-repository
```

Exit code `0` means all checks passed, `1` means findings were reported, and `2` means the target was invalid.

## Development

```bash
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
pytest --cov=repodoctor --cov-branch --cov-fail-under=80
```

You can also run the CLI as a module:

```bash
python -m repodoctor --help
python -m repodoctor check .
```

## MVP Checks

- Root `README`, `LICENSE`, and `.gitignore`
- Test directory detection
- GitHub Actions workflow detection
- Environment and secret-risk pattern scan with value redaction
- Deterministic health score and terminal report

RepoDoctor skips symlinks, common dependency/cache/build directories, binary files, and files larger than 1 MiB. It never reports a matched credential value.

See [`PROJECT.md`](PROJECT.md) for scope and milestones.

## License

License selection requires project-owner approval. No license has been applied yet.
