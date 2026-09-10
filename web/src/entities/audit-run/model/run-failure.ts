/**
 * Every way starting or watching a run can fail, as one explicit state each.
 *
 * The case this module exists for is `dependency_unavailable`. When the provider is
 * unavailable the screen says so, offers a retry under the same idempotency key, and
 * offers **nothing else** — in particular it never offers to fall back to `recorded`
 * mode. A silent downgrade from live to replayed would produce a run that looks like
 * evidence of a provider call that never happened, which is the exact confusion
 * `provider_mode` exists to prevent.
 *
 * `analysis_input_invalid` is kept distinct from `validation_failed`: the first says the
 * declared analysis inputs are not acceptable, the second says the request was malformed,
 * and collapsing them would hide which one the operator has to fix.
 */

import type { ErrorCode } from '@/shared/api';
import { ApiError, ApiFailure, TransportError, UnrecognizedApiError } from '@/shared/api';

export type RunFailureKind =
  | 'request_invalid'
  | 'analysis_input_invalid'
  | 'provider_unavailable'
  | 'not_found'
  | 'duplicate_intent'
  | 'in_progress'
  | 'stale_intent'
  | 'conflict'
  | 'not_allowed'
  | 'analysis_failed'
  | 'server_error'
  | 'unrecognized'
  | 'transport'
  | 'unknown';

export interface RunFailure {
  readonly kind: RunFailureKind;
  readonly presentation: 'unsupported' | 'error';
  readonly title: string;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
  readonly errorCode: ErrorCode | null;
}

/** Render only the safe scalar classifiers the catalog declares for this code. */
function classifiers(
  details: Readonly<Record<string, string | number | boolean | null>>,
  keys: readonly string[],
): string {
  const parts: string[] = [];
  for (const key of keys) {
    const value = details[key];
    if (value === undefined || value === null || value === '') continue;
    parts.push(`${key}: ${String(value)}`);
  }
  return parts.length === 0 ? '' : ` (${parts.join(', ')})`;
}

function fromApiError(error: ApiError): RunFailure {
  const base = {
    correlationId: error.correlationId,
    retryable: error.retryable,
    errorCode: error.errorCode,
  };

  switch (error.errorCode) {
    case 'dependency_unavailable':
      return {
        ...base,
        kind: 'provider_unavailable',
        presentation: 'error',
        title: 'The provider this run needs is unavailable.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['dependency']) +
          ' Nothing was partially applied. Retrying reuses the same idempotency key; ' +
          'the run is not started in a different provider mode instead.',
      };
    case 'analysis_input_invalid':
      return {
        ...base,
        kind: 'analysis_input_invalid',
        presentation: 'unsupported',
        title: 'The declared analysis inputs are not acceptable.',
        detail: error.envelope.message + classifiers(error.details, ['stage_id', 'reason']),
      };
    case 'validation_failed':
      return {
        ...base,
        kind: 'request_invalid',
        presentation: 'unsupported',
        title: 'This run request is not valid.',
        detail:
          error.envelope.message + classifiers(error.details, ['constraint', 'field', 'aggregate_type']),
      };
    case 'not_found':
      return {
        ...base,
        kind: 'not_found',
        presentation: 'error',
        title: 'This run or version does not exist.',
        detail: error.envelope.message + classifiers(error.details, ['aggregate_type']),
      };
    case 'idempotency_key_reuse':
      return {
        ...base,
        kind: 'duplicate_intent',
        presentation: 'error',
        title: 'This run key was already used for a different request.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['command_type']) +
          ' No run was created and nothing was resubmitted.',
      };
    case 'idempotency_key_in_progress':
      return {
        ...base,
        kind: 'in_progress',
        presentation: 'error',
        title: 'This run request is still executing.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['command_type']) +
          ' Retrying asks about the same request under the same key. A new key would be a second run.',
      };
    case 'idempotency_key_stale':
      return {
        ...base,
        kind: 'stale_intent',
        presentation: 'error',
        title: 'The recorded outcome of this run request is no longer available.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['command_type']) +
          ' It is not guessed.',
      };
    case 'state_transition_not_allowed':
      return {
        ...base,
        kind: 'not_allowed',
        presentation: 'error',
        title: 'The run is not in a state that allows this.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['machine', 'current_state', 'requested_state']),
      };
    case 'conflict':
      return {
        ...base,
        kind: 'conflict',
        presentation: 'error',
        title: 'The request conflicted with an invariant.',
        detail:
          error.envelope.message + classifiers(error.details, ['aggregate_type', 'expected_revision']),
      };
    case 'analysis_failed':
      return {
        ...base,
        kind: 'analysis_failed',
        presentation: 'error',
        title: 'The analysis failed.',
        detail: error.envelope.message + classifiers(error.details, ['run_id', 'stage_id']),
      };
    default:
      return {
        ...base,
        kind: 'server_error',
        presentation: 'error',
        title: 'The request failed on the server.',
        detail: error.envelope.message,
      };
  }
}

/** Classify anything thrown by `startRun` or by the run-status poll. */
export function classifyRunFailure(error: unknown): RunFailure {
  if (error instanceof ApiError) return fromApiError(error);

  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
      presentation: 'error',
      title: 'The server reported an error this client does not recognise.',
      detail: `Error code '${error.rawErrorCode}' is outside this client's contract. Nothing was retried.`,
      correlationId: error.correlationId,
      retryable: false,
      errorCode: null,
    };
  }

  if (error instanceof TransportError) {
    return {
      kind: 'transport',
      presentation: 'error',
      title: 'The request did not reach the API.',
      detail: `${error.message} The run state shown, if any, is the last reading and may be stale.`,
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    presentation: 'error',
    title: 'The request failed for an unclassified reason.',
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'The client received something it could not decode as a contract failure.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}
