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
