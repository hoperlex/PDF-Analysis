/**
 * What a `failed` run terminated for, as a sentence instead of a bare identifier.
 *
 * `W28-LIVE` drove a failed run through a browser and found the screen honest and
 * otherwise well built, with one hole: the outcome block reads
 *
 *   > The run terminated `failed`. Nothing was published.
 *   > Terminal reason: `dependency_unavailable`
 *
 * — an identifier on a screen where every neighbouring line is a sentence. This module
 * is the sentence, and the rules it is written under are narrower than they look.
 *
 * **1. A sentence here restates the catalog, it does not diagnose the run.** Every string
 * below is derived from the `summary` its code carries in
 * `contracts/domain/v1/error-codes.json`, the frozen catalog the database CHECK-constrains
 * `audit_run.terminal_reason` against. Nothing here reads a stage, a provider mode or a
 * document, because the reading does not carry the facts that would license it.
 *
 * **2. The load-bearing case is `dependency_unavailable`, and the point of its sentence is
 * what it refuses to say.** The catalog's dependency class covers the metadata store, blob
 * storage, a model provider *and* the worker transport, and `RunStatus` carries no
 * `details`, so the reading never says which one. `W28-LIVE` measured the case that makes
 * this matter: in `recorded` mode a document with no recording fails with this code while
 * the provider is perfectly healthy. A sentence reading "the provider is down" would be
 * the `W27-REFUSE` defect — nginx's `413` rendered as "The upload did not reach the API",
 * true of the transport and wrong about the cause. So the sentence names the class, says
 * out loud that the run does not record which member of it, and stops.
 *
 * **3. Retryability is a permission, never a prediction.** The catalog marks
 * `dependency_unavailable` retryable. `W28-LIVE` measured three of three `recorded`-mode
 * runs failing with it, where no number of retries can succeed, because the missing thing
 * is a local file. "You may start the run again" is true; "a second run will get further"
 * is not something this screen knows.
 *
 * **4. The code is kept, not replaced.** The sentence is added beside the identifier. An
 * operator quoting a code into a search or an issue needs the code; a person reading a
 * screen needs the sentence. `W12-WEB`'s U-01 mutation — the terminal reason replaced by
 * a constant — stays reddened by the existing `run-progress` test either way.
 *
 * **5. A reason this table does not know still says something true.** See
 * :data:`UNDESCRIBED_PREFIX`. The catalog has been resealed twice inside this programme,
 * and `W15-AUTH` found five classifiers collapsing into `server_error` for want of a
 * branch. A code from a newer contract than this client was built against renders as an
 * explicit "this screen has no description for it", never as silence and never as a
 * neighbouring code's sentence.
 *
 * No string here contains an apostrophe. `renderToStaticMarkup` escapes one to `&#x27;`,
 * and a test that has to un-escape a sentence before comparing it is a test that can be
 * made to pass by changing the un-escaping.
 */

import type { ErrorCode } from '@/shared/api';

/**
 * One sentence per catalog code, each a restatement of that code's own `summary` in
 * `contracts/domain/v1/error-codes.json`.
 *
 * Keyed by `ErrorCode` and declared `Record`, not `Partial<Record>`: a reseal that adds a
 * twenty-third code stops this file type-checking rather than silently routing the new
 * code to the undescribed branch. `web/tests/unit/run/terminal-reason.test.ts` is the
 * runtime half of the same claim.
 */
const CATALOG_SENTENCES: Readonly<Record<ErrorCode, string>> = {
  validation_failed:
    'A declared schema, enum, format or invariant was violated, so the run stopped rather ' +
    'than record something that does not conform. The reason does not name which rule; the ' +
    'stage table below shows which stage carried it.',
  not_found:
    'Something this run addressed does not exist, or is not visible to the caller that ' +
    'addressed it. The reason does not name what it was: the catalog forbids an answer that ' +
    'reveals a resource the caller may not see.',
  authentication_required:
    'The run stopped because no valid authenticated subject was presented. The reason ' +
    'carries no hint about what was addressed.',
  permission_denied:
    'An authenticated subject was not permitted to do something this run needed. ' +
    'Authorization is decided on the server, and the reading does not record which ' +
    'capability was required.',
  conflict:
    'A concurrent write lost the optimistic-concurrency check, or a uniqueness invariant ' +
    'would have been violated. The catalog uses this reason only where no more specific ' +
    'conflict applies, so it does not say which invariant.',
  state_transition_not_allowed:
    'The run asked for a transition the frozen state machine does not declare from the ' +
    'state it was in. This is the fail-closed answer to every undeclared transition, and no ' +
    'flag overrides it.',
  idempotency_key_reuse:
    'An idempotency key was reused with a different payload. Nothing was created or ' +
    'changed, and no duplicate was made under the key.',
  idempotency_key_in_progress:
    'A command with the same key and the same payload was still executing. The remedy is to ' +
    'ask again under that same key; a new key would be a second command.',
  idempotency_key_stale:
    'The recorded outcome for an idempotency key could no longer be established, so the ' +
    'command failed closed instead of running a second time on a guess.',
  unsupported_contract_version:
    'A declared contract or schema version is unknown to this deployment. There is no ' +
    'tolerant fallback and no best-effort interpretation.',
  storage_integrity_error:
    'A declared checksum, byte size or media type did not match the bytes that were stored ' +
    'or delivered, or a required manifest role was missing. Nothing was published.',
  dependency_unavailable:
    'A dependency this run needs was unavailable. The catalog groups the metadata store, ' +
    'blob storage, a model provider and the worker transport into that one reason, and this ' +
    'reading does not record which of them it was — so on its own it is not evidence that ' +
    'the model provider is down. The catalog marks the reason retryable, which is permission ' +
    'to start the run again rather than a prediction that a second run gets further.',
  dependency_credential_refused:
    'A dependency refused a credential belonging to this deployment. No user of this API did ' +
    'anything wrong, and starting the run again does not change the outcome until an ' +
    'operator repairs the credential.',
  staged_upload_lost:
    'The blob store no longer held the bytes an upload had staged with it. Nothing was ' +
    'published and nothing was changed; sending the same upload again is the remedy.',
  required_norm_unavailable:
    'An authoritative reference this run depends on could not be resolved to an immutable ' +
    'versioned record. No unversioned, partial or substitute source was used in its place.',
  analysis_input_invalid:
    'A delivered analysis package or a declared stage input was not acceptable. The reading ' +
    'does not record which field; the stage table below shows which stage carried it.',
  analysis_failed:
    'The analysis ended in the failed terminal state. This is the general execution failure: ' +
    'it names the outcome rather than one cause, and where the stages recorded codes of ' +
    'their own those codes are in the stage table below.',
  partial_result_not_publishable:
    'A run that terminated with a recorded degradation was asked for something that requires ' +
    'a run without one. The degraded outcome and its missing set stay visible instead of ' +
    'being quietly filled in.',
  cost_budget_exceeded:
    'The declared cost or token budget for this run was exhausted. Execution stopped ' +
    'explicitly rather than silently degrade what it produced.',
  stale_attempt:
    'The attempt that submitted this work is no longer the publication authority for it. ' +
    'What was delivered is kept as immutable evidence and is never applied to project state.',
  execution_token_invalid:
    'The execution authority presented for this work was absent, malformed, or not the ' +
    'current one. The value itself is never echoed back, so the reason does not show it.',
  internal_error:
    'An unclassified server fault stopped this run. The run still carries a stable code and ' +
    'a correlation id; the internal detail stays in protected diagnostics and no path, ' +
    'query or stack content is shown here.',
};

/**
 * How a sentence for an unknown reason starts.
 *
 * Exported so the test asserts the real string rather than a copy of it, and so the
 * assertion that no catalog sentence begins this way is a comparison against the same
 * bytes the screen renders.
 */
export const UNDESCRIBED_PREFIX = 'This screen has no description for that reason and does not guess one.';

/** The sentence a `failed` reading that carries no reason at all gets. */
export const ABSENT_SENTENCE =
  'This reading carries no terminal reason. A failed run is required to record one, so ' +
  'this reading is missing something the contract obliges it to carry. Nothing is assumed ' +
  'in its place.';

/** What the screen can say about the reason a `failed` run terminated with. */
export type TerminalReasonNote =
  /** The reading carried no `terminal_reason`, which a `failed` run is obliged to have. */
  | { readonly kind: 'absent'; readonly sentence: string }
  /** The reason is a catalog code and this screen states what that code means. */
  | { readonly kind: 'described'; readonly code: string; readonly sentence: string }
  /** The reason is outside the catalog this client was built from. */
  | { readonly kind: 'undescribed'; readonly code: string; readonly sentence: string };

/**
 * Turn a run reading's `terminal_reason` into something a person can read.
 *
 * The parameter is `string | null` and not `ErrorCode | null` on purpose. The contract
 * types the field as an `ErrorCode`, and the generated client casts the response body
 * rather than validating it, so a server one reseal ahead of this client puts a string
 * here that the type says cannot exist. That is the case the `undescribed` arm is for; a
 * signature that refused to model it would have decided the screen should crash or say
 * nothing.
 */
export function terminalReasonNote(reason: string | null | undefined): TerminalReasonNote {
  if (reason === null || reason === undefined || reason === '') {
    return { kind: 'absent', sentence: ABSENT_SENTENCE };
  }
  // Membership is read from the sentence table itself and never from a second copy of
  // the catalog. An earlier draft tested `ERROR_CODE_VALUES.has(reason)` and then indexed
  // the table, so a code present in the generated enum and absent from the table returned
  // `sentence: undefined` and the screen rendered an empty paragraph — the silent hole
  // this module exists to close, reintroduced by the check meant to close it. Mutation M5
  // is that case, run.
  if (Object.prototype.hasOwnProperty.call(CATALOG_SENTENCES, reason)) {
    return { kind: 'described', code: reason, sentence: CATALOG_SENTENCES[reason as ErrorCode] };
  }
  return {
    kind: 'undescribed',
    code: reason,
    sentence:
      `${UNDESCRIBED_PREFIX} The code above is the word the run recorded, and this client ` +
      'holds no description for it. Nothing was published, and the stage table below shows ' +
      'which stage carried it.',
  };
}
