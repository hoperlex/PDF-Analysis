# W57A-INT-SNAPSHOT-EVIDENCE-BRIDGE-01 — reviewed snapshot projection

## Result

`evidence_bridge.py` binds the SELECT reader's snapshot and canonical mapped
paragraphs to a digest-exact reviewed map and explicit caller-reviewed document
designations. The bridge checks stored slug identity, catalogue membership,
paragraph ordinals, raw reliability and text SHA-256, then returns the existing
`SnapshotBinding`, `SourceParagraph` and `TargetParagraph` types. It preserves
unreliable text as unreliable and leaves page labels as exact decimal strings
for the existing pure set builder. A focused end-to-end pure test uses its
output with ranking, set-byte and catalogue-byte builders.

## Checks

- Focused evidence-bridge suite: **5 passed**; combined reader, artifact and
  target suite: **25 passed**.
- Python compilation passed; direct task `governance_findings` returned `[]`;
  four owned files passed trailing-space and final-newline checks.
- Complete `make gate` deferred under R-135.

## Contracts and limits

No shared contract, migration, public API, dependency, composition or runtime
path changed. `PromptSelection` needs vectors/windows that this reader does not
return; it is caller-owned. The designation remains a separate owner-reviewed
input, bound to the stored `ndoc_` and slug but not authenticated as reviewed by
this module. The snapshot reader established DB paragraph totality within the
caller's consistent transaction; this pure bridge cannot independently recount
a missing trailing paragraph from its DTO. Matching `embedding_build` is only
identity agreement, not proof of a complete qualified build. No verified set,
custody, DB/S3 publication or beta claim follows.

## Integration instruction

After the owner reviews the map, designation choices and embedding build,
read `SnapshotEvidence` in one consistent transaction. Project with the exact
reviewed map and labels; feed the returned paragraphs to target resolution and
ranking. Supply separately verified windows/vectors, compare independent set
and catalogue expected digests, then follow W57 custody and verified-row steps.

## Ownership proof

Only four new task-owned paths were written. `contracts/**`, migration head,
other retrieval modules, norms repository, provider lock, public boundary,
composition root, root dependencies, global styles, corpus, `CURRENT_STATE.md`,
stand and Git refs were untouched by this task. The shared index contains
other integration work; stage only these four exact paths for this task.
