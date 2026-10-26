import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { looksLikeArV3GroupId } from '@/entities/audit-run';
import { queryKeys } from '@/shared/api';
import { ArV3BetaReview } from '@/widgets/ar-v3-beta-review';

import { newClient, renderScreen } from '../screens/harness';

import { GROUP_ID, SCOPES, groupReviewFixture } from './ar-v3-beta-review-fixtures';

describe('AR v3 beta group review panel', () => {
  it('sends no read without a valid opaque group ID', () => {
    expect(looksLikeArV3GroupId(GROUP_ID)).toBe(true);
    expect(looksLikeArV3GroupId('arg_bad')).toBe(false);
    const empty = renderScreen(newClient(), createElement(ArV3BetaReview, { groupId: null }));
    expect(empty).toContain('Показать разбор');
    expect(empty).not.toContain('Загрузка: разбора группы');
    const invalid = renderScreen(newClient(), createElement(ArV3BetaReview, { groupId: 'arg_bad' }));
    expect(invalid).toContain('Неверный идентификатор группы');
    expect(invalid).toContain('Укажите идентификатор группы из ответа запуска.');
    expect(invalid).not.toContain('Укажите идентификатор arg_');
  });

  it('shows all six states and escaped provisional evidence without claiming a verdict', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.arV3GroupReview(GROUP_ID), groupReviewFixture());
    const markup = renderScreen(client, createElement(ArV3BetaReview, { groupId: GROUP_ID }));
    expect([...markup.matchAll(/data-ar-v3-review-scope="([A-Z][0-9])"/g)].map((match) => match[1]))
      .toEqual([...SCOPES]);
    expect(markup).toContain('Прогон завершился ошибкой');
    expect(markup).toContain('Проверка сохранённого разбора отказала');
    expect(markup).toContain('ширина двери');
    expect(markup).toContain('&lt;script&gt;цитата&lt;/script&gt;');
    expect(markup).not.toContain('<script>цитата</script>');
    expect(markup).toContain('Числовой или правовой вывод здесь не утверждён');
  });

  it('refuses a partial six-scope response instead of displaying its one available quote', () => {
    const client = newClient();
    const broken = groupReviewFixture();
    client.setQueryData(queryKeys.runs.arV3GroupReview(GROUP_ID), {
      ...broken, members: broken.members.slice(0, 1),
    });
    const markup = renderScreen(client, createElement(ArV3BetaReview, { groupId: GROUP_ID }));
    expect(markup).toContain('Разбор группы не подтверждён');
    expect(markup).not.toContain('ширина двери');
  });
});
