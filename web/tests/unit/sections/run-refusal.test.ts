/**
 * A run refused because of the version's section (`W59-SECTION-UI-01`).
 *
 * Since `W59-SECTION-SEAL-01` `startRun` and `reauditRun` route the analysis profile from the
 * version's confirmed classification and refuse before any run exists:
 * `422 required_norm_unavailable` with `reference_kind` `version_classification` (nothing is
 * confirmed) or `analysis_profile` (the confirmed section has no profile). The control must
 * say which, link to the version's stage-and-section panel, and offer neither a retry nor
 * another section — in particular never the АР profile it used to apply to everything.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

const settled = vi.hoisted(() => ({ error: null as unknown }));

// The control reads its refusal off its mutation; a static render cannot settle one, so the
// mutation hook answers with the refusal this file puts in `settled`.
vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useMutation: () => ({ mutate: () => {}, isPending: false, error: settled.error }),
    useQueryClient: () => ({ setQueryData: () => {}, invalidateQueries: () => Promise.resolve() }),
  };
});

import { catalogMessage } from '@/shared/api';
import { routes } from '@/shared/lib';
import {
  SECTION_PROFILE_UNAVAILABLE_REFUSAL,
  VERSION_UNCLASSIFIED_REFUSAL,
  classifyRunFailure,
  routingRefusal,
} from '@/entities/audit-run';
import { executionFailure } from '@/entities/execution';
import { StartRunControl } from '@/features/start-run';

import { PROJECT_UID, VERSION_UID, apiError } from './fixtures';

const unclassified = () =>
  apiError(422, 'required_norm_unavailable', { reference_kind: 'version_classification' });
const noProfile = () => apiError(422, 'required_norm_unavailable', { reference_kind: 'analysis_profile' });

function control(error: unknown): string {
  settled.error = error;
  return renderToStaticMarkup(
    createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID }),
  );
}

/**
 * Every wording a reader could take as a substitute being offered: the АР mark as a word of
 * its own, the architecture section by name, a default, or a run started «instead». Case
 * sensitive on purpose — `ар` inside «зарегистрирован» is not the mark.
 */
function offersASubstitute(text: string): boolean {
  return /(?<![А-ЯЁа-яё])АР(?![А-ЯЁа-яё])|[Аа]рхитектур|по умолчанию|вместо этого запущ|запустить по разделу/.test(
    text,
  );
}

describe('the substitute detector can fail', () => {
  it('finds the АР mark, the architecture name and a default, and not a word that merely contains «ар»', () => {
    expect(offersASubstitute('Запустить по разделу АР?')).toBe(true);
    expect(offersASubstitute('Будет использован профиль Архитектурные решения.')).toBe(true);
    expect(offersASubstitute('Используется профиль по умолчанию.')).toBe(true);
    expect(offersASubstitute('Профиль ещё не зарегистрирован.')).toBe(false);
  });
});

describe('the two routing refusals are told apart by reference_kind', () => {
  it('an unclassified version', () => {
    const failure = classifyRunFailure(unclassified());
    expect(failure.kind).toBe('version_unclassified');
    expect(failure.presentation).toBe('unsupported');
    expect(failure.title).toBe(VERSION_UNCLASSIFIED_REFUSAL.title);
    expect(failure.detail).toContain('Подтвердите стадию и раздел');
    expect(failure.correlationId).toBe('cid-section');
  });

  it('a confirmed section without a profile', () => {
    const failure = classifyRunFailure(noProfile());
    expect(failure.kind).toBe('section_profile_unavailable');
    expect(failure.presentation).toBe('unsupported');
    expect(failure.title).toBe(SECTION_PROFILE_UNAVAILABLE_REFUSAL.title);
    expect(failure.detail).toContain('не зарегистрирован');
  });

  it('any other reference_kind is the catalog sentence, not one of these two', () => {
    const failure = classifyRunFailure(
      apiError(422, 'required_norm_unavailable', { reference_kind: 'norm_retrieval_set' }),
    );
    expect(failure.kind).toBe('reference_unavailable');
    expect(failure.detail).toBe(catalogMessage('required_norm_unavailable'));
    expect(routingRefusal({ reference_kind: 'norm_retrieval_set' })).toBeNull();
    expect(routingRefusal({})).toBeNull();
  });

  it('neither is offered as retryable, and neither offers another profile', () => {
    for (const error of [unclassified(), noProfile()]) {
      const failure = classifyRunFailure(error);
      expect(failure.retryable).toBe(false);
      expect(offersASubstitute(`${failure.title} ${failure.detail}`)).toBe(false);
    }
  });
});

describe('the start-run control says which, and links to the panel that settles it', () => {
  it('unclassified: the sentence, a link to the version’s stage-and-section panel, no retry', () => {
    const markup = control(unclassified());
    expect(markup).toContain('data-run-failure="version_unclassified"');
    expect(markup).toContain('У версии не подтверждены стадия и раздел.');
    expect(markup).toContain(
      `href="${routes.versionClassification(PROJECT_UID, VERSION_UID)}"`,
    );
    expect(routes.versionClassification(PROJECT_UID, VERSION_UID)).toBe(
      `/projects/${PROJECT_UID}/versions/${VERSION_UID}#version-classification`,
    );
    expect(markup).toContain('>Подтвердить стадию и раздел</a>');
    expect(markup).toContain('Прогон не запущен.');
    expect(markup.match(/<button\b/g)).toHaveLength(1);
    expect(markup).not.toContain('Повторить');
    expect(offersASubstitute(markup.replace(/<[^>]+>/g, ' '))).toBe(false);
  });

  it('no profile: the sentence and a link to read the confirmed section, no retry', () => {
    const markup = control(noProfile());
    expect(markup).toContain('data-run-failure="section_profile_unavailable"');
    expect(markup).toContain('Для подтверждённого раздела нет профиля анализа.');
    expect(markup).toContain('data-classification-link=""');
    expect(markup).toContain('>Открыть стадию и раздел версии</a>');
    expect(markup.match(/<button\b/g)).toHaveLength(1);
    expect(offersASubstitute(markup.replace(/<[^>]+>/g, ' '))).toBe(false);
  });

  it('carries no classification link for an unrelated refusal', () => {
    const markup = control(apiError(422, 'analysis_input_invalid'));
    expect(markup).not.toContain('data-classification-link');
  });
});

describe('the queue’s re-audit says the same thing', () => {
  it('words both routing refusals with the run entity’s own sentences', () => {
    const first = executionFailure(unclassified(), true);
    expect(first.kind).toBe('refusal');
    expect(first.detail).toBe(`${VERSION_UNCLASSIFIED_REFUSAL.title} ${VERSION_UNCLASSIFIED_REFUSAL.detail}`);
    const second = executionFailure(noProfile(), true);
    expect(second.detail).toContain(SECTION_PROFILE_UNAVAILABLE_REFUSAL.title);
    expect(offersASubstitute(second.detail)).toBe(false);
  });

  it('keeps the catalog sentence for any other required_norm_unavailable', () => {
    const other = executionFailure(
      apiError(422, 'required_norm_unavailable', { reference_kind: 'norm_retrieval_set' }),
      true,
    );
    expect(other.detail).toBe(catalogMessage('required_norm_unavailable'));
  });
});
