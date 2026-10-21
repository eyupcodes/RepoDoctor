import json
from pathlib import Path

from repodoctor.models import CheckResult, CheckStatus, RunResult
from repodoctor.sarif import result_to_sarif


def _result(*checks: CheckResult) -> RunResult:
    return RunResult(target=Path("/repo"), checks=checks, score=50)


def test_sarif_log_has_schema_version_and_one_rule_per_check():
    log = result_to_sarif(
        _result(
            CheckResult("readme", CheckStatus.PASS, "Found README file."),
            CheckResult("license", CheckStatus.FAIL, "Missing license file."),
        )
    )

    assert log["version"] == "2.1.0"
    assert "sarif-schema-2.1.0" in log["$schema"]
    driver = log["runs"][0]["tool"]["driver"]
    assert driver["name"] == "repodoctor"
    assert [rule["id"] for rule in driver["rules"]] == ["readme", "license"]


def test_only_warnings_and_failures_become_results():
    log = result_to_sarif(
        _result(
            CheckResult("readme", CheckStatus.PASS, "Found README file."),
            CheckResult("license", CheckStatus.FAIL, "Missing license file."),
            CheckResult("secret-risk", CheckStatus.WARNING, "Some files skipped."),
        )
    )

    results = log["runs"][0]["results"]
    assert [(r["ruleId"], r["level"]) for r in results] == [
        ("license", "error"),
        ("secret-risk", "warning"),
    ]
    assert "locations" not in results[0]


def test_secret_findings_become_physical_locations_without_values():
    log = result_to_sarif(
        _result(
            CheckResult(
                "secret-risk",
                CheckStatus.FAIL,
                "Found 2 potential secret risk(s).",
                paths=(
                    "config.txt:3 (credential assignment)",
                    "src/a:b.py:12 (private key)",
                ),
            )
        )
    )

    results = log["runs"][0]["results"]
    assert len(results) == 2
    first = results[0]["locations"][0]["physicalLocation"]
    assert first["artifactLocation"]["uri"] == "config.txt"
    assert first["region"]["startLine"] == 3
    assert "credential assignment" in results[0]["message"]["text"]
    second = results[1]["locations"][0]["physicalLocation"]
    assert second["artifactLocation"]["uri"] == "src/a:b.py"
    assert second["region"]["startLine"] == 12


def test_diagnostic_paths_without_a_line_stay_in_the_message():
    log = result_to_sarif(
        _result(
            CheckResult(
                "secret-risk",
                CheckStatus.WARNING,
                "Some files could not be inspected.",
                paths=("big.bin: file too large",),
            )
        )
    )

    (result,) = log["runs"][0]["results"]
    assert "locations" not in result
    assert "big.bin: file too large" in result["message"]["text"]


def test_sarif_log_is_json_serializable():
    json.dumps(result_to_sarif(_result()))
