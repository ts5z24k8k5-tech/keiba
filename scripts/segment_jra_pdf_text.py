#!/usr/bin/env python3
"""Strictly segment JRA PDF text into target race blocks.

This module does not download PDFs, parse runner rows, resolve horse IDs, or
write to SQLite. It only assigns a text block after date, venue, and race
number agree with a reviewed target manifest.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping, Sequence

_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
VENUES = {
    "札幌": "sapporo", "函館": "hakodate", "福島": "fukushima",
    "新潟": "niigata", "東京": "tokyo", "中山": "nakayama",
    "中京": "chukyo", "京都": "kyoto", "阪神": "hanshin",
    "小倉": "kokura",
}
_HEADER = re.compile(
    r"(?P<month>[0-9０-９]{1,2})月\s*(?P<day>[0-9０-９]{1,2})日"
    r".{0,160}?[（(]\s*(?P<year>20[0-9０-９]{2})年"
    r"(?P<meeting>[0-9０-９]{1,2})(?P<venue>札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)"
    r"\s*[）)]"
    r".{0,100}?第\s*(?P<meeting_day>[0-9０-９]{1,2})\s*日"
    r"\s*第\s*(?P<race_no>[0-9０-９]{1,2})\s*競走",
    re.DOTALL,
)


class SegmentationError(ValueError):
    """Raised when a PDF race header cannot be safely matched to the manifest."""


@dataclass(frozen=True)
class RaceBlock:
    race_id: str
    race_date: str
    venue: str
    race_no: int
    meeting_no: int
    meeting_day: int
    page_text: str


def _ascii_digits(value: str) -> str:
    return value.translate(_DIGITS)


def _header_data(match: re.Match[str]) -> dict[str, object]:
    g = {key: _ascii_digits(value) if key != "venue" else value
         for key, value in match.groupdict().items()}
    year, month, day = int(g["year"]), int(g["month"]), int(g["day"])
    import datetime as _dt
    try:
        date = _dt.date(year, month, day).isoformat()
    except ValueError as exc:
        raise SegmentationError("invalid calendar date in race heading") from exc
    return {
        "race_date": date,
        "venue": VENUES[str(g["venue"])],
        "race_no": int(g["race_no"]),
        "meeting_no": int(g["meeting"]),
        "meeting_day": int(g["meeting_day"]),
    }


def segment_expected_races(
    page_texts: Sequence[str],
    expected_rows: Iterable[Mapping[str, object]],
) -> list[RaceBlock]:
    """Return only exact date/venue/race-number matches for expected race IDs.

    Race IDs must be 12 digits and their final two digits must equal race_no.
    A missing, duplicate, or mismatched header is a hard error; no nearest-match
    or race-number-only fallback is permitted.
    """
    expected = list(expected_rows)
    if not expected:
        raise SegmentationError("expected race manifest is empty")

    text = "\n".join(page_texts)
    matches = list(_HEADER.finditer(text))
    parsed = [(_header_data(m), m) for m in matches]

    by_identity: dict[tuple[str, str, int], tuple[dict[str, object], re.Match[str]]] = {}
    for data, match in parsed:
        key = (str(data["race_date"]), str(data["venue"]), int(data["race_no"]))
        if key in by_identity:
            raise SegmentationError(f"duplicate race heading: {key}")
        by_identity[key] = (data, match)

    ids: set[str] = set()
    output: list[RaceBlock] = []
    for row in expected:
        race_id = str(row.get("race_id", "")).strip()
        if not re.fullmatch(r"20\d{10}", race_id):
            raise SegmentationError(f"malformed target race_id: {race_id!r}")
        if race_id in ids:
            raise SegmentationError(f"duplicate target race_id: {race_id}")
        ids.add(race_id)
        try:
            expected_no = int(row.get("race_no", race_id[-2:]))
        except (TypeError, ValueError) as exc:
            raise SegmentationError(f"invalid race_no for {race_id}") from exc
        if expected_no != int(race_id[-2:]):
            raise SegmentationError(f"race_no conflicts with race_id for {race_id}")
        expected_date = str(row.get("date", row.get("race_date", "")))
        expected_venue = str(row.get("venue", "")).lower()
        key = (expected_date, expected_venue, expected_no)
        if key not in by_identity:
            same_number = [k for k in by_identity if k[2] == expected_no]
            if same_number:
                raise SegmentationError(
                    f"race heading identity mismatch for {race_id}: expected {key}, found {same_number}"
                )
            raise SegmentationError(f"race heading not found for {race_id}: {key}")
        data, match = by_identity[key]
        later = [m.start() for _, m in parsed if m.start() > match.start()]
        end = min(later) if later else len(text)
        block = text[match.start():end].strip()
        output.append(RaceBlock(
            race_id=race_id,
            race_date=str(data["race_date"]),
            venue=str(data["venue"]),
            race_no=int(data["race_no"]),
            meeting_no=int(data["meeting_no"]),
            meeting_day=int(data["meeting_day"]),
            page_text=block,
        ))
    return output
