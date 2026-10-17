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


def test_scanner_truncates_files_to_max_lines(monkeypatch, tmp_path):
    (tmp_path / "long.txt").write_text("\n".join("line" for _ in range(5)))
    monkeypatch.setattr("repodoctor.scanner.MAX_LINES", 3)

    snapshot = scan_repository(tmp_path)

    assert len(snapshot.contents[0].lines) == 3


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
