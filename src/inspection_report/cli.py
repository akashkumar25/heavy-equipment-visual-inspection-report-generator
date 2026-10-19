"""Command line entry point."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .backends import BackendError, get_backend
from .config import Settings
from .schema import InvalidOutputError, inspect_image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def list_images(settings: Settings) -> list[str]:
    if not settings.images_dir.is_dir():
        return []
    return sorted(
        p.name for p in settings.images_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inspection-report", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="show configuration and discovered images")
    describe = sub.add_parser("describe", help="ask the configured VLM to describe one photo")
    describe.add_argument("image", type=Path)
    describe.add_argument(
        "--prompt",
        default="Describe the condition of the equipment components visible in this photo.",
    )
    inspect = sub.add_parser("inspect", help="produce a validated JSON inspection report for a photo")
    inspect.add_argument("image", type=Path)
    inspect.add_argument("--attempts", type=int, default=3)
    report = sub.add_parser("report", help="inspect photos and write JSON, Markdown and PDF")
    report.add_argument("images", type=Path, nargs="+")
    report.add_argument("--out", type=Path, default=Path("reports"))
    ev = sub.add_parser("eval", help="score the backend on a labelled image set")
    ev.add_argument("manifest", type=Path)
    ev.add_argument("--attempts", type=int, default=3)
    sub.add_parser("ui", help="launch the Gradio UI (needs the ui extra)")
    args = parser.parse_args(argv)

    if args.command == "status":
        s = Settings()
        model = s.local_model if s.backend == "local" else f"{s.api_model} @ {s.api_base_url}"
        print(f"Backend: {s.backend}, model: {model}")
        images = list_images(s)
        print(f"Images in {s.images_dir}: {len(images)}")
        for name in images:
            print(f"  - {name}")
        return 0
    if args.command == "describe":
        try:
            print(get_backend(Settings()).describe(args.image, args.prompt))
        except (BackendError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.command == "inspect":
        try:
            report = inspect_image(get_backend(Settings()), args.image, args.attempts)
        except (BackendError, InvalidOutputError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(report.model_dump_json(indent=2))
        return 0
    if args.command == "report":
        from .ui import build_reports

        try:
            backend = get_backend(Settings())
        except (BackendError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        reports, errors, files = build_reports(backend, args.images, args.out)
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        for kind, path in files.items():
            print(f"{kind}: {path}")
        return 0 if reports and not errors else 1
    if args.command == "eval":
        from .evaluate import evaluate

        settings = Settings()
        try:
            result = evaluate(get_backend(settings), args.manifest, args.attempts)
        except (BackendError, OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        label = settings.local_model if settings.backend == "local" else settings.api_model
        print(result.to_markdown(label))
        return 0
    if args.command == "ui":
        from .ui import launch

        launch()
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
