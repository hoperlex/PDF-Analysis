/**
 * The expert's correction of a confirmed classification (`CLASSIFICATION-CORRECTION-01`).
 *
 * What a reviewer must be able to rely on, case by case:
 *
 *   - only an expert is offered «Исправить» -- an administrator alone is not, because the API
 *     refuses `admin` alone;
 *   - the form starts from the current classification, holds its button until the pair differs
 *     from it and the reason is a real sentence, and says the correction adds a revision;
 *   - the panel names the revision it shows and lists the history newest first, each
 *     correction with its expert, time and reason, the original confirmation without one;
 *   - every refusal has its own Russian sentence and none offers an override;
 *   - the command sends one POST with the reason trimmed and the revision it was based on, and
 *     tells every read that shows a classification -- the review, the version, the version
 *     lists, the comparisons, the project structure, the dashboard and the optimisation views;
 *   - a double press sends one request.
 *
 * The static harness fires no handler, so settled states are rendered through the views, which
 * are the whole of the markup driven by props; the command is exercised through its
 * configuration, like `classify-command.test.ts`.
 */

import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({ invalidations: [] as unknown[] }));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useMutation: (configuration: unknown) => configuration,
    useQueryClient: () => ({
      invalidateQueries: (...args: unknown[]) => {
        calls.invalidations.push(args);
        return Promise.resolve();
      },
    }),
  };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, correctVersionClassification: vi.fn() };
});

import type { SectionReview, VersionClassification, VersionClassificationRevision } from '@/shared/api';
import { correctVersionClassification, queryKeys } from '@/shared/api';
import {
  CORRECTION_NOT_CLASSIFIED_DETAIL,
  CORRECTION_NOT_PERMITTED_DETAIL,
  CORRECTION_REASON_DETAIL,
  CORRECTION_REASON_MAX_LENGTH,
  CORRECTION_STALE_DETAIL,
  CORRECTION_UNCHANGED_DETAIL,
  canCorrectClassification,
  correctionFailure,
  differsFromCurrent,
  isCorrected,
  reasonProblem,
  revisionText,
  revisionsNewestFirst,
} from '@/entities/document-version';
import type { CorrectVersionClassificationCommand } from '@/features/correct-version-classification';
import {
  CorrectVersionClassificationFormView,
  createSingleFlight,
  useCorrectVersionClassification,
} from '@/features/correct-version-classification';
import { VersionClassificationView } from '@/widgets/version-classification';

import { newClient, renderWith } from '../screens/harness';
import { ADDRESS, DOCUMENT_UID, VERSION_UID, apiError, classification, review } from './fixtures';

const noop = () => undefined;
const USER_A = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const USER_B = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';

function revision(
  number: number,
  stage: 'P' | 'R',
  section: VersionClassificationRevision['section_code'],
  reason: string | null,
  actor = USER_A,
): VersionClassificationRevision {
  return {
    revision: number,
    project_stage: stage,
    section_code: section,
    actor_user_uid: actor,
    at: `2026-10-2${number}T08:00:00Z`,
    reason,
  };
}

const CORRECTED: VersionClassification = classification({
  project_stage: 'R',
  section_code: 'KJ',
  revision: 3,
  confirmed_by_user_uid: USER_B,
  confirmed_at: '2026-10-23T08:00:00Z',
});
const HISTORY = [
  revision(1, 'P', 'AR', null),
  revision(2, 'P', 'KJ', 'Раздел определён по штампу листа неверно'),
  revision(3, 'R', 'KJ', 'Это рабочая документация,\nа не проектная', USER_B),
];

function panel(props: Partial<Parameters<typeof VersionClassificationView>[0]> = {}): string {
  return renderWith(
    newClient(),
    createElement(VersionClassificationView, {
      address: ADDRESS,
      review: review({ classification: CORRECTED, revisions: HISTORY }),
      roles: ['expert'],
      conflict: false,
      onConflict: noop,
      correcting: false,
      onCorrecting: noop,
      ...props,
    }),
  );
}

/**
 * `PB-PROFILE-01`. ПБ has a draft profile now, so the API marks all fifteen options executable.
 * "A section without a profile" is what a server whose registry lacks one would answer; the state
 * is built for any section a test names (ГП here) instead of being ПБ, and `null` is the API's
 * present answer. (The shared `review()` fixture still defaults ПБ to non-executable.)
 */
function reviewWithoutProfile(
  code: SectionReview['options'][number]['section_code'] | null,
): SectionReview {
  const base = review({ classification: CORRECTED, revisions: HISTORY });
  return {
    ...base,
    options: base.options.map((option) => ({ ...option, executable: option.section_code !== code })),
  };
}

function form(props: Partial<Parameters<typeof CorrectVersionClassificationFormView>[0]> = {}): string {
  return renderWith(
    newClient(),
    createElement(CorrectVersionClassificationFormView, {
      review: review({ classification: CORRECTED, revisions: HISTORY }),
      current: CORRECTED,
      stage: 'R',
      section: 'KJ',
      reason: '',
      pending: false,
      failure: null,
      onStage: noop,
      onSection: noop,
      onReason: noop,
      onSubmit: noop,
      onCancel: noop,
      ...props,
    }),
  );
}

describe('who is offered the correction', () => {
  it('an expert sees «Исправить» next to a confirmed classification', () => {
    const markup = panel();
    expect(markup).toContain('data-classification-correct=""');
    expect(markup).toContain('Исправить');
    expect(canCorrectClassification(['expert'])).toBe(true);
  });

  it('an administrator alone is offered nothing, and neither is a reader with no role', () => {
    for (const roles of [['admin'], []] as const) {
      const markup = panel({ roles: [...roles] });
      expect(markup).not.toContain('data-classification-correct=""');
      expect(markup).not.toContain('data-classification-correction-form');
      // the history is for every reader
      expect(markup).toContain('data-classification-history="3"');
    }
    expect(canCorrectClassification(['admin'])).toBe(false);
  });

  it('draws the form only once «Исправить» was pressed', () => {
    expect(panel({ correcting: false })).not.toContain('data-classification-correction-form');
    const open = panel({ correcting: true });
    expect(open).toContain('data-classification-correction-form=""');
    expect(open).toContain('data-based-on-revision="3"');
    expect(open).not.toContain('data-classification-correct=""');
  });

  it('an unconfirmed version has no correction and no history', () => {
    const markup = panel({ review: review(), roles: ['expert'] });
    expect(markup).toContain('data-classification-state="unconfirmed"');
    expect(markup).not.toContain('data-classification-correct=""');
    expect(markup).not.toContain('data-classification-history');
  });
});

describe('the panel names the revision and lists the history', () => {
  it('says which revision it shows and that it was corrected', () => {
    const markup = panel();
    expect(markup).toContain('data-classification-revision-line="3"');
    expect(markup).toContain('Ревизия 3.');
    expect(markup).toContain('Исправлено экспертом');
    expect(markup).not.toContain('Подтверждено экспертом');
  });

  it('an uncorrected classification still reads «Подтверждено экспертом»', () => {
    const markup = panel({
      review: review({
        classification: classification(),
        revisions: [revision(1, 'P', 'AR', null)],
      }),
    });
    expect(markup).toContain('Ревизия 1.');
    expect(markup).toContain('Подтверждено экспертом');
    expect(markup).not.toContain('Исправлено экспертом');
  });

  it('lists every revision newest first, the original as a confirmation without a reason', () => {
    const markup = panel();
    const order = [...markup.matchAll(/data-classification-revision="(\d+)"/g)].map((m) => m[1]);
    expect(order).toEqual(['3', '2', '1']);
    expect(markup).toContain('data-revision-kind="confirmation"');
    expect((markup.match(/data-revision-kind="correction"/g) ?? []).length).toBe(2);
    expect((markup.match(/data-revision-reason=""/g) ?? []).length).toBe(2);
    expect(markup).toContain('Раздел определён по штампу листа неверно');
    expect(markup).toContain('Это рабочая документация,\nа не проектная');
    expect(markup).toContain('История классификации');
  });

  it('puts the original stage and section into the history, not only the latest', () => {
    const markup = panel();
    expect(markup).toContain('data-version-classification="P:AR"');
    expect(markup).toContain('data-version-classification="P:KJ"');
    expect(markup).toContain('data-version-classification="R:KJ"');
  });

  it('orders by revision number, whatever order the API listed them in', () => {
    expect(revisionsNewestFirst([HISTORY[0]!, HISTORY[2]!, HISTORY[1]!]).map((e) => e.revision)).toEqual([3, 2, 1]);
    expect(isCorrected(classification())).toBe(false);
    expect(isCorrected(CORRECTED)).toBe(true);
    expect(revisionText(2)).toBe('Ревизия 2');
  });
});

describe('the correction form', () => {
  it('starts from the current stage and section and says a revision will be added', () => {
    const markup = form();
    expect(markup).toContain('data-based-on-revision="3"');
    expect(markup).toContain('Ревизия 4');
    expect(markup).toContain('прежние ревизии');
    expect(markup).toMatch(/data-correction-stage="R"[^>]*checked=""|checked=""[^>]*data-correction-stage="R"/);
    expect(markup).toContain('<option value="KJ" selected');
    expect((markup.match(/<option /g) ?? []).length).toBe(15);
  });

  it('says that started runs keep their profile and a re-audit applies the correction', () => {
    const markup = form();
    expect(markup).toContain('Уже запущенные прогоны сохраняют профиль анализа');
    expect(markup).toContain('перезапустите анализ версии');
  });

  it('holds the button while the pair equals the current one, and says why', () => {
    const markup = form({ reason: 'Причина есть' });
    expect(markup).toMatch(/data-correction-submit=""[^>]*disabled=""/);
    expect(markup).toContain('data-correction-unchanged=""');
  });

  it('holds the button while the reason is blank, punctuation only or too long', () => {
    for (const reason of ['', '   ', '...', '​']) {
      expect(form({ stage: 'P', reason })).toMatch(/data-correction-submit=""[^>]*disabled=""/);
    }
    const tooLong = form({ stage: 'P', reason: 'а'.repeat(CORRECTION_REASON_MAX_LENGTH + 1) });
    expect(tooLong).toMatch(/data-correction-submit=""[^>]*disabled=""/);
    expect(tooLong).toContain('data-correction-reason-problem="too_long"');
    expect(form({ stage: 'P', reason: '...' })).toContain('data-correction-reason-problem="required"');
  });

  it('enables the button for a changed pair with a real reason', () => {
    const markup = form({ stage: 'P', reason: 'Лист относится к проектной документации' });
    expect(markup).not.toMatch(/data-correction-submit=""[^>]*disabled=""/);
    expect(markup).not.toContain('data-correction-unchanged');
    expect(markup).not.toContain('data-correction-reason-problem');
  });

  it('shows no problem for a reason that was not typed yet', () => {
    expect(form({ stage: 'P', reason: '' })).not.toContain('data-correction-reason-problem');
  });

  it('is disabled and says so while the request is in flight', () => {
    const markup = form({ stage: 'P', reason: 'Причина', pending: true });
    expect(markup).toContain('сохранение исправления');
    expect(markup).toMatch(/data-correction-submit=""[^>]*disabled=""/);
    expect(markup).toMatch(/data-correction-cancel=""[^>]*disabled=""/);
  });

  it('marks the sections without a profile and keeps them choosable', () => {
    const markup = form({ review: reviewWithoutProfile('GP') });
    expect(markup).toMatch(/<option value="GP"[^>]*>[^<]*профиль анализа недоступен/);
    expect(markup).not.toMatch(/<option value="GP"[^>]*disabled/);
    // Only that one: ПБ has a profile.
    expect(markup).toMatch(/<option value="PB"[^>]*>/);
    expect(markup).not.toMatch(/<option value="PB"[^>]*>[^<]*профиль анализа недоступен/);
    expect((markup.match(/профиль анализа недоступен/g) ?? []).length).toBe(1);
  });

  it('marks nothing when every section has a profile, ПБ included', () => {
    const markup = form({ review: reviewWithoutProfile(null) });
    expect(markup).toMatch(/<option value="PB"[^>]*>/);
    expect(markup).not.toContain('профиль анализа недоступен');
  });
});

describe('every refusal has its own sentence and none offers an override', () => {
  it('maps each server answer to its kind', () => {
    const stale = correctionFailure(apiError(409, 'conflict', { conflict_reason: 'classification_revision_stale' }));
    expect(stale.kind).toBe('stale');
    expect(stale.detail).toBe(CORRECTION_STALE_DETAIL);
    expect(correctionFailure(apiError(409, 'conflict', { conflict_reason: 'version_not_classified' })).detail).toBe(
      CORRECTION_NOT_CLASSIFIED_DETAIL,
    );
    expect(
      correctionFailure(apiError(422, 'validation_failed', { field: 'section_code', constraint: 'differs_from_current' })),
    ).toMatchObject({ kind: 'unchanged', detail: CORRECTION_UNCHANGED_DETAIL });
    expect(
      correctionFailure(apiError(422, 'validation_failed', { field: 'reason', constraint: 'required' })),
    ).toMatchObject({ kind: 'reason', detail: CORRECTION_REASON_DETAIL });
    expect(correctionFailure(apiError(403, 'permission_denied'))).toMatchObject({
      kind: 'not_permitted',
      detail: CORRECTION_NOT_PERMITTED_DETAIL,
    });
    expect(correctionFailure(apiError(404, 'not_found')).kind).toBe('not_found');
  });

  it('an unrelated conflict or failure is read by the shared wording, not as a stale correction', () => {
    expect(correctionFailure(apiError(409, 'conflict', { conflict_reason: 'something_else' })).kind).not.toBe('stale');
    expect(correctionFailure(apiError(503, 'dependency_unavailable')).kind).not.toBe('stale');
    expect(correctionFailure(new Error('network down')).detail).not.toContain('network down');
  });

  it('renders the failure under the form with its correlation id and no way around it', () => {
    const failure = correctionFailure(
      apiError(409, 'conflict', { conflict_reason: 'classification_revision_stale' }),
    );
    const markup = form({ stage: 'P', reason: 'Причина', failure });
    expect(markup).toContain('data-correction-failure="stale"');
    expect(markup).toContain(CORRECTION_STALE_DETAIL);
    expect(markup).toContain('cid-section');
    expect(markup).not.toMatch(/принудительно|всё равно|перезаписать/i);
  });
});

describe('the reason before it is sent', () => {
  it('needs a letter or a digit and at most the documented length', () => {
    expect(CORRECTION_REASON_MAX_LENGTH).toBe(2000);
    expect(reasonProblem('')).toBe('required');
    expect(reasonProblem('  \n ')).toBe('required');
    expect(reasonProblem('.,;')).toBe('required');
    expect(reasonProblem('1')).toBeNull();
    expect(reasonProblem('а')).toBeNull();
    expect(reasonProblem(`  ${'а'.repeat(2000)}  `)).toBeNull();
    expect(reasonProblem('а'.repeat(2001))).toBe('too_long');
  });

  it('counts characters, not UTF-16 units', () => {
    expect(reasonProblem('😀'.repeat(2000) + 'а'.repeat(0) + 'a')).toBe('too_long');
    expect(reasonProblem(`а${'😀'.repeat(1999)}`)).toBeNull();
  });

  it('a pair differs from the current one when either value does', () => {
    const current = { project_stage: 'R', section_code: 'KJ' } as const;
    expect(differsFromCurrent(current, 'R', 'KJ')).toBe(false);
    expect(differsFromCurrent(current, 'P', 'KJ')).toBe(true);
    expect(differsFromCurrent(current, 'R', 'AR')).toBe(true);
    expect(differsFromCurrent(current, null, 'AR')).toBe(false);
  });
});

type Captured = {
  mutationFn: (input: CorrectVersionClassificationCommand) => Promise<VersionClassification>;
  onSuccess: (result: VersionClassification, input: CorrectVersionClassificationCommand) => void;
  onError: (error: unknown, input: CorrectVersionClassificationCommand) => void;
  retry: boolean;
};

const COMMAND: CorrectVersionClassificationCommand = {
  ...ADDRESS,
  stage: 'P',
  section: 'KJ',
  reason: '  Раздел определён неверно \n',
  expectedRevision: 3,
};

beforeEach(() => {
  calls.invalidations.length = 0;
  vi.clearAllMocks();
});

describe('the correction command', () => {
  it('sends one POST with the reason trimmed and the revision it was based on, and never retries', async () => {
    vi.mocked(correctVersionClassification).mockResolvedValue({ data: CORRECTED } as never);
    const command = useCorrectVersionClassification() as unknown as Captured;
    expect(command.retry).toBe(false);
    expect(await command.mutationFn(COMMAND)).toEqual(CORRECTED);
    expect(vi.mocked(correctVersionClassification).mock.calls).toEqual([
      [
        {
          path: {
            project_uid: ADDRESS.projectUid,
            document_uid: ADDRESS.documentUid,
            version_uid: ADDRESS.versionUid,
          },
          body: {
            project_stage: 'P',
            section_code: 'KJ',
            reason: 'Раздел определён неверно',
            expected_revision: 3,
          },
        },
      ],
    ]);
  });

  it('on success tells every read that shows a classification', () => {
    const command = useCorrectVersionClassification() as unknown as Captured;
    command.onSuccess(CORRECTED, COMMAND);
    const keys = calls.invalidations.map((args) => (args as [{ queryKey: unknown }])[0].queryKey);
    expect(keys).toEqual([
      queryKeys.versions.sectionReview(VERSION_UID),
      queryKeys.versions.detail(VERSION_UID),
      queryKeys.versions.lists(DOCUMENT_UID),
      queryKeys.versions.comparisons(),
      queryKeys.projects.all(),
      queryKeys.dashboard.summary(),
      queryKeys.optimisation.all(),
    ]);
  });

  it('on a stale or unclassified refusal, reads the stored classification back', () => {
    const command = useCorrectVersionClassification() as unknown as Captured;
    command.onError(apiError(409, 'conflict', { conflict_reason: 'classification_revision_stale' }), COMMAND);
    command.onError(apiError(409, 'conflict', { conflict_reason: 'version_not_classified' }), COMMAND);
    expect(calls.invalidations).toEqual([
      [{ queryKey: queryKeys.versions.sectionReview(VERSION_UID) }],
      [{ queryKey: queryKeys.versions.detail(VERSION_UID) }],
      [{ queryKey: queryKeys.versions.sectionReview(VERSION_UID) }],
      [{ queryKey: queryKeys.versions.detail(VERSION_UID) }],
    ]);
  });

  it('on any other refusal, changes no cache at all', () => {
    const command = useCorrectVersionClassification() as unknown as Captured;
    command.onError(apiError(403, 'permission_denied'), COMMAND);
    command.onError(apiError(422, 'validation_failed', { field: 'reason', constraint: 'required' }), COMMAND);
    command.onError(apiError(503, 'dependency_unavailable'), COMMAND);
    expect(calls.invalidations).toEqual([]);
  });
});

describe('one press, one request', () => {
  it('refuses a second press while the first is in flight and reopens afterwards', async () => {
    const flight = createSingleFlight();
    let release: () => void = noop;
    const first = flight.run(() => new Promise<void>((resolve) => (release = resolve)));
    expect(first).toBe(true);
    expect(flight.busy).toBe(true);
    expect(flight.run(() => Promise.resolve())).toBe(false);
    release();
    await Promise.resolve();
    await Promise.resolve();
    expect(flight.busy).toBe(false);
    expect(flight.run(() => Promise.resolve())).toBe(true);
  });
});
