"""Separate semantic quality evaluator: judge one candidate, never repair it.

The judge sees the whole goal plus its parameters and the natural request on
purpose (it is not a blind reader): the payload carries only public tool
contracts, the actual final canonical calls, the full visible context, the
natural request, and the proposed intent as an untrusted candidate claim.
Creator self-ratings, previous judge feedback, sampler quotas, and hidden
metadata are never sent. The model returns closed assessments only; this
module performs no edits or repairs on the model's authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, ValidationError

from tool_gen.client import OutputError
from tool_gen.models import GoalRecord, StrictModel, ToolCall
from tool_gen.prompts import load_prompt
from tool_gen.writer import Completer


class QualityAssessment(StrictModel):
    status: Literal["acceptable", "problem", "uncertain"]
    evidence: str = Field(min_length=1)


class OperationReview(StrictModel):
    new_information: QualityAssessment
    parameter_fit: QualityAssessment


class QualityReview(StrictModel):
    goal_usefulness: QualityAssessment
    parameter_fit: QualityAssessment
    request_fidelity: QualityAssessment
    language: QualityAssessment
    bundle_kind: Literal["related", "independent_batch", "unclear"]
    operations: dict[str, OperationReview]

    def assessments(self) -> list[tuple[str, QualityAssessment]]:
        result = [
            ("goal_usefulness", self.goal_usefulness),
            ("parameter_fit", self.parameter_fit),
            ("request_fidelity", self.request_fidelity),
            ("language", self.language),
        ]
        for key, operation in self.operations.items():
            result.extend(
                [
                    (f"{key}.new_information", operation.new_information),
                    (f"{key}.parameter_fit", operation.parameter_fit),
                ]
            )
        return result

    @property
    def accepted(self) -> bool:
        return all(item.status == "acceptable" for _, item in self.assessments())

    @property
    def uncertain(self) -> bool:
        statuses = [item.status for _, item in self.assessments()]
        return "uncertain" in statuses and "problem" not in statuses


def _assessment_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["acceptable", "problem", "uncertain"],
            },
            "evidence": {"type": "string", "minLength": 1},
        },
        "required": ["status", "evidence"],
        "additionalProperties": False,
    }


def quality_schema(call_count: int = 0) -> dict[str, object]:
    """Flattened inline assessment schema (no provider $refs)."""
    return {
        "type": "object",
        "properties": {
            "goal_usefulness": _assessment_schema(),
            "parameter_fit": _assessment_schema(),
            "request_fidelity": _assessment_schema(),
            "language": _assessment_schema(),
            "bundle_kind": {
                "type": "string",
                "enum": ["related", "independent_batch", "unclear"],
            },
            "operations": {
                "type": "object",
                "properties": {
                    f"call_{i}": {
                        "type": "object",
                        "properties": {
                            "new_information": _assessment_schema(),
                            "parameter_fit": _assessment_schema(),
                        },
                        "required": ["new_information", "parameter_fit"],
                        "additionalProperties": False,
                    }
                    for i in range(call_count)
                },
                "required": [f"call_{i}" for i in range(call_count)],
                "additionalProperties": False,
            },
        },
        "required": [
            "goal_usefulness",
            "parameter_fit",
            "request_fidelity",
            "language",
            "bundle_kind",
            "operations",
        ],
        "additionalProperties": False,
    }


def quality_prompt() -> str:
    return load_prompt("quality", "base")


def _public_contracts(goal: GoalRecord) -> list[dict[str, object]]:
    """Public tool contracts only: name, description, and parameter schema."""
    contracts: list[dict[str, object]] = []
    for entry in goal.tools:
        if not isinstance(entry, dict):
            continue
        function = entry.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if not isinstance(name, str) or not name:
            continue
        contract: dict[str, object] = {"name": name}
        description = function.get("description")
        if isinstance(description, str) and description.strip():
            contract["description"] = description
        parameters = function.get("parameters")
        if isinstance(parameters, dict):
            contract["parameters"] = parameters
        contracts.append(contract)
    return contracts


def _operation_features(call: ToolCall, goal: GoalRecord) -> dict[str, object]:
    """Observable projection overlap, not an automatic quality verdict."""
    for tool in goal.tools:
        function = tool.get("function")
        if not isinstance(function, dict) or function.get("name") != call.name:
            continue
        parameters = function.get("parameters")
        if not isinstance(parameters, dict):
            continue
        properties = parameters.get("properties")
        if not isinstance(properties, dict):
            continue
        projection = properties.get("fields")
        if not isinstance(projection, dict):
            continue
        description = projection.get("description")
        fields = call.arguments.get("fields")
        if (
            isinstance(description, str)
            and "projection" in description.casefold()
            and isinstance(fields, list)
            and fields
            and all(isinstance(key, str) and key in call.arguments for key in fields)
        ):
            return {"projects_only_supplied_input_keys": fields}
    return {}


def build_quality_payload(
    goal: GoalRecord, request: str, intent: str
) -> dict[str, object]:
    """Public evidence for the judge: contracts, canonical calls, context.

    The proposed intent travels as an untrusted candidate claim, never as
    authority. Local construction only; the wire carries this dict.
    """
    return {
        "style": goal.style,
        "no_call": goal.no_call,
        "tool_contracts": _public_contracts(goal),
        "canonical_calls": {
            f"call_{i}": {"name": call.name, "arguments": dict(call.arguments)}
            for i, call in enumerate(goal.witness)
        },
        "operation_features": {
            f"call_{i}": _operation_features(call, goal)
            for i, call in enumerate(goal.witness)
        },
        "known_context": dict(goal.context),
        "request": request,
        "proposed_intent": intent,
    }


def _parse_output(raw: object, request_id: str) -> QualityReview:
    if not isinstance(raw, dict):
        raise OutputError(f"{request_id}: model output is not a JSON object")
    try:
        return QualityReview.model_validate(raw)
    except ValidationError as exc:
        raise OutputError(
            f"{request_id}: model output violates quality schema: {exc.errors()[0]['msg']}"
        ) from None


def review_candidate(
    goal: GoalRecord,
    request: str,
    intent: str,
    complete: Completer,
    request_id: str,
) -> QualityReview:
    """Judge one candidate; assessments only, never edits or repairs.

    Operational transport failures (ClientError) escape to the caller; only
    unusable parsed model outputs become OutputError.
    """
    system = quality_prompt()
    payload = build_quality_payload(goal, request, intent)
    resp = complete(
        request_id, system, payload, quality_schema(len(goal.witness)), 0.0, 3072
    )
    review = _parse_output(resp.get("output"), request_id)
    expected = {f"call_{i}" for i in range(len(goal.witness))}
    if set(review.operations) != expected:
        raise OutputError(
            f"{request_id}: quality operations do not match candidate calls"
        )
    return review
