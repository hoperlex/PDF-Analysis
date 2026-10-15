# W56A-INT-RESPONSE-PARSER-PREP-01 — offline AR v2 proposal parser

`response.py` reads the v2 schema's five proposal fields, closed category
and severity enums, and nonempty page/quote evidence. It returns immutable
proposals plus a count of complete but malformed elements. It does not
ground a quote or publish a finding; those remain separate stages.

A malformed response without a provider truncation signal raises
`V2ResponseError`. With an explicit truncation signal, the parser retains
only independently complete elements at the start of the `observations`
array. It never closes incomplete JSON, invents missing evidence or fills
in a category/severity. Even syntactically complete JSON is marked
`salvaged` when the provider reports truncation.

Checks: 21 focused AR v2 parser/schema/content tests passed, including
closed enum values, extra fields, bad pages/quotes, incomplete trailing
elements and wrong envelopes. Module compilation, direct task governance
and `git diff --check` passed. Pytest emitted only unrelated old `/tmp`
cleanup warnings. No full local gate, paid call, service-backed acceptance
or `origin/main` publication was run.

Changed paths: new `analysis/profiles/ar_v2/response.py`, one focused test,
this task/report and the top development status in `CURRENT_STATE.md`.
No shared contract, migration, provider lock, existing runtime module,
dependency, composition root, style, recording, stand file, `VERSION` or
release ref changed. Rollback is a revert before the profile lane wires
the parser; a wired profile requires a forward correction.

`W56A-PROFILES-01` must bind this parser, the schema and reviewed source
hash to a new immutable profile after its fresh grant, then pass structurally
valid proposals through the text-layer grounding gate. The available stand
config still selects a stub and the distinct recording route is unknown;
MODEL-PIN and live activation remain blocked. This is not a beta quality
or norm-validity verdict.
