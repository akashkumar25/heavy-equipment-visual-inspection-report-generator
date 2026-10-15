"""Structured inspection output: schema, validation and retry on invalid output.

Small VLMs often wrap JSON in prose or code fences, or omit fields. ``inspect_image``
asks for JSON, validates it against ``InspectionReport`` and, if that fails, feeds the
validation error back to the model and tries again.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from .backends import Backend


class Condition(str, Enum):
    good = "good"
    worn = "worn"
    damaged = "damaged"
    leaking = "leaking"
    cracked = "cracked"
    missing = "missing"
    unknown = "unknown"


class Severity(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Finding(BaseModel):
    component: str = Field(min_length=1, description="e.g. tyre, track, hydraulic hose, bucket")
    condition: Condition
    severity: Severity
    recommended_action: str = Field(min_length=1)
    notes: str = ""


class InspectionReport(BaseModel):
    image: str = ""
    findings: list[Finding] = Field(min_length=1)

    @property
    def worst_severity(self) -> Severity:
        order = list(Severity)
        return max((f.severity for f in self.findings), key=order.index)


class InvalidOutputError(ValueError):
    """Raised when the model never produced a valid report."""


SCHEMA_PROMPT = """You are inspecting heavy equipment from a photo.
Reply with ONLY a JSON object, no prose and no code fences, in this form:
{{"findings": [{{"component": "<part>", "condition": "<{conditions}>",
"severity": "<{severities}>", "recommended_action": "<what to do>", "notes": "<optional>"}}]}}
List one finding per visible component (tyres, tracks, hoses, bucket, cracks, leaks)."""


def build_prompt() -> str:
    return SCHEMA_PROMPT.format(
        conditions="|".join(c.value for c in Condition),
        severities="|".join(s.value for s in Severity),
    )


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> object:
    """Pull the first JSON object out of text that may contain fences or surrounding prose."""
    fenced = _FENCE.search(text)
    candidate = fenced.group(1) if fenced else text
    start = candidate.find("{")
    if start == -1:
        raise ValueError("no JSON object found in model output")
    obj, _ = json.JSONDecoder().raw_decode(candidate[start:])
    return obj


def parse_report(text: str, image: str = "") -> InspectionReport:
    data = extract_json(text)
    if isinstance(data, dict):
        data.setdefault("image", image)
    return InspectionReport.model_validate(data)


def inspect_image(backend: Backend, image_path: Path, max_attempts: int = 3) -> InspectionReport:
    prompt = build_prompt()
    last_error = ""
    for _ in range(max_attempts):
        attempt_prompt = prompt
        if last_error:
            attempt_prompt += (
                f"\n\nYour previous reply was invalid ({last_error}). "
                "Reply again with only the corrected JSON object."
            )
        raw = backend.describe(image_path, attempt_prompt)
        try:
            return parse_report(raw, image=image_path.name)
        except (ValueError, ValidationError) as exc:
            last_error = " ".join(str(exc).split())[:300]
    raise InvalidOutputError(f"no valid report after {max_attempts} attempts: {last_error}")
