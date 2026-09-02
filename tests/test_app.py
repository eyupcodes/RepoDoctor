from repodoctor.app import run
from repodoctor.config import RepoDoctorConfig
from tests.helpers import make_healthy_repository


def test_run_returns_healthy_result(tmp_path):
    make_healthy_repository(tmp_path)

    result = run(RepoDoctorConfig.from_target(tmp_path))

    assert result.target == tmp_path.resolve()
    assert result.score == 100
    assert len(result.passed_checks) == 6
    assert result.warnings == ()
    assert result.failures == ()


def test_run_returns_failures_for_empty_repository(tmp_path):
    result = run(RepoDoctorConfig.from_target(tmp_path))

    assert result.score == 25
    assert len(result.failures) == 5
