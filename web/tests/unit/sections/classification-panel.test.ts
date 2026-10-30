/**
 * The version screen's stage-and-section panel (`W59-SECTION-UI-01`).
 *
 * What a reviewer must be able to rely on, case by case:
 *
 *   - an expert facing an unconfirmed version gets the form: both stages, all fifteen
 *     sections, the suggested ones first with the evidence that suggested them, a section
 *     without a profile marked, and nothing pre-selected;
 *   - anyone else gets one read-only sentence and no control — an administrator too, because
 *     the API refuses `admin` alone;
 *   - a confirmed version shows its badges, and «профиль анализа недоступен» exactly when the
 *     review says its section has no profile;
 *   - `409 version_already_classified` shows the stored classification as «уже подтверждено
 *     другим решением», and `403` a role sentence — never an override;
 *   - a double press sends one request.
 *
 * The static harness renders one pass and fires no handler (`../screens/harness.ts`), so the
 * mutation's settled states are rendered through `ClassifyVersionFormView`, which is the
 * whole of the form's markup driven by props, and the one-request rule is proved on the gate
 * the form presses through.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { SectionReview } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import {
  ALREADY_CLASSIFIED_DETAIL,
  CLASSIFY_NOT_PERMITTED_DETAIL,
  canClassifyVersion,
  classificationFailure,
  orderSectionOptions,
  stageBadgeText,
} from '@/entities/document-version';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import { ClassifyVersionFormView, createSingleFlight } from '@/features/classify-version';
import { VersionClassification, VersionClassificationView } from '@/widgets/version-classification';
import { VersionDetailPage } from '@/_pages/version-detail';

import { newClient, renderScreen, renderWith, seedError } from '../screens/harness';
import { ADDRESS, PROJECT_UID, VERSION_UID, apiError, classification, review, version } from './fixtures';

const noop = () => undefined;

function view(props: Partial<Parameters<typeof VersionClassificationView>[0]> = {}): string {
  return renderWith(
    newClient(),
    createElement(VersionClassificationView, {
      address: ADDRESS,
      review: review(),
      roles: ['expert'],
      conflict: false,
      onConflict: noop,
      ...props,
    }),
  );
}

function form(props: Partial<Parameters<typeof ClassifyVersionFormView>[0]> = {}): string {
  return renderWith(
    newClient(),
    createElement(ClassifyVersionFormView, {
      review: review(),
      stage: null,
      section: null,
      pending: false,
      failure: null,
      onStage: noop,
      onSection: noop,
      onConfirm: noop,
      ...props,
    }),
  );
}

/**
 * `PB-PROFILE-01`. ПБ has a draft profile now, so the API marks all fifteen options executable.
 * "A section without a profile" is what a server whose registry lacks one would answer; that
 * state is built for any section a test names (ГП here) instead of being ПБ, as it used to be,
 * and `null` is the API's present answer: every option executable.
 */
function reviewWithoutProfile(
  code: SectionReview['options'][number]['section_code'] | null,
  overrides: Partial<SectionReview> = {},
): SectionReview {
  const base = review(overrides);
  return {
    ...base,
    options: base.options.map((option) => ({ ...option, executable: option.section_code !== code })),
  };
}

/** The `data-section-option` codes, in the order the markup lists them. */
function optionOrder(markup: string): string[] {
  return [...markup.matchAll(/data-section-option="([A-Z]+)"/g)].map((m) => m[1] as string);
}

describe('an expert facing an unconfirmed version gets the form', () => {
  it('draws the form, not the read-only sentence', () => {
    const markup = view();
    expect(markup).toContain('data-classification-state="unconfirmed"');
    expect(markup).toContain('data-classification-form=""');
    expect(markup).not.toContain('Раздел ещё не подтверждён экспертом');
  });

  it('offers both stages in Russian, with nothing chosen', () => {
    const markup = form();
    expect(markup).toContain('П — проектная');
    expect(markup).toContain('Р — рабочая');
    expect(markup).toContain('data-stage-choice="P"');
    expect(markup).toContain('data-stage-choice="R"');
    expect(markup).not.toContain('checked=""');
  });

  it('offers all fifteen sections, suggested first by score, the rest in the S-5 order', () => {
    const order = optionOrder(form());
    expect(order).toHaveLength(15);
    expect(new Set(order).size).toBe(15);
    // KJ scores 9; AR and KM tie at 4 and keep the structure order (AR before KM).
    expect(order.slice(0, 3)).toEqual(['KJ', 'AR', 'KM']);
    expect(order.slice(3)).toEqual(['AI', 'PS', 'POS', 'TX', 'OV', 'VK', 'PT', 'EOM', 'SS', 'ITP', 'GP', 'PB']);
    expect(form()).toContain('data-suggested-count="3"');
  });

  it('shows the evidence behind each suggestion, and none for the rest', () => {
    const markup = form();
    expect(markup).toContain('В имени файла:');
    expect(markup).toContain('<code>КЖ</code>');
    expect(markup).toContain('<code>-KJ</code>');
    expect(markup).toContain('В тексте: армирование');
    expect(markup).toContain('В тексте: поэтажный план');
    expect(markup).toContain('Название раздела встречается в тексте.');
    expect((markup.match(/data-suggestion-score=/g) ?? []).length).toBe(3);
  });

  it('marks a section without a profile and keeps it choosable', () => {
    const markup = form({ review: reviewWithoutProfile('GP') });
    const gp = /<label[^>]*data-section-option="GP"[\s\S]*?<\/label>/.exec(markup)?.[0] ?? '';
    expect(gp).toContain('data-executable="false"');
    expect(gp).toContain('профиль анализа недоступен');
    expect(gp).not.toContain('disabled=""');
    expect((markup.match(/data-profile-unavailable=""/g) ?? []).length).toBe(1);
    // ...and only that one: ПБ has a profile.
    const pb = /<label[^>]*data-section-option="PB"[\s\S]*?<\/label>/.exec(markup)?.[0] ?? '';
    expect(pb).toContain('data-executable="true"');
    expect(pb).not.toContain('профиль анализа недоступен');
  });

  it('marks nothing when every section has a profile, ПБ included', () => {
    const markup = form({ review: reviewWithoutProfile(null) });
    const pb = /<label[^>]*data-section-option="PB"[\s\S]*?<\/label>/.exec(markup)?.[0] ?? '';
    expect(pb).toContain('data-executable="true"');
    expect(pb).not.toContain('профиль анализа недоступен');
    expect(markup).not.toContain('data-profile-unavailable=""');
    expect(markup).not.toContain('профиль анализа недоступен');
  });

  it('says when nothing was suggested, and when the recognised text was not read', () => {
    const markup = form({
      review: review({
        recognised_text_consulted: false,
        options: review().options.map((option) => ({ ...option, suggestion: null })),
      }),
    });
    expect(markup).toContain('data-suggested-count="0"');
    expect(markup).toContain('Выберите его сами');
    expect(markup).toContain('data-recognised-text="not-consulted"');
    expect(optionOrder(markup)[0]).toBe('AR');
  });

  it('holds the confirm button until both a stage and a section are chosen', () => {
    const button = (markup: string) =>
      /<button[^>]*data-classification-confirm=""[^>]*>/.exec(markup)?.[0] ?? '';
    expect(button(form())).toContain('disabled=""');
    expect(button(form({ stage: 'P' }))).toContain('disabled=""');
    expect(button(form({ section: 'AR' }))).toContain('disabled=""');
    expect(button(form({ stage: 'P', section: 'AR' }))).not.toContain('disabled=""');
    expect(form()).toContain('>Подтвердить раздел</button>');
  });

  it('disables every control while the request is in flight', () => {
    const markup = form({
      stage: 'R', section: 'GP', pending: true, review: reviewWithoutProfile('GP'),
    });
    expect(/<button[^>]*data-classification-confirm=""[^>]*disabled=""/.test(markup)).toBe(true);
    expect((markup.match(/<input[^>]*disabled=""/g) ?? []).length).toBe(17);
    expect(markup).toContain('Загрузка: подтверждение стадии и раздела…');
    // A chosen section without a profile says what a run over it will meet.
    expect(markup).toContain('data-chosen-profile="unavailable"');
  });

  it('says nothing about a missing profile for a chosen ПБ: it has one', () => {
    const markup = form({ stage: 'R', section: 'PB', review: reviewWithoutProfile(null) });
    expect(markup).not.toContain('data-chosen-profile="unavailable"');
  });

  it('offers a chosen АР as an executable text profile', () => {
    const markup = form({ stage: 'P', section: 'AR', review: review() });
    expect(markup).not.toContain('data-chosen-profile="unavailable"');
    expect(markup).not.toContain('группой из шести проверок АР v3');
    const other = form({ stage: 'R', section: 'GP', review: reviewWithoutProfile('GP') });
    expect(other).toContain('пока профиль не появится');
  });
});

describe('anyone who is not an expert reads, and is offered nothing', () => {
  it('draws one sentence for a session with no expert role, an administrator included', () => {
    for (const roles of [['admin'], []] as const) {
      const markup = view({ roles });
      expect(markup).toContain('data-classification-state="read-only"');
      expect(markup).toContain('Раздел ещё не подтверждён экспертом.');
      expect(markup).not.toContain('<form');
      expect(markup).not.toContain('<input');
      expect(markup).not.toContain('<button');
    }
  });

  it('is the same rule the API applies: expert, and admin alone is not enough', () => {
    expect(canClassifyVersion(['expert'])).toBe(true);
    expect(canClassifyVersion(['admin', 'expert'])).toBe(true);
    expect(canClassifyVersion(['admin'])).toBe(false);
    expect(canClassifyVersion([])).toBe(false);
  });
});

describe('a confirmed version shows its stage and section', () => {
  it('renders the two badges in Russian, the machine values in data- attributes', () => {
    const markup = view({ review: review({ classification: classification() }) });
    expect(markup).toContain('data-classification-state="confirmed"');
    expect(markup).toContain('Стадия: П');
    expect(markup).toContain('Архитектурные решения (АР)');
    expect(markup).toContain('data-project-stage="P"');
    expect(markup).toContain('data-section-code="AR"');
    expect(markup).toContain('data-version-classification="P:AR"');
    expect(markup).toContain('usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F');
    expect(markup).not.toContain('<form');
    expect(markup).not.toContain('профиль анализа недоступен');
  });

  it('shows a confirmed classification to a non-expert the same way', () => {
    const markup = view({ roles: ['admin'], review: review({ classification: classification() }) });
    expect(markup).toContain('data-classification-state="confirmed"');
    expect(markup).not.toContain('Раздел ещё не подтверждён экспертом');
  });

  it('adds «профиль анализа недоступен» exactly when the review says so', () => {
    const markup = view({
      review: reviewWithoutProfile('GP', {
        classification: classification({ project_stage: 'R', section_code: 'GP' }),
      }),
    });
    expect(markup).toContain('Стадия: Р');
    expect(markup).toContain('Генеральный план (ГП)');
    expect(markup).toContain('профиль анализа недоступен');
    expect(markup).toContain('data-profile-unavailable-note=""');
    // The note refuses a substitute, and never names one.
    expect(markup).toContain('Анализ по другому разделу вместо него не запускается.');
    expect(markup).not.toContain('АР');
  });

  it('shows a confirmed АР version without a missing-profile note', () => {
    const markup = view({
      review: review({
        classification: classification({ project_stage: 'P', section_code: 'AR' }),
      }),
    });
    expect(markup).not.toContain('data-profile-unavailable-note=""');
    expect(markup).not.toContain('data-profile-unavailable-section="AR"');
  });

  it('adds no note to a confirmed ПБ version: it has a profile now', () => {
    const markup = view({
      review: reviewWithoutProfile(null, {
        classification: classification({ project_stage: 'R', section_code: 'PB' }),
      }),
    });
    expect(markup).toContain('Стадия: Р');
    expect(markup).toContain('Пожарная безопасность (ПБ)');
    expect(markup).not.toContain('профиль анализа недоступен');
    expect(markup).not.toContain('data-profile-unavailable-note=""');
  });

  it('carries the document identity the journey captures', () => {
    expect(view({ review: review({ classification: classification() }) })).toContain(
      `data-classified-document="${ADDRESS.documentUid}"`,
    );
  });
});

describe('a refusal shows what is stored or who may act, and offers no override', () => {
  it('409: shows the stored classification as another decision, without the form', () => {
    const markup = view({
      conflict: true,
      review: review({ classification: classification({ project_stage: 'R', section_code: 'KJ' }) }),
    });
    expect(markup).toContain('data-classification-conflict=""');
    expect(markup).toContain('уже подтверждены другим решением');
    expect(markup).toContain('Конструкции железобетонные (КЖ)');
    expect(markup).not.toContain('<form');
  });

  it('409: is classified by its conflict reason, not by its status alone', () => {
    const stored = classificationFailure(
      apiError(409, 'conflict', { conflict_reason: 'version_already_classified' }),
    );
    expect(stored.kind).toBe('already_classified');
    expect(stored.detail).toBe(ALREADY_CLASSIFIED_DETAIL);
    // Another conflict reason is a plain conflict, not this one.
    expect(classificationFailure(apiError(409, 'conflict', { conflict_reason: 'other' })).kind).toBe('conflict');
  });

  it('403: says only an expert may confirm, and renders it on the form', () => {
    const failure = classificationFailure(
      apiError(403, 'permission_denied', { required_capability: 'role:expert' }),
    );
    expect(failure.kind).toBe('not_permitted');
    expect(failure.detail).toBe(CLASSIFY_NOT_PERMITTED_DETAIL);
    const markup = form({ stage: 'P', section: 'AR', failure });
    expect(markup).toContain('data-classification-failure="not_permitted"');
    expect(markup).toContain('ролью «Эксперт»');
    expect(markup).toContain('cid-section');
  });

  it('409 on the form: the failure line carries the stored-decision sentence', () => {
    const failure = classificationFailure(
      apiError(409, 'conflict', { conflict_reason: 'version_already_classified' }),
    );
    const markup = form({ stage: 'P', section: 'AR', failure });
    expect(markup).toContain('data-classification-failure="already_classified"');
    expect(markup).toContain('ничего не изменено');
  });

  it('404 and everything else get their own Russian reading, never a thrown message', () => {
    expect(classificationFailure(apiError(404, 'not_found')).kind).toBe('not_found');
    const unknown = classificationFailure(new Error('boom: /var/secret'));
    expect(unknown.kind).toBe('unexpected');
    expect(unknown.detail).not.toContain('boom');
  });
});

describe('a double press sends one request', () => {
  it('refuses a second run while the first is in flight, and reopens when it settles', async () => {
    const flight = createSingleFlight();
    let settle: () => void = noop;
    let calls = 0;
    const send = () => {
      calls += 1;
      return new Promise<void>((resolve) => {
        settle = resolve;
      });
    };

    expect(flight.run(send)).toBe(true);
    expect(flight.run(send)).toBe(false);
    expect(flight.busy).toBe(true);
    expect(calls).toBe(1);

    settle();
    await Promise.resolve();
    await Promise.resolve();
    expect(flight.busy).toBe(false);
    expect(flight.run(send)).toBe(true);
    expect(calls).toBe(2);
  });

  it('reopens after a refusal too, so a fixed choice can be sent again', async () => {
    const flight = createSingleFlight();
    flight.run(() => Promise.reject(new Error('refused')));
    await Promise.resolve();
    await Promise.resolve();
    expect(flight.busy).toBe(false);
  });
});

describe('the ordering never picks a section', () => {
  it('keeps every option and moves only the suggested ones forward', () => {
    const ordered = orderSectionOptions(review().options);
    expect(ordered.suggested.length + ordered.rest.length).toBe(15);
    expect(ordered.rest.every((option) => option.suggestion === null)).toBe(true);
  });

  it('words the stage badge with the Cyrillic mark', () => {
    expect(stageBadgeText('P')).toBe('Стадия: П');
    expect(stageBadgeText('R')).toBe('Стадия: Р');
  });
});

describe('the panel on the version screen', () => {
  it('reads the review at the address the version names, and says when it cannot', () => {
    const client = newClient();
    seedError(client, queryKeys.versions.sectionReview(VERSION_UID), apiError(503, 'dependency_unavailable'));
    const markup = renderWith(
      client,
      createElement(VersionClassification, { address: ADDRESS, roles: ['expert'] }),
    );
    expect(markup).toContain('id="version-classification"');
    expect(markup).toContain('Стадию и раздел этой версии не удалось прочитать.');
    expect(markup).toContain('data-classification-read-failure="dependency_unavailable"');
  });

  it('is drawn under the version, the form for an expert and the sentence for anyone else', () => {
    const seeded = () => {
      const client = newClient();
      client.setQueryData(queryKeys.versions.detail(VERSION_UID), version());
      client.setQueryData(queryKeys.versions.sectionReview(VERSION_UID), review());
      return client;
    };
    const expert = renderScreen(
      seeded(),
      createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'] }),
    );
    expect(expert).toContain('<h2>Стадия и раздел</h2>');
    expect(expert).toContain('data-classification-form=""');
    const admin = renderScreen(
      seeded(),
      createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['admin'] }),
    );
    expect(admin).toContain('data-classification-state="read-only"');
    expect(admin).not.toContain('data-classification-form=""');
  });

  it('hands both АР and another confirmed section to the ordinary Run start', () => {
    const withSection = (code: 'AR' | 'KJ') => {
      const client = newClient();
      client.setQueryData(
        queryKeys.versions.detail(VERSION_UID),
        version({ classification: classification({ section_code: code }) }),
      );
      client.setQueryData(queryKeys.versions.sectionReview(VERSION_UID), review());
      client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
        items: [], page: { next_cursor: null },
      });
      return renderScreen(
        client,
        createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'] }),
      );
    };
    const ar = withSection('AR');
    expect(ar).toContain('data-start-run-control');
    expect(ar).not.toContain('data-ar-start-note');
    const kj = withSection('KJ');
    expect(kj).toContain('data-start-run-control');
    expect(kj).not.toContain('data-ar-start-note');
  });

  it('waits for the version before it asks for the review', () => {
    const client = newClient();
    const markup = renderScreen(
      client,
      createElement(VersionDetailPage, { projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'] }),
    );
    expect(markup).not.toContain('Стадия и раздел');
    expect(client.getQueryCache().find({ queryKey: queryKeys.versions.sectionReview(VERSION_UID) })).toBeUndefined();
  });
});
