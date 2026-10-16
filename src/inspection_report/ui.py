"""Gradio UI: upload photos, get the JSON, Markdown and PDF report.

``build_reports`` holds the logic so it can be tested without Gradio; ``launch``
imports Gradio lazily (install the ``ui`` extra).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .backends import Backend, BackendError, get_backend
from .config import Settings
from .render import to_markdown, to_pdf
from .schema import InspectionReport, InvalidOutputError, inspect_image


def build_reports(
    backend: Backend, images: list[Path], out_dir: Path
) -> tuple[list[InspectionReport], list[str], dict[str, Path]]:
    """Inspect each image. Returns (reports, per-image errors, written files)."""
    reports: list[InspectionReport] = []
    errors: list[str] = []
    for img in images:
        try:
            reports.append(inspect_image(backend, img))
        except (BackendError, InvalidOutputError, OSError) as exc:
            errors.append(f"{img.name}: {exc}")
    files: dict[str, Path] = {}
    if reports:
        out_dir.mkdir(parents=True, exist_ok=True)
        files["json"] = out_dir / "report.json"
        files["json"].write_text(
            json.dumps([r.model_dump(mode="json") for r in reports], indent=2), encoding="utf-8"
        )
        files["md"] = out_dir / "report.md"
        files["md"].write_text(to_markdown(reports), encoding="utf-8")
        try:
            files["pdf"] = to_pdf(reports, out_dir / "report.pdf")
        except RuntimeError as exc:
            errors.append(str(exc))
    return reports, errors, files


def launch(settings: Settings | None = None, share: bool = False) -> None:
    try:
        import gradio as gr
    except ImportError as exc:
        raise SystemExit("The UI needs the ui extra: pip install -e '.[ui,pdf]'") from exc

    backend = get_backend(settings or Settings())

    def run(paths: list[str] | None):
        if not paths:
            return "Upload at least one photo.", None, None, None
        out = Path(tempfile.mkdtemp(prefix="inspection_"))
        reports, errors, files = build_reports(backend, [Path(p) for p in paths], out)
        md = to_markdown(reports) if reports else ""
        if errors:
            md += "\n\n**Problems:**\n" + "\n".join(f"- {e}" for e in errors)
        return md, *(str(files[k]) if k in files else None for k in ("json", "md", "pdf"))

    demo = gr.Interface(
        fn=run,
        inputs=gr.File(file_count="multiple", file_types=["image"], label="Equipment photos"),
        outputs=[
            gr.Markdown(label="Report"),
            gr.File(label="JSON"),
            gr.File(label="Markdown"),
            gr.File(label="PDF"),
        ],
        title="Heavy equipment inspection report",
    )
    demo.launch(share=share)
