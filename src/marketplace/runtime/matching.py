"""Read-only local match composition for the Marketplace reference runtime."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .contracts import ExactRecordSource, MatchEvaluator


class RuntimeMatchError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class InvalidLocalRecordIdentityError(RuntimeMatchError):
    def __init__(self, field: str) -> None:
        super().__init__(
            "INVALID_LOCAL_RECORD_IDENTITY",
            f"{field} MUST be non-empty Record Identity text",
        )


class LocalRecordNotFoundError(RuntimeMatchError):
    def __init__(self, side: str, record_id: str) -> None:
        super().__init__(
            "LOCAL_RECORD_NOT_FOUND",
            f"{side} record {record_id!r} is not available in the local runtime source",
        )
        self.side = side
        self.record_id = record_id


class InvalidMatchEvaluatorResult(RuntimeMatchError):
    def __init__(self) -> None:
        super().__init__(
            "INVALID_MATCH_EVALUATOR_RESULT",
            "match evaluator MUST return a mapping",
        )


def _record_identity(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidLocalRecordIdentityError(field)
    return value


@dataclass(frozen=True)
class LocalMatchService:
    """Resolve two exact local records and delegate matching semantics.

    This application service deliberately does not interpret the evaluator's
    conclusion. It performs no fuzzy/latest/global resolution and no network
    fallback. A missing local record is a local availability condition only.
    """

    record_source: ExactRecordSource
    evaluate_match: MatchEvaluator

    def evaluate(
        self,
        left_record_id: str,
        right_record_id: str,
        *,
        method: str,
        base_status: str,
        observations: Sequence[Mapping[str, Any]],
        evidence_completeness: str,
        understood_critical: Iterable[str] = (),
    ) -> Mapping[str, Any]:
        left_id = _record_identity(left_record_id, "left_record_id")
        right_id = _record_identity(right_record_id, "right_record_id")

        left = self.record_source.get(left_id)
        if left is None:
            raise LocalRecordNotFoundError("left", left_id)

        if right_id == left_id:
            right = left
        else:
            right = self.record_source.get(right_id)
            if right is None:
                raise LocalRecordNotFoundError("right", right_id)

        result = self.evaluate_match(
            left,
            right,
            method=method,
            base_status=base_status,
            observations=observations,
            evidence_completeness=evidence_completeness,
            understood_critical=understood_critical,
        )
        if not isinstance(result, Mapping):
            raise InvalidMatchEvaluatorResult()
        return result
