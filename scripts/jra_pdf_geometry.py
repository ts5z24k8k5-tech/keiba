"""Coordinate-aware grouping primitives for JRA PDF text extraction.

Input coordinates follow PyMuPDF's page coordinate system (points, origin at
top-left). This module is deliberately independent of PyMuPDF so geometry
logic can be unit-tested without downloading or parsing a real PDF.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PositionedWord:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2.0


@dataclass(frozen=True)
class TextRow:
    y_center: float
    words: tuple[PositionedWord, ...]

    @property
    def text(self) -> str:
        return " ".join(word.text for word in self.words)


def group_words_into_rows(
    words: Iterable[PositionedWord],
    *,
    baseline_tolerance: float = 2.5,
) -> list[TextRow]:
    """Group positioned words by vertical baseline, then order left-to-right.

    A word joins the closest existing row whose center is within the explicit
    tolerance. No semantic column inference or runner parsing is performed.
    """
    if baseline_tolerance < 0:
        raise ValueError("baseline_tolerance must be non-negative")

    ordered = sorted(words, key=lambda word: (word.center_y, word.x0, word.x1))
    rows: list[list[PositionedWord]] = []
    centers: list[float] = []

    for word in ordered:
        if not word.text.strip():
            continue
        if word.x1 < word.x0 or word.y1 < word.y0:
            raise ValueError("word has an inverted bounding box")

        candidates = [
            (abs(word.center_y - center), index)
            for index, center in enumerate(centers)
            if abs(word.center_y - center) <= baseline_tolerance
        ]
        if not candidates:
            rows.append([word])
            centers.append(word.center_y)
            continue

        _, index = min(candidates)
        rows[index].append(word)
        centers[index] = sum(item.center_y for item in rows[index]) / len(rows[index])

    result = []
    for center, row_words in zip(centers, rows):
        row_words.sort(key=lambda word: (word.x0, word.x1))
        result.append(TextRow(center, tuple(row_words)))
    result.sort(key=lambda row: row.y_center)
    return result
