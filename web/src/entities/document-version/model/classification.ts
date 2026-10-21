/**
 * A version's project stage and section, as this application shows them
 * (`W59-SECTION-UI-01`).
 *
 * **Who decides.** An expert confirms both, explicitly, through `classifyDocumentVersion`;
 * the stored answer is `DocumentVersion.classification` and `SectionReview.classification`.
 * Nothing here infers a stage or a section: a file name, a keyword hit or the legacy
 * document `section` is evidence a reviewer reads, never a classification (owner poll answer
 * `S-4`). That is why {@link orderSectionOptions} only *orders* the fifteen choices and never
 * pre-selects one, and why {@link ClassificationBadges} says «раздел не подтверждён» instead
 * of showing the best suggestion.
 *
 * **Who may.** `classifyDocumentVersion` requires the `expert` role, and `admin` alone does
 * not imply it (the backend's role table). {@link canClassifyVersion} is the same rule as a
 * hint for which control to draw; the API still checks every write, and its `403` has its
 * own sentence below.
 *
 * **What a refusal says.** A different stage or section over an existing classification is
 * `409 conflict` with `conflict_reason: version_already_classified` and changes nothing: the
 * screen shows the stored classification as «уже подтверждено другим решением». Changing a
 * confirmed classification is a separate act, the correction (`CLASSIFICATION-CORRECTION-01`,
 * `correctVersionClassification`): an expert appends a numbered revision with a reason, the
 * latest revision is the version's classification, and the history (`SectionReview.revisions`)
 * keeps every earlier one. {@link canCorrectClassification}, {@link reasonProblem} and
 * {@link correctionFailure} are its counterparts of the three rules above.
 */

import type {
  ProjectSection as SectionCode,
  ProjectStage,
  Role,
  SectionReviewOption,
  SectionSuggestion,
  VersionClassification,
  VersionClassificationRevision,
  VersionUid,
} from '@/shared/api';
import { ApiError, PROJECT_STAGE_VALUES } from '@/shared/api';
import type { FailureKind } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';
import { projectSectionOf, projectSectionTitle, structureRank } from '@/entities/project';

/** How one project stage reads on screen: the Cyrillic mark and its meaning. */
export interface ProjectStagePresentation {
  /** `П` or `Р`, the mark a designer writes on a title block. */
  readonly abbr: string;
  /** `проектная` or `рабочая`. */
  readonly name: string;
}

/** Keyed by the contract's closed set, so a third stage fails to compile here. */
export const PROJECT_STAGE_LABELS: Readonly<Record<ProjectStage, ProjectStagePresentation>> = {
  P: { abbr: 'П', name: 'проектная' },
  R: { abbr: 'Р', name: 'рабочая' },
};

/** The stages in the contract's order, for a choice that offers both. */
export const PROJECT_STAGES: readonly ProjectStage[] = PROJECT_STAGE_VALUES;

/** «Стадия: П». */
export function stageBadgeText(stage: ProjectStage): string {
  return `Стадия: ${PROJECT_STAGE_LABELS[stage].abbr}`;
}

/** «П — проектная», the label of one choice. */
export function stageChoiceText(stage: ProjectStage): string {
  const label = PROJECT_STAGE_LABELS[stage];
  return `${label.abbr} — ${label.name}`;
}

/** «Архитектурные решения (АР)»: the section's name with the mark, never the Latin code. */
export function sectionTitleOf(code: SectionCode): string {
  return projectSectionTitle(projectSectionOf(code));
}

/** The address one version is classified at: its project, its document and the version itself. */
export interface VersionAddress {
  readonly projectUid: string;
  readonly documentUid: string;
  readonly versionUid: VersionUid;
}

/** Whether to draw the classification control. Only `expert`; `admin` alone is refused. */
export function canClassifyVersion(roles: readonly Role[]): boolean {
  return roles.includes('expert');
}

/** The fifteen choices, split for the form: suggested first, then every other section. */
export interface OrderedSectionOptions {
  /** Options carrying evidence, strongest first; ties in the project structure's order. */
  readonly suggested: readonly SectionReviewOption[];
  /** Options with no evidence, in the project structure's order (`S-5`). */
  readonly rest: readonly SectionReviewOption[];
}

/**
 * Order the review's options for a reviewer. It never drops one and never picks one: every
 * section stays choosable whatever the heuristics found, which is the review's own promise.
 */
export function orderSectionOptions(options: readonly SectionReviewOption[]): OrderedSectionOptions {
  const byStructure = (a: SectionReviewOption, b: SectionReviewOption) =>
    structureRank(a.section_code) - structureRank(b.section_code);
  const suggested = options
    .filter((option) => option.suggestion !== null)
    .sort(
      (a, b) =>
        (b.suggestion?.score ?? 0) - (a.suggestion?.score ?? 0) || byStructure(a, b),
    );
  const rest = options.filter((option) => option.suggestion === null).sort(byStructure);
  return { suggested, rest };
}

/** What the evidence behind one suggestion was, in the reviewer's words. */
export interface SuggestionEvidence {
  /** The file-name patterns that matched, exactly as the server reported them. */
  readonly filenamePatterns: readonly string[];
  /** The text keywords that matched, exactly as the server reported them. */
  readonly textKeywords: readonly string[];
  /** Whether the section's own name was found in the recognised text. */
  readonly nameInText: boolean;
}

export function suggestionEvidence(suggestion: SectionSuggestion): SuggestionEvidence {
  return {
    filenamePatterns: suggestion.filename_patterns,
    textKeywords: suggestion.text_keywords,
    nameInText: suggestion.name_in_text,
  };
}

/** The option for `code`, or `null` when the review did not list it. */
export function reviewOptionOf(
  options: readonly SectionReviewOption[],
  code: SectionCode,
): SectionReviewOption | null {
  return options.find((option) => option.section_code === code) ?? null;
}

export type ClassificationFailureKind =
  | 'already_classified'
  | 'not_permitted'
  | 'not_found'
  | FailureKind;

export interface ClassificationFailure {
  readonly kind: ClassificationFailureKind;
  /** The Russian sentence a screen renders. Never a thrown value's own message. */
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
}

/** `409 version_already_classified`. Shown beside the stored classification, never instead. */
export const ALREADY_CLASSIFIED_DETAIL =
  'Стадия и раздел этой версии уже подтверждены другим решением. Ваш выбор не применён и ' +
  'ничего не изменено; изменить подтверждённую классификацию может эксперт кнопкой ' +
  '«Исправить» с указанием причины.';

/** `403` on the classification write: the role, not the credential, is what is missing. */
export const CLASSIFY_NOT_PERMITTED_DETAIL =
  'Подтвердить стадию и раздел может только пользователь с ролью «Эксперт». У вашей учётной ' +
  'записи этой роли нет, поэтому ничего не изменено.';

/** Classify anything `classifyDocumentVersion` threw, and say it in Russian. */
export function classificationFailure(error: unknown): ClassificationFailure {
  if (error instanceof ApiError) {
    const base = { correlationId: error.correlationId, retryable: error.retryable };
    if (
      error.errorCode === 'conflict' &&
      error.details['conflict_reason'] === 'version_already_classified'
    ) {
      return { ...base, kind: 'already_classified', detail: ALREADY_CLASSIFIED_DETAIL };
    }
    if (error.errorCode === 'permission_denied') {
      return { ...base, kind: 'not_permitted', detail: CLASSIFY_NOT_PERMITTED_DETAIL };
    }
    if (error.errorCode === 'not_found') {
      return {
        ...base,
        kind: 'not_found',
        detail:
          'Такой версии в этом документе и проекте нет. Ничего не изменено; откройте версию ' +
          'заново из списка документов проекта.',
      };
    }
  }
  const failure = failureMessage(error, {
    validation_failed:
      'Сервер не принял выбор: стадия и раздел должны быть из предложенных. Ничего не изменено.',
  });
  return {
    kind: failure.kind,
    detail: failure.detail,
    correlationId: failure.correlationId,
    retryable: failure.retryable,
  };
}

// -- the correction (`CLASSIFICATION-CORRECTION-01`) ---------------------------------------

/** The longest reason, in characters: the contract's `maxLength` of the correction request. */
export const CORRECTION_REASON_MAX_LENGTH = 2000;

/** Whether to draw the correction control. Only `expert`; `admin` alone is refused. */
export function canCorrectClassification(roles: readonly Role[]): boolean {
  return roles.includes('expert');
}

/** Whether a classification has ever been corrected: revision 1 is the original confirmation. */
export function isCorrected(classification: Pick<VersionClassification, 'revision'>): boolean {
  return classification.revision > 1;
}

/** «Ревизия 2»: the number a correction is based on, as a reader sees it. */
export function revisionText(revision: number): string {
  return `Ревизия ${revision}`;
}

/** Whether the chosen pair differs from the current classification, which a correction must. */
export function differsFromCurrent(
  current: Pick<VersionClassification, 'project_stage' | 'section_code'>,
  stage: ProjectStage | null,
  section: SectionCode | null,
): boolean {
  return stage !== null && section !== null && (stage !== current.project_stage || section !== current.section_code);
}

export type ReasonProblem = 'required' | 'too_long';

/**
 * What is wrong with a reason before it is sent, or `null`. The server decides; this only
 * keeps the button honest: trimmed text with at least one letter or digit, and no more than
 * {@link CORRECTION_REASON_MAX_LENGTH} characters.
 */
export function reasonProblem(raw: string): ReasonProblem | null {
  const text = raw.trim();
  if (text === '' || !/[\p{L}\p{N}]/u.test(text)) return 'required';
  if (Array.from(text).length > CORRECTION_REASON_MAX_LENGTH) return 'too_long';
  return null;
}

export function reasonProblemText(problem: ReasonProblem): string {
  return problem === 'required'
    ? 'Укажите причину исправления: нужна хотя бы одна буква или цифра.'
    : `Причина длиннее ${CORRECTION_REASON_MAX_LENGTH} символов.`;
}

/** The history newest first, which is how a reader looks for «what changed last». */
export function revisionsNewestFirst(
  revisions: readonly VersionClassificationRevision[],
): readonly VersionClassificationRevision[] {
  return [...revisions].sort((a, b) => b.revision - a.revision);
}

export type CorrectionFailureKind =
  | 'stale'
  | 'not_classified'
  | 'unchanged'
  | 'reason'
  | 'not_permitted'
  | 'not_found'
  | FailureKind;

export interface CorrectionFailure {
  readonly kind: CorrectionFailureKind;
  /** The Russian sentence a screen renders. Never a thrown value's own message. */
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
}

/** `409 classification_revision_stale`: somebody corrected after the revision the form was built on. */
export const CORRECTION_STALE_DETAIL =
  'Классификацию этой версии уже изменили, пока вы готовили исправление. Ваше исправление не ' +
  'применено и ничего не изменено; ниже показана актуальная классификация. Проверьте её и, если ' +
  'исправление всё ещё нужно, повторите.';

/** `409 version_not_classified`. */
export const CORRECTION_NOT_CLASSIFIED_DETAIL =
  'У этой версии ещё нет подтверждённых стадии и раздела, поэтому исправлять нечего. Сначала ' +
  'подтвердите их; ничего не изменено.';

/** `422 differs_from_current`. */
export const CORRECTION_UNCHANGED_DETAIL =
  'Выбранные стадия и раздел совпадают с текущими. Измените хотя бы одно из значений; ничего не ' +
  'изменено.';

/** `422` on the reason. */
export const CORRECTION_REASON_DETAIL =
  'Сервер не принял причину: она обязательна, должна содержать буквы или цифры и быть не ' +
  `длиннее ${CORRECTION_REASON_MAX_LENGTH} символов. Ничего не изменено.`;

/** `403` on the correction write: the role, not the credential, is what is missing. */
export const CORRECTION_NOT_PERMITTED_DETAIL =
  'Исправить стадию и раздел может только пользователь с ролью «Эксперт». У вашей учётной записи ' +
  'этой роли нет, поэтому ничего не изменено.';

/** Classify anything `correctVersionClassification` threw, and say it in Russian. */
export function correctionFailure(error: unknown): CorrectionFailure {
  if (error instanceof ApiError) {
    const base = { correlationId: error.correlationId, retryable: error.retryable };
    if (error.errorCode === 'conflict') {
      const reason = error.details['conflict_reason'];
      if (reason === 'classification_revision_stale') {
        return { ...base, kind: 'stale', detail: CORRECTION_STALE_DETAIL };
      }
      if (reason === 'version_not_classified') {
        return { ...base, kind: 'not_classified', detail: CORRECTION_NOT_CLASSIFIED_DETAIL };
      }
    }
    if (error.errorCode === 'validation_failed') {
      if (error.details['constraint'] === 'differs_from_current') {
        return { ...base, kind: 'unchanged', detail: CORRECTION_UNCHANGED_DETAIL };
      }
      if (error.details['field'] === 'reason') {
        return { ...base, kind: 'reason', detail: CORRECTION_REASON_DETAIL };
      }
    }
    if (error.errorCode === 'permission_denied') {
      return { ...base, kind: 'not_permitted', detail: CORRECTION_NOT_PERMITTED_DETAIL };
    }
    if (error.errorCode === 'not_found') {
      return {
        ...base,
        kind: 'not_found',
        detail:
          'Такой версии в этом документе и проекте нет. Ничего не изменено; откройте версию ' +
          'заново из списка документов проекта.',
      };
    }
  }
  const failure = failureMessage(error, {
    validation_failed:
      'Сервер не принял исправление: стадия и раздел должны быть из предложенных, причина ' +
      'обязательна. Ничего не изменено.',
  });
  return {
    kind: failure.kind,
    detail: failure.detail,
    correlationId: failure.correlationId,
    retryable: failure.retryable,
  };
}
