/**
 * Refusals of the agent commands, worded (`EXEC2-WEB-WIZARD-01`).
 *
 * EXEC-2 adds no error code (ADR-0026 decision 18): the enrollment and install operations refuse
 * through `validation_failed` (a `field` and a `constraint`), `conflict` (a `conflict_reason`) and
 * `dependency_unavailable` (a `dependency`), the same safe detail keys the connection commands use.
 * The values are a closed set the executors context chooses. This module words the new ones —
 * `enrollment_shown_once`, `install_in_progress`, `agent_package`, `public_origin`, a refused
 * private key — and leaves every other refusal to `connectionFailure`, whose table already words
 * `connection_archived`, `no_revision` and `secrets_public_key_missing`. A value neither table knows
 * falls back to the code's own catalogue sentence, never to the server's English message.
 */

import { ApiError } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { connectionFailure } from '@/entities/executor-connection';

import { COMMAND_UNKNOWN_OUTCOME, CONFLICT_SENTENCES, DEPENDENCY_SENTENCES, VALIDATION_SENTENCES } from './words';

function detailText(error: ApiError, key: string): string | null {
  const value = error.details[key];
  return typeof value === 'string' ? value : null;
}

/** The sentence for a refusal this wizard words; `null` for any other. */
export function agentRefusalSentence(error: ApiError): string | null {
  if (error.errorCode === 'validation_failed') {
    const field = detailText(error, 'field');
    const constraint = detailText(error, 'constraint');
    return field === null || constraint === null ? null : (VALIDATION_SENTENCES[`${field}/${constraint}`] ?? null);
  }
  if (error.errorCode === 'conflict') {
    const reason = detailText(error, 'conflict_reason');
    return reason === null ? null : (CONFLICT_SENTENCES[reason] ?? null);
  }
  if (error.errorCode === 'dependency_unavailable') {
    const dependency = detailText(error, 'dependency');
    return dependency === null ? null : (DEPENDENCY_SENTENCES[dependency] ?? null);
  }
  return null;
}

/**
 * The failure of an agent command or read. A definite refusal gets its sentence; an unknown
 * outcome keeps the shared one, except that a command which shows a secret once (`issue`) says what
 * a repeat does, because for it a repeat is a new grant and never a retry of the old one.
 */
export function agentFailure(error: unknown, write: boolean, showsSecretOnce = false): ExecutionFailure {
  const base = connectionFailure(error, write);
  if (error instanceof ApiError) {
    const sentence = agentRefusalSentence(error);
    if (sentence !== null) {
      // A 503 on a write is an unknown outcome in general, but a dependency the server names before
      // it writes anything is a definite refusal: nothing was done, and «исход неизвестен» would
      // send the person to repeat a command that cannot work (the rule `connectionFailure` keeps).
      const definite = base.kind !== 'unknown_outcome' || error.errorCode === 'dependency_unavailable';
      if (definite) {
        return { ...base, kind: base.kind === 'unknown_outcome' ? 'refusal' : base.kind, detail: sentence };
      }
    }
  }
  if (showsSecretOnce && base.kind === 'unknown_outcome') return { ...base, detail: COMMAND_UNKNOWN_OUTCOME };
  return base;
}
