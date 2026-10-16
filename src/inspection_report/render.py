"""Render validated inspection reports as Markdown or PDF.

Markdown has no dependencies. PDF needs the ``pdf`` extra (fpdf2, pure Python).
Several photos are combined into one document by passing a list of reports.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .schema import InspectionReport

SEVERITY_LABEL = {"none": "None", "low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}


def _cell(text: str) -> str:
    return " ".join(text.replace("|", "/").split()) or "-"


def to_markdown(reports: list[InspectionReport], title: str = "Equipment inspection report") -> str:
    lines = [f"# {title}", "", f"Date: {date.today().isoformat()}", ""]
    if reports:
        worst = max((r.worst_severity for r in reports), key=lambda s: list(type(s)).index(s))
        lines += [f"Photos: {len(reports)} | Highest severity: **{SEVERITY_LABEL[worst.value]}**", ""]
    for r in reports:
        lines += [
            f"## {r.image or 'photo'}",
            "",
            "| Component | Condition | Severity | Recommended action | Notes |",
            "|---|---|---|---|---|",
        ]
        for f in r.findings:
            lines.append(
                f"| {_cell(f.component)} | {f.condition.value} | {SEVERITY_LABEL[f.severity.value]} "
                f"| {_cell(f.recommended_action)} | {_cell(f.notes)} |"
            )
        lines.append("")
    return "\n".join(lines)


def _latin1(text: str) -> str:
    # Core PDF fonts are Latin-1 only; replace anything else rather than crash.
    return text.encode("latin-1", "replace").decode("latin-1")


def to_pdf(
    reports: list[InspectionReport], path: Path, title: str = "Equipment inspection report"
) -> Path:
    try:
        from fpdf import FPDF
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError("PDF output needs the pdf extra: pip install -e '.[pdf]'") from exc

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _latin1(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Date: {date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT")
    for r in reports:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, _latin1(r.image or "photo"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        with pdf.table(col_widths=(25, 17, 15, 43)) as table:
            header = table.row()
            for h in ("Component", "Condition", "Severity", "Action / notes"):
                header.cell(h)
            for f in r.findings:
                row = table.row()
                row.cell(_latin1(f.component))
                row.cell(f.condition.value)
                row.cell(SEVERITY_LABEL[f.severity.value])
                extra = f" ({f.notes})" if f.notes else ""
                row.cell(_latin1(f.recommended_action + extra))
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
    return path
