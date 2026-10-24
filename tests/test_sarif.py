import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

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
    assert second["artifactLocation"]["uri"] == "src/a%3Ab.py"
    assert second["region"]["startLine"] == 12


@pytest.mark.parametrize(
    ("path", "expected_uri"),
    [
        ("src/my config.py", "src/my%20config.py"),
        ("src/key#backup.env", "src/key%23backup.env"),
        ("src/100%.env", "src/100%25.env"),
        ("src/what?.env", "src/what%3F.env"),
        ("src/şifre.env", "src/%C5%9Fifre.env"),
        ("src/already%20encoded.env", "src/already%2520encoded.env"),
        ("config:backup.env", "config%3Abackup.env"),
    ],
)
def test_finding_paths_are_encoded_as_relative_uris(path, expected_uri):
    log = result_to_sarif(
        _result(
            CheckResult(
                "secret-risk",
                CheckStatus.FAIL,
                "Found 1 potential secret risk(s).",
                paths=(f"{path}:7 (credential assignment)",),
            )
        )
    )

    (result,) = log["runs"][0]["results"]
    location = result["locations"][0]["physicalLocation"]
    uri = location["artifactLocation"]["uri"]
    assert uri == expected_uri
    parsed = urlsplit(uri)
    assert (parsed.scheme, parsed.netloc, parsed.query, parsed.fragment) == ("",) * 4
    assert unquote(parsed.path) == path
    assert location["region"]["startLine"] == 7


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
