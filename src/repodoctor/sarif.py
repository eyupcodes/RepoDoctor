import re
from urllib.parse import quote

from repodoctor import __version__
from repodoctor.models import CheckStatus, RunResult

SARIF_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/"
    "sarif-2.1/schema/sarif-schema-2.1.0.json"
)
_LEVELS = {CheckStatus.WARNING: "warning", CheckStatus.FAIL: "error"}
_FINDING = re.compile(r"^(?P<path>.+):(?P<line>\d+) \((?P<kind>[^()]+)\)$")


def result_to_sarif(result: RunResult) -> dict[str, object]:
    """Return a SARIF 2.1.0 log for a run, without any matched secret values.

    Every check is a rule; only warnings and failures produce results. Paths shaped
    like ``<path>:<line> (<risk class>)`` become one located result each.
    """
    results: list[dict[str, object]] = []
    for check in result.checks:
        level = _LEVELS.get(check.status)
        if level is None:
            continue
        matches = [m for m in map(_FINDING.match, check.paths) if m]
        if check.paths and len(matches) == len(check.paths):
            for match in matches:
                results.append(
                    {
                        "ruleId": check.id,
                        "level": level,
                        "message": {"text": f"{check.summary} ({match['kind']})"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {
                                        "uri": quote(match["path"], safe="/")
                                    },
                                    "region": {"startLine": int(match["line"])},
                                }
                            }
                        ],
                    }
                )
            continue
        text = " ".join([check.summary, *check.paths])
        results.append({"ruleId": check.id, "level": level, "message": {"text": text}})

    return {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "repodoctor",
                        "version": __version__,
                        "rules": [
                            {"id": check.id, "shortDescription": {"text": check.id}}
                            for check in result.checks
                        ],
                    }
                },
                "results": results,
            }
        ],
    }
