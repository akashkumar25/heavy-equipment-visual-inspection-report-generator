import json

from inspection_report import cli
from inspection_report.render import to_markdown, to_pdf
from inspection_report.schema import InspectionReport
from inspection_report.ui import build_reports

DATA = {
    "image": "a.jpg",
    "findings": [
        {
            "component": "hose | left",
            "condition": "leaking",
            "severity": "high",
            "recommended_action": "replace\nhose",
            "notes": "weeping at fitting – near clamp",
        },
        {"component": "tyre", "condition": "worn", "severity": "low", "recommended_action": "monitor"},
    ],
}
REPLY = json.dumps({"findings": DATA["findings"]})


class Fake:
    def __init__(self, reply=REPLY):
        self.reply = reply

    def describe(self, image_path, prompt):
        return self.reply


def test_markdown_table_and_summary():
    md = to_markdown([InspectionReport.model_validate(DATA)])
    assert "## a.jpg" in md
    assert "Highest severity: **High**" in md
    assert "| hose / left | leaking | High | replace hose |" in md
    assert "| tyre | worn | Low | monitor | - |" in md


def test_pdf_written(tmp_path):
    path = to_pdf([InspectionReport.model_validate(DATA)], tmp_path / "r.pdf")
    assert path.read_bytes().startswith(b"%PDF")


def test_build_reports_collects_errors(tmp_path):
    img = tmp_path / "x.jpg"
    img.write_bytes(b"x")
    reports, errors, files = build_reports(Fake(), [img], tmp_path / "out")
    assert len(reports) == 1 and not errors
    assert set(files) == {"json", "md", "pdf"}
    assert json.loads(files["json"].read_text())[0]["image"] == "x.jpg"

    reports, errors, files = build_reports(Fake("not json"), [img], tmp_path / "out2")
    assert not reports and files == {} and "x.jpg" in errors[0]


def test_report_command(tmp_path, monkeypatch, capsys):
    img = tmp_path / "x.jpg"
    img.write_bytes(b"x")
    monkeypatch.setattr(cli, "get_backend", lambda settings: Fake())
    assert cli.main(["report", str(img), "--out", str(tmp_path / "o")]) == 0
    assert "pdf:" in capsys.readouterr().out
    monkeypatch.setattr(cli, "get_backend", lambda settings: Fake("bad"))
    assert cli.main(["report", str(img), "--out", str(tmp_path / "o2")]) == 1
