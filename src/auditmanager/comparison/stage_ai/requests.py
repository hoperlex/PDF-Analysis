"""Transport-neutral call plans for the shared consent/spend/runtime boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .validation import canonical_json, digest


@dataclass(frozen=True, slots=True)
class CallPlan:
    phase: str
    unit_key: str
    group_id: str
    source_sha256: str
    content_key: str
    prompt_version: str
    model: str
    instructions: str
    payload_json: str
    schema_json: str
    max_output_tokens: int

    @property
    def prompt_chars(self) -> int:
        return len(self.instructions) + len(self.payload_json) + len(self.schema_json)

    @property
    def response_schema(self) -> dict[str, Any]:
        return json.loads(self.schema_json)

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.payload_json)

    def estimate_group(self):
        """One C2 call-group estimate; no route, consent, spend or provider side effect."""
        from auditmanager.comparison.ai_jobs.model import AiCallGroup
        return AiCallGroup(calls=1, prompt_chars=self.prompt_chars,
                           output_tokens=self.max_output_tokens)

    def request_document(self) -> dict[str, Any]:
        return {
            "model": self.model, "system": self.instructions,
            "messages": [{"role": "user", "content": self.payload_json}],
            "max_tokens": self.max_output_tokens,
            "response_schema": self.response_schema,
            "metadata": {"phase": self.phase, "content_key": self.content_key,
                         "source_sha256": self.source_sha256, "unit_key": self.unit_key},
        }


def make_plan(*, phase: str, group_id: str, unit_key: str, source: dict[str, Any],
              payload: dict[str, Any], schema: dict[str, Any], instructions: str,
              version: str, model: str, output_tokens: int) -> CallPlan:
    if not isinstance(model, str) or not model.strip() or len(model) > 200:
        raise ValueError("pinned_model_invalid")
    source_sha = digest(source)
    body = dict(payload) | {"source_sha256": source_sha}
    encoded = canonical_json(body)
    schema_json = canonical_json(schema)
    if len(encoded) > 240_000:
        raise ValueError("stage_ai_request_budget_exceeded")
    key = digest({"phase": phase, "unit_key": unit_key, "source_sha256": source_sha,
                  "prompt_version": version, "prompt": instructions,
                  "schema": schema, "model": model, "output_tokens": output_tokens})
    return CallPlan(phase, unit_key, group_id, source_sha, key, version, model,
                    instructions, encoded, schema_json, output_tokens)
