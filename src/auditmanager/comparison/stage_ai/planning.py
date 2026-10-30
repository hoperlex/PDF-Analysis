"""Read-only conservative estimates before deterministic text rows exist."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from auditmanager.comparison.ai_jobs.model import AiCallGroup, AiCounts, AiMode
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.stage_text.fragments import extract_fragments
from auditmanager.shared.errors import DomainError, ErrorCode

from . import classifier, reviewer, synthesis
from .source import link_components
from .validation import digest


class StageAiMethod:
    method = "stage_review"

    def __init__(self, repository, *, sessions=None, blob_store=None, profile_reader=None) -> None:
        self._repo = repository
        self._sessions = sessions
        self._blob_store = blob_store
        self._reader = profile_reader
        self.source_signature = ""
        self.source_profiles: list[dict[str, Any]] = []

    @property
    def prompt_version(self) -> str:
        return digest({
            "source": self.source_signature,
            "review": [reviewer.PROMPT_VERSION, reviewer.SYSTEM_PROMPT, reviewer.REVIEW_SCHEMA],
            "classify": [classifier.PROMPT_VERSION, classifier.SYSTEM_PROMPT, classifier.CLASSIFICATION_SCHEMA],
            "synthesize": [synthesis.PROMPT_VERSION, synthesis.SYSTEM_PROMPT, synthesis.SYNTHESIS_SCHEMA],
        })

    def _profiles(self):
        if self._reader is None:
            if self._blob_store is None:
                raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="comparison_stage_profiles")
            self._reader = PageProfileReader(self._sessions, self._blob_store)
        return self._reader

    def counts(self, session, request) -> AiCounts:
        revision = request.scope.stage_link_revision_id
        if not revision and request.scope.stage_chain_run_id:
            revision = self._repo.run(session, request.scope.stage_chain_run_id)["revision_id"]
        snapshot = self._repo.revision(session, revision)
        shape: dict[str, tuple[int, int]] = {}
        facts = []
        for row in snapshot["all_profiles"]:
            profile = self._profiles().read_page_profile(row["profile_id"])
            if (profile.row.profile_blob_id is None or profile.row.content_key != row["content_key"]
                    or profile.row.version_uid != row["version_uid"]):
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="stage_ai_profile_changed")
            fragments = extract_fragments(profile, side=row["side"])
            shape[row["profile_id"]] = (len(fragments), sum(len(f.text) for f in fragments))
            facts.append({"profile_id": row["profile_id"], "version_uid": row["version_uid"],
                          "content_key": row["content_key"],
                          "fragment_keys": [fragment.content_key for fragment in fragments]})
        self.source_profiles = facts
        self.source_signature = digest({"revision_id": revision, "profiles": facts,
                                        "links": snapshot["links"]})
        units = []
        if request.scope.stage_chain_run_id and request.mode is not AiMode.START:
            units = [dict(row) for row in session.execute(text(
                "SELECT kind,group_id,state,progress AS payload FROM stage_ai_unit WHERE stage_chain_run_id=:run"
            ), {"run": request.scope.stage_chain_run_id}).mappings()]
        completed = {(row["kind"], row["group_id"]) for row in units if row["state"] == "completed"}
        groups, call_groups = 0, []
        for component in link_components(snapshot["links"]):
            group_id = "grp:" + digest([link["stage_link_item_id"] for link in component])[:24]
            ids = {link[field] for link in component for field in ("left_profile_id", "right_profile_id")}
            count = sum(shape.get(profile, (0, 0))[0] for profile in ids)
            chars = sum(shape.get(profile, (0, 0))[1] for profile in ids)
            if count > 400:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="stage_pair_id", constraint="stage_ai_group_budget")
            if not count:
                continue
            groups += 1
            review_calls = (count + reviewer.MAX_ITEMS_PER_CHUNK - 1) // reviewer.MAX_ITEMS_PER_CHUNK
            review_chars = chars + count * 750 + 8_000
            classification_chars = chars * 2 + count * 800 + 8_000
            synthesis_chars = chars * 2 + count * 1_000 + 8_000
            if max(review_chars, classification_chars, synthesis_chars) > 240_000:
                raise DomainError(ErrorCode.VALIDATION_FAILED, field="stage_pair_id", constraint="stage_ai_group_budget")
            if ("review", group_id) not in completed:
                call_groups.append(AiCallGroup(calls=review_calls,
                    prompt_chars=review_chars, output_tokens=16_000))
            if ("classify", group_id) not in completed:
                call_groups.append(AiCallGroup(calls=1, prompt_chars=classification_chars,
                                               output_tokens=12_000))
            if ("synthesize", group_id) not in completed:
                call_groups.append(AiCallGroup(calls=1, prompt_chars=synthesis_chars,
                                               output_tokens=4_000))
        return AiCounts(groups=tuple(call_groups), units=groups, reused=0,
                        sheets=len(snapshot["all_profiles"]), pairs=len(snapshot["links"]),
                        versions=len({row["version_uid"] for row in snapshot["all_profiles"]}))

    def work_items(self, session, job, mode):
        # The caller's durable full-chain item owns advancement. Shared start is
        # called with queue_items=False, so no competing Stage AI worker appears.
        return []
