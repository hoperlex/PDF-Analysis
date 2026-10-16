# W57A-INT-V3-PROMPT-MATERIAL-PREP-01 — unserved v3 prompt material

**Base:** published `origin/dev=6f1307412c94de45e67ffdeba71506dc5a0aa8fb`. **Status:** isolated source candidate; no model call, route, registry entry, remote publication or beta claim.

The new AR v3 renderer composes its draft system text from the existing reviewed AR checklist sections and the prompt rules fixed in W57 §A3.3. It JSON-quotes the PDF text layer as project evidence, keeps selected OCR as marked context, and appends exactly the `V3SetInput.prompt_part` as normative data. The full `rebinding_paragraphs` text stays local for deterministic citation grounding and is never sent by this renderer. It returns only immutable strings and a prompt-part character count; it does not interpret a model response or decide a finding.

The current published tree has no reviewed W57a map, qualified repaired W54 snapshot/set, registered v3 profile or `CAP-01` measurements for the v3 output cap. This task creates draft material for later review and does not choose an `ap_`/`pb_` ID, model, provider mode or `max_output_tokens`. V1/v2 source and prompt bytes remain untouched.

## Checks

- Focused AR v3 prompt and set-input tests: **20 passed**.
- Complete program governance suite: **16 passed**.
- `py_compile`, `git diff --check`, frozen API/stage/domain/error/migration SHA-256: passed.
- Test checks selected norm text appears only in user material, full rebinding-only text is absent, PDF content stays JSON data, OCR remains context and the reviewed v2 material digest is unchanged.

## Integration

Cherry-pick the bounded commit after dev41. The later W57a PROFILE owner must bind the reviewed map and exact Run-pinned, custody-checked set; inspect and seal these prompt bytes; enforce the G-11 input budget and CAP-01 output cap; and wire the v3 response schema and grounding before any provider call. No current return value is a canonical finding.

Changed paths are exactly this report, its formal task, the additive renderer and its offline tests. `contracts/**`, migrations, root locks, v1/v2 production, norms context, API/UI, composition root, `CURRENT_STATE.md` and remote refs were untouched.
