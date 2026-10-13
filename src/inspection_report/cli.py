"""Command line entry point."""

import argparse
import sys

from . import __version__
from .config import Settings

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
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
