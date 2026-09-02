from repodoctor.models import CheckResult, CheckStatus
from repodoctor.scoring import calculate_health_score


def check(identifier, status):
    return CheckResult(id=identifier, status=status, summary=identifier)


def test_score_is_100_for_passes():
    assert calculate_health_score((check("readme", CheckStatus.PASS),)) == 100


def test_score_applies_fixed_penalties():
    checks = (
        check("readme", CheckStatus.FAIL),
        check("ci", CheckStatus.FAIL),
        check("secret-risk", CheckStatus.FAIL),
        check("scan", CheckStatus.WARNING),
    )

    assert calculate_health_score(checks) == 25


def test_score_never_drops_below_zero():
    checks = tuple(check(f"check-{index}", CheckStatus.FAIL) for index in range(10))

    assert calculate_health_score(checks) == 0
