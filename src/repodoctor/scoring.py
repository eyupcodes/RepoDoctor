from repodoctor.models import CheckResult, CheckStatus

STRUCTURAL_FAILURE_PENALTY = 15
SECRET_FAILURE_PENALTY = 40
WARNING_PENALTY = 5


def calculate_health_score(checks: tuple[CheckResult, ...]) -> int:
    penalty = 0
    for check in checks:
        if check.status is CheckStatus.WARNING:
            penalty += WARNING_PENALTY
        elif check.status is CheckStatus.FAIL:
            penalty += (
                SECRET_FAILURE_PENALTY
                if check.id == "secret-risk"
                else STRUCTURAL_FAILURE_PENALTY
            )
    return max(0, 100 - penalty)
