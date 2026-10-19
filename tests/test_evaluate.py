import json

from inspection_report import cli
from inspection_report.evaluate import EvalResult, evaluate

REPLY = {
    "findings": [
        {"component": "hydraulic hose", "condition": "leaking", "severity": "high",
         "recommended_action": "replace"},
        {"component": "tyre", "condition": "good", "severity": "none", "recommended_action": "none"},
    ]
}


class Fake:
    def __init__(self, replies):
        self.replies = replies

    def describe(self, image_path, prompt):
        return self.replies[image_path.name]


def _manifest(tmp_path):
    items = [
        {"image": "a.jpg", "findings": [
            {"component": "hose", "condition": "leaking", "severity": "critical"},
            {"component": "tyre", "condition": "worn", "severity": "low"},
            {"component": "bucket", "condition": "cracked", "severity": "high"}]},
        {"image": "b.jpg", "findings": [
            {"component": "track", "condition": "worn", "severity": "medium"}]},
    ]
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"images": items}))
    return path


def test_scoring(tmp_path):
    backend = Fake({"a.jpg": json.dumps(REPLY), "b.jpg": "not json"})
    r = evaluate(backend, _manifest(tmp_path), max_attempts=1)
    assert (r.images, r.valid, r.expected, r.matched) == (2, 1, 4, 2)
    assert r.condition_correct == 1  # hose leaking ok, tyre good != worn
    assert r.severity_exact == 0 and r.severity_within_one == 2  # high~critical and none~low are one level apart
    rates = r.rates()
    assert rates["valid output"] == 0.5 and rates["component recall"] == 0.5


def test_empty_rates_and_markdown():
    r = EvalResult()
    assert all(v is None for v in r.rates().values())
    assert "n/a" in r.to_markdown("m")


def test_cli_eval(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "get_backend", lambda s: Fake({"a.jpg": json.dumps(REPLY), "b.jpg": "x"}))
    assert cli.main(["eval", str(_manifest(tmp_path))]) == 0
    assert "component recall" in capsys.readouterr().out
    assert cli.main(["eval", str(tmp_path / "missing.json")]) == 1
