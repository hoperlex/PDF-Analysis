/**
 * Project presentation rules.
 *
 * Pure functions over the contract's `Project`. Nothing here calls the API and nothing
 * here formats for a particular screen: the widget decides layout, this decides meaning.
 *
 * `document_count` is optional in the contract. An absent count is **unknown**, not zero.
 * Rendering `0` for "the server did not say" is the same class of mistake as rendering a
 * recorded run as a live one: it invents a fact the response did not carry.
 */

import type { Project } from '@/shared/api';
import { PROJECT_UID_PATTERN } from '@/shared/api';

/**
 * Contract bounds on `CreateProjectRequest.name`.
 *
 * The generator emits identifier patterns but not string lengths, so these two numbers
 * are restated here and checked against `contracts/api/v1/openapi.json` by a unit test —
 * a hand-copied bound nobody compares to its source is a bound that drifts.
 */
export const PROJECT_NAME_MIN_LENGTH = 1;
export const PROJECT_NAME_MAX_LENGTH = 200;

/** Why a typed project name cannot be sent. `null` means it can. */
export type ProjectNameProblem = 'empty' | 'too_long';

/**
 * Validate a name against the contract bounds before spending a request on it.
 *
 * This is a courtesy check, never an authority: the server validates the same rule and
 * its `validation_failed` is what the screen renders if the two ever disagree.
 */
export function validateProjectName(raw: string): ProjectNameProblem | null {
  const trimmed = raw.trim();
  if (trimmed.length < PROJECT_NAME_MIN_LENGTH) return 'empty';
  if (trimmed.length > PROJECT_NAME_MAX_LENGTH) return 'too_long';
  return null;
}

/** The message for a name problem, in the user's words. */
export function projectNameProblemMessage(problem: ProjectNameProblem): string {
  switch (problem) {
    case 'empty':
      return 'Проекту нужно название.';
    case 'too_long':
      return `Название проекта — не более ${PROJECT_NAME_MAX_LENGTH} символов.`;
  }
}

/** The document count, or `null` when the response did not carry one. Never invented. */
export function projectDocumentCount(project: Project): number | null {
  return project.document_count ?? null;
}

/** How an unknown count is rendered. Distinct from the string `0`. */
export const UNKNOWN_COUNT_LABEL = '—';

/** Display text for the document count, distinguishing unknown from zero. */
export function projectDocumentCountLabel(project: Project): string {
  const count = projectDocumentCount(project);
  return count === null ? UNKNOWN_COUNT_LABEL : String(count);
}

const PROJECT_UID_RE = new RegExp(PROJECT_UID_PATTERN);

/**
 * Whether a route parameter is shaped like a project identity.
 *
 * The UI never parses a `prj_<ULID>` for meaning. This only separates "the URL is
 * malformed" from "the server says not found", so a typo does not spend a request and
 * does not render as a server failure.
 */
export function looksLikeProjectUid(value: string): boolean {
  return PROJECT_UID_RE.test(value);
}
