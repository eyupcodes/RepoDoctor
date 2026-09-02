# RepoDoctor

RepoDoctor is a Python CLI for checking repository health, structure, and security hygiene. It helps catch missing project essentials and risky files before publication.

> Current status: M1 foundation. Repository checks and health scoring arrive in M2.

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

Current output:

```text
Foundation ready: /path/to/repository
```

Invalid or non-directory targets return a clear error and non-zero exit code.

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

## Planned MVP Checks

- `README`, `LICENSE`, and `.gitignore`
- Test directory detection
- CI workflow detection
- Environment and secret-risk pattern scan
- Health score and terminal report

See [`PROJECT.md`](PROJECT.md) for scope and milestones.

## License

License selection requires project-owner approval. No license has been applied yet.
