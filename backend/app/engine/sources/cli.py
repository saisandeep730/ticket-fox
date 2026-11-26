"""Shared CLI helpers for the source-testing commands."""

from __future__ import annotations

import argparse
import logging
import sys

from ..format import format_shows, format_theatre_list
from ..http import BlockedError, FetchError
from ..models import Source, Theatre
from .bookmyshow import BookMyShowAdapter
from .district import DistrictAdapter
from ..urls import parse_movie_url


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


def theatre_ids_from_names(names: list[str], theatres: list[Theatre]) -> list[Theatre]:
    """Resolve user-provided theatre name substrings to Theatre objects."""
    if not names:
        return []
    wanted: list[Theatre] = []
    for t in theatres:
        if any(n.lower() in t.theatre_name.lower() for n in names):
            wanted.append(t)
    return wanted


def run_source_test(
    source: Source,
    url: str,
    city: str | None,
    theatres: list[str],
    list_theatres_only: bool,
) -> int:
    parsed = parse_movie_url(url)
    adapter: BookMyShowAdapter | DistrictAdapter

    if source == Source.BOOKMYSHOW:
        adapter = BookMyShowAdapter()
        region_slug = city or parsed.region_slug
        region = adapter.resolve_region(region_slug)
        region_name = region.name or region_slug
    else:
        adapter = DistrictAdapter()  # type: ignore[assignment]
        city_slug = city or parsed.city_slug
        region = adapter.resolve_region(city_slug or "hyderabad")
        region_name = region.name

    print(f"source={source.value} movie_id={parsed.movie_id} region={region.code}\n")

    try:
        if source == Source.BOOKMYSHOW:
            theatre_list = adapter.list_theatres(region)  # type: ignore[union-attr]
        else:
            theatre_list = adapter.list_theatres_for_movie(parsed.movie_id, parsed.movie_slug, region)  # type: ignore[attr-defined]

        selected = theatre_ids_from_names(theatres, theatre_list) if theatres else theatre_list

        if list_theatres_only:
            print(format_theatre_list(region_name, theatre_list))
            return 0

        if source == Source.BOOKMYSHOW:
            shows = adapter.fetch_shows(parsed.movie_id, region, selected or None)  # type: ignore[union-attr]
        else:
            shows = adapter.fetch_shows(parsed.movie_id, region, selected or None, parsed.movie_slug)  # type: ignore[attr-defined]

        print(format_shows(parsed_show_name(parsed, shows), region_name, shows, selected))
        return 0

    except (BlockedError, FetchError, RuntimeError, LookupError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


def parsed_show_name(parsed, shows) -> str:
    for s in shows:
        if s.movie_name:
            return s.movie_name
    return ""


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("url", help="Movie URL from BookMyShow or District")
    parser.add_argument("--city", help="City/region name (e.g. Hyderabad)")
    parser.add_argument("--theatre", action="append", default=[], help="Theatre name substring (repeatable)")
    parser.add_argument("--list-theatres", action="store_true", help="Only list theatres, do not fetch shows")