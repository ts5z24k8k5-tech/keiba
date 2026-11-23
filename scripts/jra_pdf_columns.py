"""Explicit x-coordinate column assignment for JRA PDF runner-row candidates.

Column boundaries must come from inspection of the actual source PDF. This
module deliberately does not guess JRA column positions or interpret values.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from scripts.jra_pdf_geometry import PositionedWord, TextRow


class ColumnAssignmentError(ValueError):
    """Raised when column boundaries are ambiguous or words cannot be assigned."""


@dataclass(frozen=True)
class ColumnBand:
    name: str
    x_min: float
    x_max: float


def validate_column_bands(bands: Iterable[ColumnBand]) -> list[ColumnBand]:
    ordered = sorted(bands, key=lambda band: band.x_min)
    if not ordered:
        raise ColumnAssignmentError("at least one column band is required")
    names: set[str] = set()
    previous: ColumnBand | None = None
    for band in ordered:
        if not band.name or band.name in names:
            raise ColumnAssignmentError(f"empty or duplicate column name: {band.name!r}")
        names.add(band.name)
        if band.x_max <= band.x_min:
            raise ColumnAssignmentError(f"invalid bounds for column {band.name!r}")
        if previous is not None and band.x_min < previous.x_max:
            raise ColumnAssignmentError(
                f"overlapping column bands: {previous.name!r} and {band.name!r}"
            )
        previous = band
    return ordered


def assign_word_to_column(word: PositionedWord, bands: Iterable[ColumnBand]) -> str:
    """Assign by word center; gaps/out-of-range centers are hard errors."""
    ordered = validate_column_bands(bands)
    center = (word.x0 + word.x1) / 2.0
    matches = [band for band in ordered if band.x_min <= center < band.x_max]
    if len(matches) != 1:
        raise ColumnAssignmentError(
            f"word center x={center:.2f} does not map to exactly one configured column"
        )
    return matches[0].name


def split_row_into_columns(
    row: TextRow,
    bands: Iterable[ColumnBand],
    *,
    reject_unassigned: bool = True,
) -> dict[str, str]:
    """Return text cells in visual left-to-right order; no semantic parsing."""
    ordered = validate_column_bands(bands)
    cells: dict[str, list[PositionedWord]] = {band.name: [] for band in ordered}
    unassigned: list[str] = []
    for word in row.words:
        try:
            name = assign_word_to_column(word, ordered)
        except ColumnAssignmentError:
            if reject_unassigned:
                raise
            unassigned.append(word.text)
            continue
        cells[name].append(word)

    result = {
        name: " ".join(word.text for word in sorted(words, key=lambda item: item.x0))
        for name, words in cells.items()
    }
    if unassigned:
        result["_unassigned"] = " ".join(unassigned)
    return result
