"""Coordinate-aware primitives for extracting text rows from JRA result PDFs.

The geometry layer accepts PyMuPDF's page.get_text("words") tuples but does
not import PyMuPDF. It can therefore be tested without external PDFs or the
optional PDF library.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable, Sequence


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


def positioned_words_from_pymupdf(raw_words: Iterable[Sequence[object]]) -> list[PositionedWord]:
    """Convert PyMuPDF 'words' tuples (x0,y0,x1,y1,text,...) to our type."""
    converted = []
    for item in raw_words:
        if len(item) < 5:
            raise ValueError("PyMuPDF word tuple must contain at least five fields")
        try:
            x0, y0, x1, y1 = (float(item[i]) for i in range(4))
        except (TypeError, ValueError) as exc:
            raise ValueError("word coordinates must be numeric") from exc
        text = str(item[4])
        if x1 < x0 or y1 < y0:
            raise ValueError("word has an inverted bounding box")
        if text.strip():
            converted.append(PositionedWord(x0, y0, x1, y1, text))
    return converted


def group_words_into_rows(
    words: Iterable[PositionedWord],
    *,
    baseline_tolerance: float = 2.5,
) -> list[TextRow]:
    """Group words by vertical center without allowing tolerance-chain drift.

    Each row has a fixed anchor: its median vertical center. A candidate joins
    only if it is within tolerance of that anchor. Words are sorted left-right.
    This is geometric grouping only; it does not infer semantic columns.
    """
    if baseline_tolerance < 0:
        raise ValueError("baseline_tolerance must be non-negative")

    ordered = sorted(words, key=lambda word: (word.center_y, word.x0, word.x1))
    buckets: list[list[PositionedWord]] = []
    anchors: list[float] = []

    for word in ordered:
        if not word.text.strip():
            continue
        if word.x1 < word.x0 or word.y1 < word.y0:
            raise ValueError("word has an inverted bounding box")

        candidates = []
        for index, bucket in enumerate(buckets):
            centers = [item.center_y for item in bucket]
            proposed_min = min(min(centers), word.center_y)
            proposed_max = max(max(centers), word.center_y)
            if proposed_max - proposed_min <= baseline_tolerance:
                candidates.append((abs(word.center_y - anchors[index]), index))
        if not candidates:
            buckets.append([word])
            anchors.append(word.center_y)
            continue

        _, index = min(candidates)
        buckets[index].append(word)
        anchors[index] = median(item.center_y for item in buckets[index])

    rows = []
    for anchor, bucket in zip(anchors, buckets):
        bucket.sort(key=lambda word: (word.x0, word.x1))
        rows.append(TextRow(anchor, tuple(bucket)))
    rows.sort(key=lambda row: row.y_center)
    return rows
