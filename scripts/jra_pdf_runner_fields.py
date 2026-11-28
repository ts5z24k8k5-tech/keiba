"""Strict normalization of explicitly assigned JRA PDF runner cells.

This module does not locate columns, infer missing values, resolve IDs, or write
to any database. Callers must provide cells from a separately reviewed layout.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Mapping


class RunnerFieldParseError(ValueError):
    """Raised when a supplied cell is ambiguous or malformed."""


@dataclass(frozen=True)
class ParsedRunnerFields:
    raw_cells: dict[str, str]
    frame_no: int | None
    horse_no: int
    horse_name: str
    sex: str | None
    age: int | None
    impost_kg: float | None
    jockey_name: str | None
    trainer_name: str | None
    body_weight: int | None
    body_weight_change: int | None
    finish_raw: str | None
    finish_rank: int | None
    result_status: str | None
    finish_seconds: float | None
    margin_text: str | None
    final_win_odds: float | None
    final_popularity: int | None


def _clean(value: object, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise RunnerFieldParseError(f"{field} must be supplied as text")
    return unicodedata.normalize("NFKC", value).strip()


def _optional_int(value: object, field: str, *, minimum: int = 0) -> int | None:
    text = _clean(value, field)
    if not text:
        return None
    if not re.fullmatch(r"\d+", text):
        raise RunnerFieldParseError(f"{field} is not a plain integer: {text!r}")
    number = int(text)
    if number < minimum:
        raise RunnerFieldParseError(f"{field} is below minimum {minimum}")
    return number


def _optional_decimal(value: object, field: str, *, minimum: float = 0.0) -> float | None:
    text = _clean(value, field)
    if not text:
        return None
    if not re.fullmatch(r"(?:\d+)(?:\.\d+)?", text):
        raise RunnerFieldParseError(f"{field} is not a plain decimal: {text!r}")
    number = float(text)
    if number < minimum:
        raise RunnerFieldParseError(f"{field} is below minimum {minimum}")
    return number


def _parse_sex_age(value: object) -> tuple[str | None, int | None]:
    text = _clean(value, "sex_age")
    if not text:
        return None, None
    match = re.fullmatch(r"(牡|牝|セ)(\d{1,2})", text)
    if not match:
        raise RunnerFieldParseError(f"sex_age has unsupported format: {text!r}")
    return match.group(1), int(match.group(2))


def _parse_body_weight(value: object) -> tuple[int | None, int | None]:
    text = _clean(value, "body_weight")
    if not text:
        return None, None
    match = re.fullmatch(r"(\d{2,3})(?:\(([+-]\d{1,3}|\s*0)\))?", text)
    if not match:
        raise RunnerFieldParseError(f"body_weight has unsupported format: {text!r}")
    change = int(match.group(2).replace(" ", "")) if match.group(2) else None
    return int(match.group(1)), change


def _parse_finish(value: object) -> tuple[str | None, int | None, str | None]:
    raw = _clean(value, "finish")
    if not raw:
        return None, None, None
    if raw in {"中", "中止"}:
        return raw, None, "中"
    if raw in {"失", "失格"}:
        return raw, None, "失"
    if re.fullmatch(r"\d+\s*\(降\)", raw):
        # The displayed placing is provisional; final rank needs official reconciliation.
        return raw, None, "降"
    if re.fullmatch(r"\d+", raw):
        rank = int(raw)
        if rank < 1:
            raise RunnerFieldParseError("finish rank must be positive")
        return raw, rank, None
    raise RunnerFieldParseError(f"finish has unsupported format: {raw!r}")


def _parse_time(value: object) -> float | None:
    text = _clean(value, "finish_time")
    if not text:
        return None
    match = re.fullmatch(r"(\d+):(\d{2})\.(\d)", text)
    if not match:
        raise RunnerFieldParseError(f"finish_time has unsupported format: {text!r}")
    minutes, seconds, tenth = map(int, match.groups())
    if seconds >= 60:
        raise RunnerFieldParseError("finish_time seconds component must be below 60")
    return minutes * 60 + seconds + tenth / 10


def parse_runner_cells(cells: Mapping[str, object]) -> ParsedRunnerFields:
    """Normalize a caller-supplied cell mapping; preserve every raw cell."""
    allowed = {
        "frame_no", "horse_no", "horse_name", "sex_age", "impost_kg",
        "jockey_name", "trainer_name", "body_weight", "finish",
        "finish_time", "margin", "win_odds", "popularity",
    }
    unknown = set(cells) - allowed
    if unknown:
        raise RunnerFieldParseError(f"unknown cell keys: {', '.join(sorted(unknown))}")

    raw = {key: _clean(value, key) for key, value in cells.items()}
    horse_no = _optional_int(raw.get("horse_no", ""), "horse_no", minimum=1)
    if horse_no is None:
        raise RunnerFieldParseError("horse_no is required")
    horse_name = raw.get("horse_name", "")
    if not horse_name:
        raise RunnerFieldParseError("horse_name is required")

    sex, age = _parse_sex_age(raw.get("sex_age", ""))
    body_weight, body_change = _parse_body_weight(raw.get("body_weight", ""))
    finish_raw, finish_rank, result_status = _parse_finish(raw.get("finish", ""))

    return ParsedRunnerFields(
        raw_cells=raw,
        frame_no=_optional_int(raw.get("frame_no", ""), "frame_no", minimum=1),
        horse_no=horse_no,
        horse_name=horse_name,
        sex=sex,
        age=age,
        impost_kg=_optional_decimal(raw.get("impost_kg", ""), "impost_kg", minimum=0.0),
        jockey_name=raw.get("jockey_name") or None,
        trainer_name=raw.get("trainer_name") or None,
        body_weight=body_weight,
        body_weight_change=body_change,
        finish_raw=finish_raw,
        finish_rank=finish_rank,
        result_status=result_status,
        finish_seconds=_parse_time(raw.get("finish_time", "")),
        margin_text=raw.get("margin") or None,
        final_win_odds=_optional_decimal(raw.get("win_odds", ""), "win_odds", minimum=0.0),
        final_popularity=_optional_int(raw.get("popularity", ""), "popularity", minimum=1),
    )
