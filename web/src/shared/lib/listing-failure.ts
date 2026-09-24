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
  catalogMessage,
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
/**
 * The parents a listing can hang off, as a closed set rather than a free string.
 *
 * Russian declines, and every sentence below needs this noun in the genitive. A free
 * `string` cannot be declined, so the noun has to come from a table — and a table keyed on
 * a free string is the hand-maintained-set defect `W30-LISTS` closed eighteen instances of.
 * Narrowing the type instead makes the compiler the guard: a fourth parent stops
 * type-checking at the caller rather than rendering an English word inside a Russian
 * sentence. That is `run-state.ts`'s pattern, which is this repository's standard for a
 * hand-maintained set that no contract defines.
 */
export type ListingParent = 'project' | 'document' | 'version';

/**
 * A parent noun in the genitive, **with the determiners that have to agree with it**.
 *
 * `D-95`, and the reason this is a record rather than a string. The table used to hold the
 * noun alone and the sentences below wrote `Такого ${parent}` and `этого ${parent}` around
 * it — masculine forms, correct for `проекта` and `документа`. `версии` is **feminine**,
 * so a reviewer on a well-formed but absent version read:
 *
 * > Такого версии не существует. · На сервере нет этого версии, поэтому перечислять здесь
 * > нечего.
 *
 * Cyrillic throughout, well-formed word by word, and wrong as a sentence — which is why
 * `rendered-language.guard.test.ts` could not see it and never could: it fails on Latin
 * words a contract did not put there, and there is no Latin here.
 *
 * **A gendered word hard-coded beside a substitution is a bet that every value the
 * substitution can take has that gender.** The repair is to stop betting: the determiner
 * travels with the noun, so adding a fourth parent forces whoever adds it to write the
 * forms that go with it, and the compiler refuses an entry that leaves one out.
 * `web/tests/guards/gender-agreement.guard.test.ts` holds both halves — that no module
 * writes a determiner next to a `${…}` again, and that no sentence this classifier can
 * produce disagrees with itself.
 */
interface ParentNoun {
  /** The noun in the genitive, which is the case every sentence below puts it in. */
  readonly genitive: string;
  /** `Такого` / `Такой` — sentence-initial, agreeing with `genitive`. */
  readonly noSuch: string;
  /** `этого` / `этой` — mid-sentence, agreeing with `genitive`. */
  readonly thisOne: string;
}

const PARENT_GENITIVE: Readonly<Record<ListingParent, ParentNoun>> = {
  project: { genitive: 'проекта', noSuch: 'Такого', thisOne: 'этого' },
  document: { genitive: 'документа', noSuch: 'Такого', thisOne: 'этого' },
  version: { genitive: 'версии', noSuch: 'Такой', thisOne: 'этой' },
};

export interface ListingSubject {
  readonly collection: string;
  readonly parent: ListingParent;
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
  const { collection } = subject;
  const parent = PARENT_GENITIVE[subject.parent];

  if (error instanceof ApiError) {
    const base = {
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: error.errorCode,
      // The envelope's `message` is the API's own English, rendered from the frozen
      // catalog's `summary` fields. `W31-RUS` established that a client cannot translate
      // it and built the restatement this reads instead.
      detail: catalogMessage(error.errorCode),
    };
    switch (error.errorCode) {
      case 'validation_failed':
        return { ...base, kind: 'request_invalid', title: `Запрос на ${collection} отклонён.` };
      case 'not_found':
        return {
          ...base,
          kind: 'parent_not_found',
          title: `${parent.noSuch} ${parent.genitive} не существует.`,
          detail:
            `На сервере нет ${parent.thisOne} ${parent.genitive}, поэтому перечислять ` +
            'здесь нечего. Это не то же самое, что пустой список, и повтор не выполняется.',
          retryable: false,
        };
      case 'dependency_unavailable':
        return {
          ...base,
          kind: 'dependency_unavailable',
          title: `Зависимость, нужная чтобы прочитать ${collection}, недоступна.`,
        };
      case 'authentication_required':
        return {
          ...base,
          kind: 'not_authenticated',
          title: `Чтение: ${collection} — доступ не подтверждён.`,
          detail: AUTHENTICATION_REQUIRED_DETAIL,
        };
      case 'permission_denied':
        return {
          ...base,
          kind: 'not_permitted',
          title: `Нет прав на чтение: ${collection}.`,
          detail: PERMISSION_DENIED_DETAIL,
        };
      default:
        return { ...base, kind: 'server_error', title: `Не удалось прочитать ${collection}.` };
    }
  }

  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
      title: 'Сервер сообщил об ошибке, которую этот клиент не распознаёт.',
      detail: `Код ошибки '${error.rawErrorCode}' вне контракта этого клиента. Повтор не выполнялся.`,
      correlationId: error.correlationId,
      retryable: false,
      errorCode: null,
    };
  }

  if (error instanceof TransportError) {
    return {
      kind: 'transport',
      title: `Запрос на ${collection} не дошёл до API.`,
      detail: error.message,
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    title: `Не удалось прочитать ${collection}.`,
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'Клиент получил нечто, что не смог разобрать как отказ по контракту.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}

// `capitalize` was removed with the English sentences that needed it. The Russian ones put
// the collection noun mid-sentence, where it is already in the case and case-of-letter the
// caller supplies, so there is nothing left to capitalise.
