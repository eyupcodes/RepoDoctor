import runpy

import pytest

from tests.helpers import make_healthy_repository


def test_python_dash_m_runs_cli(monkeypatch, tmp_path, capsys):
    make_healthy_repository(tmp_path)
    monkeypatch.setattr("sys.argv", ["repodoctor", "check", str(tmp_path)])

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("repodoctor", run_name="__main__")

    assert excinfo.value.code == 0
    assert "Score: 100/100" in capsys.readouterr().out
