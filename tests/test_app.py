from repodoctor.app import run
from repodoctor.config import RepoDoctorConfig


def test_run_returns_foundation_result_for_target(tmp_path):
    config = RepoDoctorConfig.from_target(tmp_path)

    result = run(config)

    assert result.target == tmp_path.resolve()
    assert result.passed_checks == ()
    assert result.warnings == ()
    assert result.failures == ()
