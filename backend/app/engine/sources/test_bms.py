"""Source-testing CLI for BookMyShow.

Usage:
    python -m app.sources.test_bms <URL> [--city Hyderabad] [--theatre PVR]*
"""

from __future__ import annotations

import argparse

from ..models import Source
from .cli import add_common_arguments, configure_logging, run_source_test


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="test-bms", description="Test the BookMyShow adapter")
    add_common_arguments(parser)
    args = parser.parse_args()
    return run_source_test(Source.BOOKMYSHOW, args.url, args.city, args.theatre, args.list_theatres)


if __name__ == "__main__":
    raise SystemExit(main())