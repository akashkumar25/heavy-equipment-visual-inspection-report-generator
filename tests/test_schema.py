import json

import pytest

from inspection_report import cli
from inspection_report.schema import (
    InspectionReport,
    InvalidOutputError,
    Severity,
    extract_json,
    inspect_image,
    parse_report,
)

GOOD = {
    "findings": [
        {
            "component": "hydraulic hose",
            "condition": "leaking",
            "severity": "high",
            "recommended_action": "replace hose",
        },
        {"component": "tyre", "condition": "worn", "severity": "low", "recommended_action": "monitor"},
    ]
}


class Scripted:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts = []

    def describe(self, image_path, prompt):
        self.prompts.append(prompt)
        return self.replies.pop(0)


def test_extract_json_handles_fences_and_prose():
    assert extract_json("Sure!\n```json\n{\"a\": 1}\n```\nDone") == {"a": 1}
    assert extract_json('Here: {"a": {"b": 2}} thanks') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_parse_report_validates_enums():
    report = parse_report(json.dumps(GOOD), image="x.jpg")
    assert isinstance(report, InspectionReport)
    assert report.image == "x.jpg"
    assert report.worst_severity == Severity.high
    bad = {"findings": [{**GOOD["findings"][0], "severity": "catastrophic"}]}
    with pytest.raises(ValueError):
        parse_report(json.dumps(bad))
    with pytest.raises(ValueError):
        parse_report('{"findings": []}')


def test_retry_feeds_error_back_and_succeeds(tmp_path):
    backend = Scripted("I think the tyre is fine.", "```json\n" + json.dumps(GOOD) + "\n```")
    report = inspect_image(backend, tmp_path / "p.jpg")
    assert len(report.findings) == 2
    assert len(backend.prompts) == 2
    assert "previous reply was invalid" in backend.prompts[1]
    assert "previous reply" not in backend.prompts[0]


def test_gives_up_after_max_attempts(tmp_path):
    backend = Scripted("nope", "still nope")
    with pytest.raises(InvalidOutputError):
        inspect_image(backend, tmp_path / "p.jpg", max_attempts=2)


def test_cli_inspect_prints_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "get_backend", lambda s: Scripted(json.dumps(GOOD)))
    assert cli.main(["inspect", str(tmp_path / "tyre.jpg")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["image"] == "tyre.jpg" and len(out["findings"]) == 2


def test_cli_inspect_reports_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "get_backend", lambda s: Scripted("x", "x", "x"))
    assert cli.main(["inspect", str(tmp_path / "t.jpg")]) == 1
    assert "no valid report" in capsys.readouterr().err
