"""Human-readable rendering of normalized show data (CLI / debugging).

Ported from the shared Ticket Fox engine: ``engine/sources/cli.py`` imports
:func:`format_shows` and :func:`format_theatre_list` from here, but this module
was missing from the web backend, so ``python -m app.engine.sources.test_bms``
(and ``test_district``) died with an ImportError.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .models import Show, Theatre


def _pretty_time(show_time: str) -> str:
    """Normalize '2026-09-16T15:45' (District) or '01:30 PM' (BMS) for display."""
    try:
        dt = datetime.fromisoformat(show_time)
        return dt.strftime("%d %b, %I:%M %p")
    except ValueError:
        return show_time


def format_shows(movie_name: str, city_name: str, shows: list[Show], theatres: list[Theatre] | None = None) -> str:
    """Render shows grouped by theatre, matching the milestone sample output."""
    lines: list[str] = []
    if movie_name:
        lines.append(f"🎬 {movie_name}")
    if city_name:
        lines.append("")
        lines.append(f"🏙️ {city_name}")
    lines.append("")

    by_theatre: dict[str, list[Show]] = defaultdict(list)
    for s in shows:
        by_theatre[s.theatre_name].append(s)

    theatre_lookup = {t.theatre_id: t for t in (theatres or [])}

    if not by_theatre:
        lines.append("   (no shows found)")
        return "\n".join(lines)

    for name in sorted(by_theatre):
        grouped = by_theatre[name]
        lines.append(f"🏢 {name}")
        for s in sorted(grouped, key=lambda s: s.show_time):
            marker = "✅" if s.available else "🔴"
            fmt = f" [{s.screen_format}]" if s.screen_format else ""
            lines.append(f"   {marker} {_pretty_time(s.show_time)}{fmt}")
        lines.append("")

    # Note theatres that were selected but have no shows at all.
    selected_ids = {t.theatre_id for t in (theatres or [])}
    shown_ids = {s.theatre_id for s in shows}
    for tid in sorted(selected_ids - shown_ids):
        t = theatre_lookup.get(tid)
        if t:
            lines.append(f"🏢 {t.theatre_name}")
            lines.append("   (no shows yet)")
            lines.append("")

    return "\n".join(lines).rstrip()


def format_theatre_list(city_name: str, theatres: list[Theatre]) -> str:
    lines = [f"🏙️ {city_name}", ""]
    for i, t in enumerate(theatres, 1):
        address = f" — {t.address}" if t.address else ""
        lines.append(f"{i}. {t.theatre_name}  [{t.theatre_id}]{address}")
    return "\n".join(lines)
