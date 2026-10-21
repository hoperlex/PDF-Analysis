# MODEL-IDENTITY-CHECK-01 — a reply from another model than the pinned one is a typed stage failure

Task: `docs/program/tasks/MODEL-IDENTITY-CHECK-01.md`. Branch `agent/lane-b-01`, base `ffdc32d1`
(`origin/dev`). Container-free (`R-126`); no live call, no key, no gateway probe.

## Result

In proxy mode, when the configured model is pinned, a chat-completions reply whose `model` is not the
configured name or a listed alias — or that carries no `model` at all — fails the stage with
`model_identity_mismatch`. The refusal is `outcome_unknown`, never retry-safe, keeps the reply's usage
evidence (the stage journals it as `response_received`), publishes no finding and carries no model name,
key or base URL. A matching reply behaves exactly as before. Recorded mode never reads a model.

For the two placeholder names the tree already uses, `proxy` and `replay`, the check is **not applied**,
and that is visible: `ProxyAdapter.identity_pinned` is `False`. See "Decisions taken".

## What changed

| File | Change |
| --- | --- |
| `src/auditmanager/analysis/text/adapter.py` | `ModelResponse.model: str \| None = None`, last field; not part of `response_sha256` |
| `src/auditmanager/analysis/text/proxy.py` | `_from_openai_response` reads the reply's `model` (absent, null or not text read as none); `ProxySettings.model_aliases: tuple[str, ...] = ()` with a structural check; `_UNPINNED_MODEL_NAMES`; read-only `ProxyAdapter.identity_pinned`; the check in `complete()`; `_identity_mismatch` and `_is_configured_model`; usage evidence factored out of `_unusable_answer` into `_received_evidence` (same behaviour) |
| `tests/integration/analysis_text/test_model_identity.py` | new, 60 cases |

`test_proxy_adapter.py` and `test_w53c_proxy_answer_shapes.py` are unchanged: with the base default
(`model="proxy"`, unpinned) they pass as they stood. No contract, migration, `runs/**`, `bootstrap/**` or
`norms/**` change. The failure code reaches the stage record and the run row without a `runs/**` edit:
`StageError.from_domain_error` carries `error.code` and `str(error)`, `_reason_for` in
`findings/terminal.py` admits any catalogue member, and `RetryPolicy` cannot hold a code the catalogue
marks non-retryable (`model_identity_mismatch` is `retryable: false`, 502).

## Decisions taken

1. **Deviation from the task file (integrator ruling, point 4 of the Work list superseded).** The task
   asked for stub or default names to be refused where `ProxySettings` validates its other values. I
   implemented that first and measured its blast radius on this branch, container-free, one file at a time:
   - `src/auditmanager/norms/__main__.py:309` `read_proxy_answer` builds `ProxySettings(model="replay")` to
     parse checkpointed bodies offline; a body naming the real model then raised the mismatch and
     `tests/integration/norms/repair/test_proxy_transport.py` failed 3 of 22 (the ledger replay and the
     sample command returned `unusable`);
   - removing the `model` default broke `tests/integration/analysis_text/test_proxy_truncation_reaches_partial.py`
     (2), `tests/integration/qa_w53/test_proxy_refusal_boundary.py` (2) and
     `tests/integration/composition/test_composition_root.py::test_the_proxy_adapter_reports_live` (passes
     at the base);
   - `src/auditmanager/bootstrap/settings.py:304` defaults `proxy_model` to `proxy` and
     `infra/deploy/env/provider.env.example:72` ships `PROXY_LLM_MODEL=proxy`, so a start-up refusal would
     refuse the stand's default proxy configuration; the database-backed composition tests that build the
     application in proxy mode would hit it too.

   The integrator replaced the refusal with the minimum-blast-radius version, which is what is delivered:
   `ProxySettings.model` keeps its base default; no model name is refused by the settings; the check is
   applied only to a pinned name; `proxy` and `replay` are the unpinned placeholders, held in one named
   constant with the reason for each; `identity_pinned` makes the gap explicit. Refusing the placeholder at
   start-up is the day of `W56A-MODEL-PIN-01`, by the bootstrap owner.
2. **Exact placeholder names.** `_UNPINNED_MODEL_NAMES == {"proxy", "replay"}` and nothing else. `default`,
   `auto`, `Proxy`, ` proxy` and the empty string are *pinned* names: a reply cannot equal them in practice,
   so they fail closed, which is the conservative direction. A test pins the set so a third name cannot
   unpin a model unnoticed.
3. **Exact match, no normalisation.** Neither the reported name nor the aliases are stripped, case-folded
   or prefix-matched; a dated variant a gateway echoes is added to `model_aliases` deliberately.
4. **A reply `model` that is not text reads as "none named"** and, when pinned, is a mismatch: one typed
   outcome for every way a reply fails to name the model, instead of a second code for malformed names.
5. **Aliases are validated structurally only**: a tuple of non-blank strings. A list or a bare string would
   be iterated into characters and a blank alias would accept a reply naming nothing. No model name is
   refused.
6. **The reported name goes to the server-side log only**, as `repr`, cut at 80 characters, on a mismatch
   (so an operator can tell a foreign model from a dated variant that belongs in `model_aliases`). The
   failure message names no model, key or URL, as the catalogue note requires; `details` is empty.
7. **Precedence.** A reply that is otherwise unusable (no choices, bad usage) is still
   `analysis_failed`, as before; the identity check runs on a parsed reply.

## Commands and exit statuses

All from `/root/projects/PDF-Analysis/.local/worktrees/lane-b`, interpreter
`/root/projects/PDF-Analysis/.venv/bin/python`, `nice -n 10`, `-c pyproject.toml --rootdir=. -q -p no:cacheprovider`,
status read from `$?` of the pytest process. A plugin printed the import origin at session start: both
`proxy.py` and `adapter.py` were imported from this worktree's `src/`.

| Command (files) | Before (base `ffdc32d1`) | After |
| --- | --- | --- |
| `test_proxy_adapter.py test_w53c_proxy_answer_shapes.py test_provider_modes.py tests/unit/analysis test_proxy_truncation_reaches_partial.py` | rc 0, 158 passed | rc 0, 158 passed (same files) |
| `test_model_identity.py` | does not exist (an import of `_UNPINNED_MODEL_NAMES` fails on the base) | rc 0, 60 passed |
| required set: `test_model_identity.py test_proxy_adapter.py test_w53c_proxy_answer_shapes.py test_provider_modes.py tests/unit/analysis` | 156 passed without the new file | rc 0, 216 passed |
| `tests/integration/norms/repair/test_proxy_transport.py` (outside the allowed paths, run only) | rc 0, 22 passed | rc 0, 22 passed, unchanged |
| `tests/integration/qa_w53/test_proxy_refusal_boundary.py` (run only) | rc 0, 2 passed | rc 0, 2 passed |
| `tests/integration/composition/test_composition_root.py` (run only) | rc 1, 18 failed, 3 passed (database) | rc 1, 18 failed, 3 passed; the failing set is identical to the base |
| `git diff --check` | | rc 0 |

## Mutation probes

The copy is `.local/mut-b1/src` (a copy of `src/` with `contracts`, `docs`, `fixtures` linked beside it);
each run used `-o pythonpath=<copy>/src` and the plugin line proved `copy_imported=True`. The unmutated
copy passed 60 of 60 first. Each mutation was applied to the copy alone, run against
`test_model_identity.py`, and restored.

| Branch guarded | Mutation | Result |
| --- | --- | --- |
| the check exists | `if self.identity_pinned and not ...` replaced by `if False:` | 30 failed |
| missing field fails closed | `reported is not None and (...)` → `reported is None or (...)` | 8 failed |
| alias accepted | drop `or reported in settings.model_aliases` | 1 failed |
| exact match | `startswith(settings.model)` for the name | 3 failed |
| exact match | `.lower()` on both sides | 1 failed |
| exact alias match | alias compared by `startswith` | 1 failed |
| pinned for every name | `identity_pinned` returns `True` | 12 failed |
| pinned for no name | `identity_pinned` returns `False` | 31 failed |
| placeholder set | gains `default` | 2 failed |
| placeholder set | loses `replay` | 1 failed |
| placeholder set | compared case-folded and stripped | 3 failed |
| typed refusal | `retry_safe=True` | 9 failed |
| typed refusal | `dispatch_class="not_sent"` | 11 failed |
| typed refusal | code `analysis_failed` | 29 failed |
| usage evidence kept | `received=None` | 10 failed |
| message carries no name | reported name interpolated into the message | 1 failed |
| details carry no name | reported name put under `details` | 1 failed |
| log is bounded | `%.80r` → `%r` | 1 failed |
| log carries no key | token added to the log line | 1 failed |
| match is silent | a warning logged on every checked reply | 1 failed |
| alias list type | tuple test removed (list, bare string accepted) | 2 failed |
| alias list type | tuple test replaced by a bare `any(...)` | 2 failed |
| alias blank | blank alias allowed | 3 failed |
| alias type | non-string alias allowed | 2 failed |
| non-text model | passed through unchanged | 2 failed |
| model not read | `model=None` in `_from_openai_response` | 8 failed |
| checksum | `model` added to `response_sha256` | 1 failed |
| response default | `ModelResponse.model` defaults to `""` | 2 failed (the recorded replay named a model) |
| settings default | `ProxySettings.model` default changed | 1 failed |

## Not exercised

- No database-backed suite and no composition test that builds the application: `test_composition_root.py`
  fails 18 of 21 at the base for want of `DATABASE_URL`, with the same failing set after.
- No live call, no gateway, no stand, no complete gate and no `tests/contract` battery (`R-135`; the
  integrator's gate runs them on the merged candidate).
- The path from the stage error to the persisted `audit_run.terminal_reason` was read, not run: it needs a
  database. The stage-level behaviour (status, no artifact, journalled usage, not retried) is tested.

## Risks and known limitations

- **The check does not protect an installation that keeps `PROXY_LLM_MODEL=proxy` (the default and the
  example file).** `identity_pinned` is `False` there and nothing yet surfaces it; a later slice can read it.
  Until the placeholder is refused at start-up, only a deployment that names a concrete model is covered.
- **Norms and the check.** `ProxyRepairTransport` and `ProxyPageRecogniser` pass the operator's concrete
  `PROXY_LLM_MODEL` to the same adapter, so a gateway that echoes a dated variant now fails their calls
  as `outcome_unknown` unless the variant is in `model_aliases`, which `norms/__main__.py` cannot set
  today. Follow-up debt for the integrator: aliases for `ProxyRepairTransport`.
- A pinned name that the gateway never echoes exactly would be paid for and then refused on every call
  (the plan's own warning); the freeze's identity probe (`W56A-PROBE-01`, failed) is what establishes the
  right name and alias for each gateway.

## Instruction for the integrator

Merge as a real merge into `integration/night-1020`. Light acceptance: `git diff --check`; the named test
files; `tests/contract` with the three ignores. Register as follow-up debt: refusing `proxy` at start-up
(`bootstrap/settings.py:304`, `infra/deploy/env/provider.env.example:72`) with `W56A-MODEL-PIN-01`; aliases for
`ProxyRepairTransport`; surfacing `identity_pinned` in the run or health reading.
