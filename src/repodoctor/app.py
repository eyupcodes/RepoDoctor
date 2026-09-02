from repodoctor.checks import evaluate_repository
from repodoctor.config import RepoDoctorConfig
from repodoctor.models import RunResult
from repodoctor.scanner import scan_repository
from repodoctor.scoring import calculate_health_score


def run(config: RepoDoctorConfig) -> RunResult:
    """Scan a repository and return deterministic health results."""
    snapshot = scan_repository(config.target)
    checks = evaluate_repository(snapshot)
    return RunResult(
        target=config.target,
        checks=checks,
        score=calculate_health_score(checks),
    )
