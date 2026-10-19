"""Score a backend against a labelled image set.

Manifest (JSON), paths relative to the manifest file::

    {"images": [{"image": "tyre1.jpg", "source": "<public URL>", "license": "CC BY 4.0",
                 "findings": [{"component": "tyre", "condition": "worn", "severity": "medium"}]}]}

Metrics, per image then summed:
- valid: the model produced a schema-valid report (after the usual retries)
- component recall: expected components whose name appears in a predicted component
  (case-insensitive substring either way, so "hydraulic hose" matches "hose")
- condition accuracy / severity exact / severity within one level: over matched components
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from .backends import Backend, BackendError
from .schema import Condition, InspectionReport, InvalidOutputError, Severity, inspect_image


class ExpectedFinding(BaseModel):
    component: str
    condition: Condition
    severity: Severity


class EvalItem(BaseModel):
    image: str
    source: str = ""
    license: str = ""
    findings: list[ExpectedFinding] = Field(min_length=1)


class EvalSet(BaseModel):
    images: list[EvalItem] = Field(min_length=1)


class EvalResult(BaseModel):
    images: int = 0
    valid: int = 0
    expected: int = 0
    matched: int = 0
    condition_correct: int = 0
    severity_exact: int = 0
    severity_within_one: int = 0

    @staticmethod
    def _rate(num: int, den: int) -> float | None:
        return num / den if den else None

    def rates(self) -> dict[str, float | None]:
        return {
            "valid output": self._rate(self.valid, self.images),
            "component recall": self._rate(self.matched, self.expected),
            "condition accuracy": self._rate(self.condition_correct, self.matched),
            "severity exact": self._rate(self.severity_exact, self.matched),
            "severity within one level": self._rate(self.severity_within_one, self.matched),
        }

    def to_markdown(self, label: str = "") -> str:
        head = f"Evaluation{f' ({label})' if label else ''}: {self.images} images, {self.expected} labelled findings"
        rows = ["| Metric | Score |", "|---|---|"]
        for name, rate in self.rates().items():
            rows.append(f"| {name} | {'n/a' if rate is None else f'{rate:.0%}'} |")
        return head + "\n\n" + "\n".join(rows)


def load_eval_set(manifest: Path) -> tuple[EvalSet, Path]:
    return EvalSet.model_validate(json.loads(manifest.read_text(encoding="utf-8"))), manifest.parent


def _match(expected: ExpectedFinding, report: InspectionReport):
    want = expected.component.lower()
    for f in report.findings:
        got = f.component.lower()
        if want in got or got in want:
            return f
    return None


def score_item(item: EvalItem, report: InspectionReport | None, into: EvalResult) -> None:
    into.images += 1
    into.expected += len(item.findings)
    if report is None:
        return
    into.valid += 1
    order = list(Severity)
    for exp in item.findings:
        got = _match(exp, report)
        if got is None:
            continue
        into.matched += 1
        into.condition_correct += got.condition == exp.condition
        gap = abs(order.index(got.severity) - order.index(exp.severity))
        into.severity_exact += gap == 0
        into.severity_within_one += gap <= 1


def evaluate(backend: Backend, manifest: Path, max_attempts: int = 3) -> EvalResult:
    data, root = load_eval_set(manifest)
    result = EvalResult()
    for item in data.images:
        try:
            report = inspect_image(backend, root / item.image, max_attempts)
        except (InvalidOutputError, BackendError, OSError):
            report = None
        score_item(item, report, result)
    return result
