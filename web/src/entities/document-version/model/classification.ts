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
 * `409 conflict` with `conflict_reason: version_already_classified` and changes nothing:
 * there is no correction workflow yet, so the screen shows the stored classification as
 * «уже подтверждено другим решением» and offers no override.
 */

import type {
  ProjectSection as SectionCode,
  ProjectStage,
  Role,
  SectionReviewOption,
  SectionSuggestion,
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
  'ничего не изменено; исправить подтверждённую классификацию пока нельзя.';

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
