# Synthetic section recordings (`W59-ANALYSIS-SETTINGS-01`)

**Every file here is synthetic.** The replies were authored by hand to prove that a
document version classified to АИ (`AI`), ПЗ (`PS`), ПОС (`POS`) or ТХ (`TX`) runs end
to end in recorded mode with its **own** section profile. No model produced them and no
provider call was made. They are not field evidence for any profile's expert review and
never count towards a profile becoming `reviewed`.

## Layout

| Path | What it is |
|---|---|
| `<code_lower>/<request_sha256>.json` | the one recording for that section's profile over the AR corpus text layer |
| `build_fixtures.py` | rebuilds every recording above; `--check` reports drift and stale files |

## How a recording is found

`RecordedAdapter()` built with no directory (what the composition root serves in
`recorded` mode) searches `fixtures/recorded/text_analysis/` and then each directory
here. An adapter given a directory reads only that directory, as before. The file name
is `sha256` of the canonical JSON of the exact request body: model, `max_tokens`, the
section profile's system prompt, the rendered text layer, `thinking` and
`output_config`. A different section's prompt is a different key, so an АИ recording
can never answer a ПЗ request; the same key in two searched directories is refused as
`recording_ambiguous`; no file at all is `recording_missing`. Either way the run fails
explicitly and nothing calls a provider.

## What each file declares

- `origin.kind: synthetic` with a statement, the task, the section, the profile and
  bundle identities, the bundle's `content_sha256`, the profile status at build time
  and the text layer the request was built over
  (`fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json`, the layer
  the pinned extractor produces from `fixtures/synthetic/ar/ar_baseline.pdf`);
- every `finding_text` opens with «Синтетический ответ (<раздел>), не результат вызова
  модели», so a finding published from one of these runs cannot pass for a model's;
- no `provider_mode` field (the adapter's class constant stamps `recorded`);
- authored, not measured, `usage` and `latency_ms`.

## Not a section: `ar_specification/`

`ar_specification/` (`SPEC-TABLE-RECORDING-01`) holds the synthetic **AR** reply for the
specification set `fixtures/synthetic/ar_specification/` -- the canonical AR profile's request
over that set's PDF, not a section profile's. It lives here only because `RecordedAdapter()`
searches the canonical directory and every directory below this one, and
`fixtures/recorded/text_analysis/` is closed to new recordings (its tests count its files). It is
rebuilt by its own `ar_specification/build_fixtures.py`, not by the one below.

## Refreshing

```
PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/build_fixtures.py
PYTHONPATH=src .venv/bin/python fixtures/recorded/sections/build_fixtures.py --check
```

Editing a section's `system_prompt.md` (or anything in
`auditmanager.analysis.text.prompt`) changes its key and orphans its recording; re-run
the builder.
