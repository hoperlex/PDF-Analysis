/**
 * The critic's advice for a finding that stands on portal blocks, from the run's saved extended review (`F8-WEB`, plan v5 section 4.5).
 *
 * A block finding is published from a candidate of the extended review (`finding_observation.extended_observation_ref` names the
 * candidate). The sealed ref is authoritative. Older responses without it can be recognised by the two things the publisher
 * copied, but only when those name exactly one candidate:
 *
 *   - the finding's text is the candidate's words, as the publisher wrote them (`_candidate_words` in `runs/extended_review.py`:
 *     the description, or the title over the description);
 *   - every block of the finding is one of the candidate's `source_ids` (a block's id is the source's id).
 *
 * Exactly one candidate must satisfy both. A present but unresolved ref never falls back to matching words.
 *
 * The advice is a machine's recommendation and never an expert's decision (AGENTS section 4); the words say so.
 */

import { EXTENDED_ADVICE } from '@/entities/audit-run';

type RecordValue = Record<string, unknown>;

function object(value: unknown): RecordValue | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as RecordValue) : null;
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

/** What the card needs of a finding to find its candidate. */
export interface AdviceSubject {
  readonly findingText: string;
  readonly blockIds: readonly string[];
  readonly observationRef?: string | undefined;
}

/**
 * A candidate's words as the publisher wrote them into the finding: the description, or the title over the description when the
 * description does not start with it. Mirrors `_candidate_words`; `null` when the candidate has neither.
 */
export function candidateWords(candidate: RecordValue): string | null {
  const title = text(candidate.title).trim();
  const description = text(candidate.description).trim();
  const words = title === '' || description.startsWith(title) ? description : description === '' ? title : `${title}\n\n${description}`;
  return words === '' ? null : words;
}

function sourceIds(candidate: RecordValue): readonly string[] {
  return Array.isArray(candidate.source_ids) ? candidate.source_ids.filter((id): id is string => typeof id === 'string') : [];
}

/**
 * The one candidate of the saved review a block finding was published from, or `null` when none or more than one fits.
 * `result` is the review's `result` as the API returns it (untyped).
 */
export function candidateOfFinding(result: unknown, subject: AdviceSubject): RecordValue | null {
  const rows = object(result)?.observations;
  if (!Array.isArray(rows)) return null;
  if (subject.observationRef !== undefined) {
    const exact = rows.flatMap((row) => {
      const candidate = object(row);
      return candidate?.observation_id === subject.observationRef ? [candidate] : [];
    });
    return exact.length === 1 ? exact[0] ?? null : null;
  }
  if (subject.blockIds.length === 0 || subject.findingText === '') return null;
  const fitting = rows.flatMap((row) => {
    const candidate = object(row);
    if (candidate === null || candidateWords(candidate) !== subject.findingText) return [];
    const sources = new Set(sourceIds(candidate));
    return subject.blockIds.every((id) => sources.has(id)) ? [candidate] : [];
  });
  return fitting.length === 1 ? (fitting[0] ?? null) : null;
}

/** The critic's word on one candidate, ready to be said in one line. */
export interface CandidateAdvice {
  /** `llm_decision` as the critic gave it: accept, reject, borderline, needs_human or rewrite. */
  readonly decision: string;
  /** The words of {@link EXTENDED_ADVICE} for it. */
  readonly label: string;
  /** A rule of the original's critic (no model), or a model. */
  readonly mode: 'rules' | 'model';
  /** The critic's explanation shortened to one line; empty when it gave none. */
  readonly explanation: string;
}

/** An explanation is cut at its first sentence, and at this many characters at most: the card draws it on one line and the title carries all of it. */
export const ADVICE_EXPLANATION_LIMIT = 140;

function oneLine(explanation: string): string {
  const flat = explanation.replace(/\s+/g, ' ').trim();
  const end = flat.search(/[.!?](\s|$)/);
  const sentence = end < 0 ? flat : flat.slice(0, end + 1);
  if (sentence.length <= ADVICE_EXPLANATION_LIMIT) return sentence;
  return `${sentence.slice(0, ADVICE_EXPLANATION_LIMIT - 1).trimEnd()}…`;
}

/**
 * The critic's advice for a block finding: what its candidate's critic recommended, or `null` when the review holds no candidate
 * for it, the critic did not review it, or gave no recommendation this screen knows the words of.
 */
export function adviceForFinding(result: unknown, subject: AdviceSubject): CandidateAdvice | null {
  const candidate = candidateOfFinding(result, subject);
  if (candidate === null) return null;
  const critic = object(candidate.review ?? candidate.critic);
  const decision = text(critic?.llm_decision).trim();
  const label = Object.hasOwn(EXTENDED_ADVICE, decision) ? EXTENDED_ADVICE[decision] : undefined;
  if (critic === null || label === undefined) return null;
  return { decision, label, mode: critic.mode === 'deterministic' ? 'rules' : 'model', explanation: oneLine(text(critic.explanation)) };
}

/** The one line the card says: «Совет критика: рекомендует снять наблюдение — …». */
export function adviceLine(advice: CandidateAdvice): string {
  const head = advice.mode === 'rules' ? 'Правила критика (без модели)' : 'Совет критика';
  const words = advice.label.charAt(0).toLocaleLowerCase('ru') + advice.label.slice(1);
  return advice.explanation === '' ? `${head}: ${words}` : `${head}: ${words} — ${advice.explanation}`;
}
