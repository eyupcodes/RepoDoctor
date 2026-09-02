import os
from pathlib import Path

from repodoctor.models import FileContent, RepositorySnapshot

MAX_FILE_SIZE = 1024 * 1024
MAX_LINES = 10_000
MAX_FILES = 10_000
MAX_TOTAL_BYTES = 8 * 1024 * 1024
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
    }
)


def _sanitize_relative_path(path: str) -> str:
    escaped: list[str] = []
    for char in path:
        code = ord(char)
        if char == "\x1b":
            escaped.append("\\x1b")
        elif 0 <= code < 32 or code == 127:
            escaped.append(f"\\x{code:02x}")
        else:
            escaped.append(char)
    return "".join(escaped)


def _read_candidate(
    path: Path, relative_path: str
) -> tuple[FileContent | None, str | None]:
    try:
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            return None, f"{_sanitize_relative_path(relative_path)} (file too large)"
        data = path.read_bytes()
        if b"\x00" in data:
            return None, None
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return None, _sanitize_relative_path(relative_path)
        lines = tuple(text.splitlines()[:MAX_LINES])
        return FileContent(
            path=_sanitize_relative_path(relative_path), lines=lines
        ), None
    except OSError:
        return None, _sanitize_relative_path(relative_path)


def scan_repository(target: Path) -> RepositorySnapshot:
    files: list[str] = []
    directories: list[str] = []
    contents: list[FileContent] = []
    diagnostics: list[str] = []
    total_bytes = 0
    total_limit_reached = False

    def on_error(error: OSError) -> None:
        filename = getattr(error, "filename", None)
        if filename:
            try:
                rel = Path(filename).relative_to(target).as_posix()
            except ValueError:
                rel = Path(filename).as_posix()
            diagnostics.append(
                f"{_sanitize_relative_path(rel)} (directory access error)"
            )
        else:
            diagnostics.append("directory access error")

    for root, directory_names, file_names in os.walk(
        target, followlinks=False, onerror=on_error
    ):
        if total_limit_reached:
            directory_names.clear()
            break
        root_path = Path(root)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in EXCLUDED_DIRECTORIES and not (root_path / name).is_symlink()
        )
        for name in directory_names:
            directories.append(
                _sanitize_relative_path(
                    (root_path / name).relative_to(target).as_posix()
                )
            )
        for name in sorted(file_names):
            if total_limit_reached:
                break
            if len(files) >= MAX_FILES:
                if "file scan limit reached" not in diagnostics:
                    diagnostics.append("file scan limit reached")
                total_limit_reached = True
                directory_names.clear()
                break
            path = root_path / name
            if path.is_symlink():
                continue
            relative_path = path.relative_to(target).as_posix()
            sanitized_relative = _sanitize_relative_path(relative_path)
            files.append(sanitized_relative)

            try:
                file_size = path.stat().st_size
            except OSError:
                diagnostics.append(sanitized_relative)
                continue

            # Oversized files get their own diagnostic and do not count toward total.
            if file_size > MAX_FILE_SIZE:
                content, diagnostic = _read_candidate(path, relative_path)
                if diagnostic is not None:
                    diagnostics.append(diagnostic)
                continue

            if total_bytes + file_size > MAX_TOTAL_BYTES:
                if "total byte scan limit reached" not in diagnostics:
                    diagnostics.append("total byte scan limit reached")
                total_limit_reached = True
                directory_names.clear()
                break

            content, diagnostic = _read_candidate(path, relative_path)
            if content is not None:
                total_bytes += file_size
                contents.append(content)
            elif diagnostic is not None:
                if diagnostic.endswith("(file too large)"):
                    diagnostics.append(diagnostic)
                elif diagnostic.endswith("(directory access error)"):
                    diagnostics.append(diagnostic)
                else:
                    diagnostics.append(diagnostic)
            else:
                total_bytes += file_size

    return RepositorySnapshot(
        target=target,
        files=tuple(sorted(files)),
        directories=tuple(sorted(directories)),
        contents=tuple(sorted(contents, key=lambda item: item.path)),
        diagnostics=tuple(sorted(set(diagnostics))),
    )
