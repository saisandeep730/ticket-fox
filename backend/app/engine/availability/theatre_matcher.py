"""Intelligent cross-platform theatre and cinema matcher.

Disambiguates multiplex chains (PVR, INOX, Cinépolis, Miraj, etc.) by matching
specific mall names, road names, and sub-localities to avoid false alerts across
different branches of the same chain in the same city.
"""

from __future__ import annotations

import re

from ..models import Theatre

# Major multi-unit cinema chains
CHAINS = {
    "pvr",
    "inox",
    "cinepolis",
    "miraj",
    "moviemax",
    "mukta",
    "asian",
    "carnival",
    "wave",
    "rajhans",
    "ny cinemas",
    "movie time",
    "cinemarc",
}

# Generic words that do not identify a specific branch/mall
GENERIC_WORDS = {
    "cinema",
    "cinemas",
    "multiplex",
    "theatre",
    "theater",
    "talkies",
    "picture",
    "hall",
    "screens",
    "screen",
    "imax",
    "4dx",
    "dolby",
    "atmos",
    "gold",
    "luxe",
    "p[xl]",
    "pxl",
    "ice",
    "laser",
    "mall",
    "road",
    "rd",
    "near",
    "opp",
    "beside",
    "street",
    "st",
    "city",
    # City names commonly appended to venue titles
    "hyderabad",
    "mumbai",
    "bengaluru",
    "bangalore",
    "delhi",
    "ncr",
    "chennai",
    "kolkata",
    "pune",
    "kochi",
    "ahmedabad",
    "chandigarh",
}


def _tokenize(text: str) -> list[str]:
    """Extract clean lowercase alphabetic and numeric tokens."""
    clean = re.sub(r"[^\w\s]", " ", (text or "").lower())
    return [token for token in clean.split() if len(token) > 1]


def extract_chain_and_locality(name: str) -> tuple[str | None, set[str]]:
    """Extract cinema chain brand and distinct locality/mall tokens from a theatre name."""
    tokens = _tokenize(name)
    matched_chain: str | None = None

    # Check multi-word chains first (e.g. 'ny cinemas', 'movie time')
    lower_name = name.lower()
    for chain in sorted(CHAINS, key=len, reverse=True):
        if chain in lower_name:
            matched_chain = chain
            break

    locality_tokens = set()
    chain_tokens = set(matched_chain.split()) if matched_chain else set()

    for token in tokens:
        if token in chain_tokens:
            continue
        if token in GENERIC_WORDS:
            continue
        locality_tokens.add(token)

    return matched_chain, locality_tokens


def match_theatre_names(name1: str, name2: str) -> float:
    """Calculate match confidence score between 0.0 and 1.0.

    Strict rules:
    - If both belong to the same chain (e.g. INOX), they MUST have matching
      distinct locality/mall tokens (e.g. 'gvk' or 'gsm'). If localities conflict, score = 0.0.
    - If chains conflict (e.g. PVR vs INOX), score = 0.0.
    - If standalone cinemas, calculate token overlap.
    """
    chain1, loc1 = extract_chain_and_locality(name1)
    chain2, loc2 = extract_chain_and_locality(name2)

    # If both have recognized chains
    if chain1 and chain2:
        if chain1 != chain2:
            return 0.0
        # Both are the same chain (e.g. both INOX)
        # Must have at least one distinguishing mall/locality token matching!
        overlap = loc1.intersection(loc2)
        if not overlap:
            # Different branches (e.g. INOX GVK One vs INOX GSM Mall)
            return 0.0

        # Score based on overlap ratio
        overlap_score = len(overlap) / max(1, min(len(loc1), len(loc2)))
        return round(0.5 + 0.5 * overlap_score, 2)

    # One has chain, one doesn't (e.g. "GVK One Mall" vs "INOX GVK One")
    if (chain1 and not chain2) or (chain2 and not chain1):
        overlap = loc1.intersection(loc2)
        if len(overlap) >= 2 or (len(overlap) == 1 and any(len(t) >= 4 for t in overlap)):
            return 0.75
        return 0.0

    # Neither has a recognized chain: standalone theatres (e.g. "Prasads Multiplex", "AMB Cinemas")
    tokens1 = set(_tokenize(name1)) - GENERIC_WORDS
    tokens2 = set(_tokenize(name2)) - GENERIC_WORDS
    if not tokens1 or not tokens2:
        return 0.0

    overlap = tokens1.intersection(tokens2)
    if not overlap:
        return 0.0

    # Jaccard + subset similarity
    jaccard = len(overlap) / len(tokens1.union(tokens2))
    subset_ratio = len(overlap) / min(len(tokens1), len(tokens2))
    return round(0.4 * jaccard + 0.6 * subset_ratio, 2)


def find_matching_theatres(
    source_theatres: list[dict[str, str]],
    candidate_theatres: list[Theatre],
    min_confidence: float = 0.75,
) -> list[Theatre]:
    """Find candidate theatres that match the user's selected source theatres.

    Returns deduplicated list of matched candidate Theatre objects.
    """
    if not source_theatres or not candidate_theatres:
        return []

    matched: list[Theatre] = []
    seen_ids: set[str] = set()

    for src in source_theatres:
        src_name = src.get("name", "")
        best_candidate: Theatre | None = None
        best_score = 0.0

        for cand in candidate_theatres:
            cand_name = cand.theatre_name
            score = match_theatre_names(src_name, cand_name)
            if score >= min_confidence and score > best_score:
                best_score = score
                best_candidate = cand

        if best_candidate and best_candidate.theatre_id not in seen_ids:
            seen_ids.add(best_candidate.theatre_id)
            matched.append(best_candidate)

    return matched
