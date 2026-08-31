# Bootstrap validation

Validation executed before packaging.

```text
Bootstrap validation
  json_files=11
  markdown_files=119
  stages=11
  manual_runbooks=11
  adrs=18
PASS
```

## Checks performed

- all JSON files parse;
- JSON Schema draft 2020-12 definitions pass metaschema checks where applicable;
- shipped JobPackage/StageResult/ResultPackage/Event examples validate against their schemas;
- identifier prefixes are unique;
- state-machine transitions are closed and terminal states have no outgoing transitions;
- internal Markdown relative links resolve;
- required plan-of-record documents are present;
- expected counts exist: 11 stage plans, 11 manual checkpoint runbooks, 18 ADRs.

## Deliberate unresolved decisions

The package does not pretend to know owner/legal/product facts not supported by supplied sources. In particular exact retention TTL/legal-hold authority, tenant/IdP choice, cloud vendor and exact tool/runtime versions are frozen only by the designated future decision/toolchain tasks.

## Scope note

This validates the **bootstrap package itself**, not an implementation: production code does not yet exist by design. CP-01 and later checkpoints define executable product validation.
