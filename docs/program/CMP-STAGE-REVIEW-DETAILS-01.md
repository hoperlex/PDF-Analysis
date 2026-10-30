# CMP-STAGE-REVIEW-DETAILS-01 — source-bound detail labels

Completed 2026-10-30 over root metadata seal `80b6b9e3`. API/schema/migration/AI/UI/wiring are not authored by this lane.

Stage card/detail/journal projections now expose `materiality`, `importance` and `detail_increased` from the original immutable classification card JSON. Matching requires the same class and exact atomic evidence ID set, plus matching card_key when historical JSON carries one. A foreign card in the same answer cannot lend its labels. The private classification ID never leaves the service projection. Missing/invalid/ambiguous labels yield unknown/unknown/false; raw/manual cards receive the same defaults. No category, text or model class is converted into a synthetic high/material assessment.

`counts.high_importance` now counts actual matched `high` labels. `counts.importance_unknown` explicitly counts unassessed cards. Existing total/review/project_changes/conflicts meanings remain. The synchronous journal exports still use the frozen journal columns and now correctly say AI materiality/importance require expert review, rather than claiming importance was never assessed. Card identities/evidence digests/verdict rules and immutable source rows do not change.

Focused evidence: **15 real-0042 PostgreSQL tests passed in 3.80 s**, covering metadata high/normal/old-default/invalid labels, raw unknown defaults and the existing connected review/promote workflows. **9 pure review/export tests passed**. The first metadata SQL check caught PostgreSQL JSONB operator precedence; explicit parentheses fixed the query and the focused suite passed. `git diff --check` clean. No full gate/build/browser/live-model/deploy/ref action.

Authored files: exact review service/writer note, focused `test_details.py`, the existing counts assertion in `test_service.py`, this task/report. Root can merge the local provider after expert escalation. The AI lane supplies genuine classifier labels and the UI lane groups sections; older answers remain useful with explicit unknown assessment. Broader windows remain deferred by the owner.
