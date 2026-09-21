/**
 * Every way a *read of a collection* can fail, as one explicit state each.
 *
 * `entities/project` already classifies `listProjects` this way, and its reason holds for
 * the three list operations `W18-SEAL` added: a read has no idempotency case, so the
 * surface is smaller than a write's, but "creating the project failed" over a failed
 * `GET` is a sentence that sends the reader looking for something they never asked to
 * create. Each listing therefore names its own subject.
 *
 * What is generic here is the mapping from catalog code to state, and what is not is the
 * wording. So the subject is a parameter: three entities share the mapping and none of
 * them shares a sentence. This lives in `shared/lib` and not in an entity because
 * `document-version` and `audit-run` both need it and an entity may not import another
 * entity.
 *
 * `classifyProjectListFailure` is deliberately **not** re-expressed in terms of this. It
 * is a `W16-WEB`-era classifier with its own tests and its own wording, and rewriting a
 * tested module to prove a point about reuse is how a green suite starts describing a
 * different program.
 */

import type { ErrorCode } from '@/shared/api';
import {
  AUTHENTICATION_REQUIRED_DETAIL,
  ApiError,
  ApiFailure,
  PERMISSION_DENIED_DETAIL,
  TransportError,
  UnrecognizedApiError,
} from '@/shared/api';

export type ListingFailureKind =
  | 'request_invalid'
  | 'parent_not_found'
  | 'dependency_unavailable'
  | 'not_authenticated'
  | 'not_permitted'
  | 'server_error'
  | 'unrecognized'
  | 'transport'
  | 'unknown';

/**
 * The two nouns every sentence below is built from.
 *
 * `collection` is what was being read — "the documents of this project". `parent` is the
 * aggregate the collection hangs off — "project" — because `W18-SEAL` §2 made an unknown
 * parent a `404` rather than an empty page, and a screen that renders that as "nothing
 * here yet" tells the user the opposite of what the server said.
 */
export interface ListingSubject {
  readonly collection: string;
  readonly parent: string;
}

export interface ListingFailure {
  readonly kind: ListingFailureKind;
  readonly title: string;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
  readonly errorCode: ErrorCode | null;
}

/** Classify anything thrown by `listDocuments`, `listVersions` or `listRuns`. */
export function classifyListingFailure(error: unknown, subject: ListingSubject): ListingFailure {
  const { collection, parent } = subject;

  if (error instanceof ApiError) {
    const base = {
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: error.errorCode,
      detail: error.envelope.message,
    };
    switch (error.errorCode) {
      case 'validation_failed':
        return { ...base, kind: 'request_invalid', title: `The request for ${collection} was refused.` };
      case 'not_found':
        return {
          ...base,
          kind: 'parent_not_found',
          title: `There is no such ${parent}.`,
          detail:
            `The server does not have this ${parent}, so there is nothing here to list. ` +
            'Это не то же самое, что пустой список, и повтор не выполняется.',
          retryable: false,
        };
      case 'dependency_unavailable':
        return {
          ...base,
          kind: 'dependency_unavailable',
          title: `A dependency needed to read ${collection} is unavailable.`,
        };
      case 'authentication_required':
        return {
          ...base,
          kind: 'not_authenticated',
          title: `Reading ${collection} is not authorized.`,
          detail: AUTHENTICATION_REQUIRED_DETAIL,
        };
      case 'permission_denied':
        return {
          ...base,
          kind: 'not_permitted',
          title: `You are not permitted to read ${collection}.`,
          detail: PERMISSION_DENIED_DETAIL,
        };
      default:
        return { ...base, kind: 'server_error', title: `${capitalize(collection)} could not be read.` };
    }
  }

  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
      title: 'Сервер сообщил об ошибке, которую этот клиент не распознаёт.',
      detail: `Error code '${error.rawErrorCode}' is outside this client's contract. Nothing was retried.`,
      correlationId: error.correlationId,
      retryable: false,
      errorCode: null,
    };
  }

  if (error instanceof TransportError) {
    return {
      kind: 'transport',
      title: `The request for ${collection} did not reach the API.`,
      detail: error.message,
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    title: `${capitalize(collection)} could not be read.`,
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'Клиент получил нечто, что не смог разобрать как отказ по контракту.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}

function capitalize(text: string): string {
  return text.length === 0 ? text : `${text[0]?.toUpperCase() ?? ''}${text.slice(1)}`;
}
