# AR-V3-ORIGINAL-TOPICS-01 — source-bound AR v3 topic guide

**Task:** [AR-V3-ORIGINAL-TOPICS-01](tasks/AR-V3-ORIGINAL-TOPICS-01.md).
**Initial base:** published `origin/dev=9b4d682ac412deda4fd8b7b2b6881e891e1b7942`.
Before publication the remote moved to `24aa9bbc1c71298eea8993654a17ac2ab13328b2`
(`EXEC-PULL-PROBE-INT-01`). This packet was rebased on that exact head; its
four-path executor diff is disjoint from the five paths here.

The original AR role and checklist at `/root/projects/PDF-proverka`
(`16ba8e5d`) were rechecked against the six-file manifest. The new
`original_topics.md` carries their exact SHA-256 provenance and a reviewed
topic guide for residential buildings, built-in premises and parking. It
restores planning, facade, roof, evacuation/fire, accessibility, thermal,
acoustic, documentation and lighting/insolation topics to draft v3 prompt
context. Lighting/insolation is limited to explicit internal consistency:
the current response schema has no normative category or qualified source for
it. No legacy number, clause assertion or supposed required drawing is
promoted to a rule.

The renderer checks the topic file's own digest and provenance markers before
including only the marked prompt body. A changed resource refuses. The
request-candidate SHA already binds the rendered system text. V1/v2 resources
and response schemas are unchanged.

## Checks

- Focused prompt/request and program governance on the rebased tree:
  **43 passed**.
- Python compilation and `git diff --check`: passed.
- Changed paths: exactly the new topic file, v3 renderer/test and this
  task/report. No forbidden hotspot changed.

## Integration limit

This is prompt fidelity work, still unserved. The topic guide is never
normative evidence. Serving citation-backed v3 still requires an approved
current map, qualified Run-pinned set, provider request, local grounding and
saved citation publication. Roll back by a forward revert of these five
paths; no data migration or feature flag is involved.
