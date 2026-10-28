from pathlib import Path

import pytest

from repodoctor.scanner import scan_repository


def test_scanner_skips_ignored_directories_and_symlinks(tmp_path):
    ignored = tmp_path / ".git"
    ignored.mkdir()
    (ignored / "config").write_text("TOKEN=synthetic-value", encoding="utf-8")
    target = tmp_path / "target.txt"
    target.write_text("PASSWORD=synthetic-value", encoding="utf-8")
    link = tmp_path / "linked.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pass

    snapshot = scan_repository(tmp_path)

    assert ".git/config" not in snapshot.files
    assert "linked.txt" not in snapshot.files


def test_scanner_reports_when_file_limit_is_reached(monkeypatch, tmp_path):
    for index in range(3):
        (tmp_path / f"file-{index}.txt").write_text("safe", encoding="utf-8")
    monkeypatch.setattr("repodoctor.scanner.MAX_FILES", 2)

    snapshot = scan_repository(tmp_path)

    assert snapshot.diagnostics == ("file scan limit reached",)
    assert len(snapshot.files) == 2


def test_scanner_marks_large_files_as_incomplete(tmp_path):
    (tmp_path / "large.txt").write_bytes(b"x" * (1024 * 1024 + 1))

    snapshot = scan_repository(tmp_path)

    assert snapshot.contents == ()
    assert snapshot.diagnostics == ("large.txt (file too large)",)


def test_scanner_skips_binary_files(tmp_path):
    (tmp_path / "binary.txt").write_bytes(b"TOKEN=value\x00")

    snapshot = scan_repository(tmp_path)

    assert snapshot.contents == ()
    assert snapshot.diagnostics == ()


def test_scanner_stops_after_total_byte_limit(monkeypatch, tmp_path):
    (tmp_path / "a.txt").write_text("12345", encoding="utf-8")
    (tmp_path / "b.txt").write_text("67890", encoding="utf-8")
    monkeypatch.setattr("repodoctor.scanner.MAX_TOTAL_BYTES", 5)

    snapshot = scan_repository(tmp_path)

    assert snapshot.diagnostics == ("total byte scan limit reached",)
    assert len(snapshot.contents) == 1


def test_scanner_reports_total_byte_limit(monkeypatch, tmp_path):
    for name in ("a.txt", "b.txt", "c.txt"):
        (tmp_path / name).write_text("x" * 10, encoding="utf-8")
    monkeypatch.setattr("repodoctor.scanner.MAX_TOTAL_BYTES", 25)

    snapshot = scan_repository(tmp_path)

    assert snapshot.diagnostics == ("total byte scan limit reached",)
    assert [item.path for item in snapshot.contents] == ["a.txt", "b.txt"]


def test_scanner_reports_non_utf8_files_as_unscanned(tmp_path):
    (tmp_path / "latin1.txt").write_bytes("caf\xe9".encode("latin-1"))

    snapshot = scan_repository(tmp_path)

    assert snapshot.contents == ()
    assert snapshot.diagnostics == ("latin1.txt",)


def test_scanner_skips_binary_files_without_diagnostic(tmp_path):
    (tmp_path / "image.bin").write_bytes(b"\x00\x01\x02")

    snapshot = scan_repository(tmp_path)

    assert snapshot.files == ("image.bin",)
    assert snapshot.contents == ()
    assert snapshot.diagnostics == ()


@pytest.mark.parametrize("line_count", [0, 2, 3, 4])
@pytest.mark.parametrize("trailing_newline", [False, True])
def test_scanner_reports_only_files_exceeding_max_lines(
    monkeypatch, tmp_path, line_count, trailing_newline
):
    text = "\n".join("line" for _ in range(line_count))
    if text and trailing_newline:
        text += "\n"
    (tmp_path / "long.txt").write_text(text, encoding="utf-8")
    monkeypatch.setattr("repodoctor.scanner.MAX_LINES", 3)

    snapshot = scan_repository(tmp_path)

    assert snapshot.contents[0].lines == ("line",) * min(line_count, 3)
    assert snapshot.diagnostics == (
        ("long.txt (line scan limit reached)",) if line_count > 3 else ()
    )


def test_scanner_reports_unreadable_file(monkeypatch, tmp_path):
    (tmp_path / "secret.txt").write_text("data", encoding="utf-8")

    def deny(self):
        raise PermissionError("denied")

    monkeypatch.setattr("pathlib.Path.read_bytes", deny)

    snapshot = scan_repository(tmp_path)

    assert snapshot.files == ("secret.txt",)
    assert snapshot.contents == ()
    assert snapshot.diagnostics == ("secret.txt",)


def test_scanner_reports_file_that_cannot_be_stat(monkeypatch, tmp_path):
    (tmp_path / "broken.txt").write_text("data", encoding="utf-8")

    def fail(self, *args, **kwargs):
        raise OSError("stat failed")

    monkeypatch.setattr("pathlib.Path.stat", fail)

    snapshot = scan_repository(tmp_path)

    assert snapshot.files == ("broken.txt",)
    assert snapshot.diagnostics == ("broken.txt",)


def fake_walk(errors, tree):
    """Build an ``os.walk`` stand-in that reports ``errors`` then yields ``tree``."""

    def walk(top, followlinks=False, onerror=None):
        for error in errors:
            onerror(error)
        yield from tree

    return walk


@pytest.mark.parametrize(
    ("limit", "value", "diagnostic", "expected_files"),
    [
        ("MAX_FILES", 1, "file scan limit reached", ("first/a.txt",)),
        (
            "MAX_TOTAL_BYTES",
            4,
            "total byte scan limit reached",
            ("first/a.txt", "first/b.txt"),
        ),
    ],
)
def test_scanner_stops_before_next_directory_after_limit(
    monkeypatch, tmp_path, limit, value, diagnostic, expected_files
):
    first = tmp_path / "first"
    later = tmp_path / "later"
    first.mkdir()
    (later / "nested").mkdir(parents=True)
    for path in (first / "a.txt", first / "b.txt", later / "unread.txt"):
        path.write_text("safe", encoding="utf-8")
    later_directories = ["nested"]
    monkeypatch.setattr(
        "os.walk",
        fake_walk(
            [],
            [
                (tmp_path, ["first", "later"], []),
                (first, [], ["a.txt", "b.txt"]),
                (later, later_directories, ["unread.txt"]),
            ],
        ),
    )
    monkeypatch.setattr(f"repodoctor.scanner.{limit}", value)
    read_paths = []
    read_bytes = Path.read_bytes

    def track_read(path):
        read_paths.append(path.relative_to(tmp_path).as_posix())
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", track_read)

    snapshot = scan_repository(tmp_path)

    assert snapshot.files == expected_files
    assert snapshot.directories == ("first", "later")
    assert [item.path for item in snapshot.contents] == ["first/a.txt"]
    assert read_paths == ["first/a.txt"]
    assert snapshot.diagnostics == (diagnostic,)
    assert later_directories == []


def test_scanner_reports_unreadable_directory_relative_to_target(monkeypatch, tmp_path):
    error = PermissionError(13, "denied", str(tmp_path / "locked"))
    monkeypatch.setattr("os.walk", fake_walk([error], []))

    snapshot = scan_repository(tmp_path)

    assert snapshot.diagnostics == ("locked (directory access error)",)


def test_scanner_reports_directory_error_outside_target(monkeypatch, tmp_path):
    error = PermissionError(13, "denied", "/elsewhere/locked")
    monkeypatch.setattr("os.walk", fake_walk([error], []))

    snapshot = scan_repository(tmp_path)

    assert snapshot.diagnostics == ("/elsewhere/locked (directory access error)",)


def test_scanner_reports_directory_error_without_filename(monkeypatch, tmp_path):
    monkeypatch.setattr("os.walk", fake_walk([OSError("boom")], []))

    snapshot = scan_repository(tmp_path)

    assert snapshot.diagnostics == ("directory access error",)


def test_scanner_sanitizes_control_characters_in_paths(tmp_path):
    try:
        (tmp_path / "bad\x1bname.txt").write_text("safe", encoding="utf-8")
    except OSError:
        return

    snapshot = scan_repository(tmp_path)

    assert snapshot.files == ("bad\\x1bname.txt",)


def test_scanner_splits_lines_like_an_editor(tmp_path):
    (tmp_path / "mixed.txt").write_bytes("a\x0cb\u2028c\x85d\r\ne\rf\ng\n".encode())

    snapshot = scan_repository(tmp_path)

    assert snapshot.contents[0].lines == ("a\x0cb\u2028c\x85d", "e", "f", "g")
