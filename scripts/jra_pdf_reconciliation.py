"""Field-by-field reconciliation against an independently supplied reference."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import unicodedata
from typing import Mapping, Sequence


class ReconciliationError(ValueError):
    pass


@dataclass(frozen=True)
class FieldDifference:
    field: str
    extracted: object
    reference: object
    status: str


@dataclass(frozen=True)
class ReconciliationReport:
    race_id: str
    horse_no: int
    compared_fields: tuple[str, ...]
    differences: tuple[FieldDifference, ...]

    @property
    def is_match(self) -> bool:
        return not self.differences

    @property
    def mismatch_count(self) -> int:
        return sum(item.status == "mismatch" for item in self.differences)

    @property
    def missing_count(self) -> int:
        return sum(item.status.startswith("missing_") for item in self.differences)


def _normalize(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        return " ".join(unicodedata.normalize("NFKC", value).split())
    return value


def reconcile_runner_fields(
    extracted: Mapping[str, object],
    reference: Mapping[str, object],
    *,
    race_id: str,
    horse_no: int,
    fields: Sequence[str],
    numeric_tolerances: Mapping[str, str] | None = None,
) -> ReconciliationReport:
    """Compare requested fields; nulls are not wildcards.

    Default comparison is normalized exact equality. Numeric tolerance is
    allowed only when explicitly configured by the caller.
    """
    if not race_id or not isinstance(horse_no, int) or isinstance(horse_no, bool) or horse_no < 1:
        raise ReconciliationError("valid race_id and positive integer horse_no are required")
    if not fields or len(set(fields)) != len(fields):
        raise ReconciliationError("fields must be non-empty and unique")
    tolerances = dict(numeric_tolerances or {})
    if set(tolerances) - set(fields):
        raise ReconciliationError("numeric tolerance supplied for an unrequested field")

    differences = []
    for field in fields:
        if field not in extracted or field not in reference:
            raise ReconciliationError(f"both inputs must contain requested field {field!r}")
        actual, expected = _normalize(extracted[field]), _normalize(reference[field])
        if actual is None and expected is None:
            continue
        if actual is None:
            status = "missing_extracted"
        elif expected is None:
            status = "missing_reference"
        elif field in tolerances:
            try:
                tolerance = Decimal(tolerances[field])
                a, b = Decimal(str(actual)), Decimal(str(expected))
            except (InvalidOperation, ValueError) as exc:
                raise ReconciliationError(f"invalid numeric value or tolerance for {field}") from exc
            if tolerance < 0:
                raise ReconciliationError(f"negative tolerance for {field}")
            status = "match" if abs(a - b) <= tolerance else "mismatch"
        else:
            status = "match" if actual == expected else "mismatch"
        if status != "match":
            differences.append(FieldDifference(field, actual, expected, status))

    return ReconciliationReport(race_id, horse_no, tuple(fields), tuple(differences))
