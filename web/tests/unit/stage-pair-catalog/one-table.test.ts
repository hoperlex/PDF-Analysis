/**
 * One table of pairs, the possible pairs among its rows (`UIP-S16-04`, `Г1-C`, `Г3-B`, `Г12-B`, `Г4-B`).
 *
 * Step 1 shows one table: the documents of stage П and of stage Р, the status, «Открыть» and «Управление». A possible pair is a row of
 * the same table, after the confirmed pairs, dashed and marked «предложение», with «Подтвердить» (the command of a pair made by
 * hand, with its key) and the documents in the row itself. There is no block «Возможные пары» under the table. A suggestion decides
 * nothing: «Документы связывает эксперт» stays true, and a reader has no button to press.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { StagePair, StagePairSuggestion } from '@/shared/api';
import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';
import { StagePairCatalog } from '@/widgets/stage-pair-catalog';

import { WEB_ROOT } from '../../guards/lib/repo';
import { newClient, renderScreen } from '../screens/harness';
import { parseRules } from '../styles/contrast';
import { PROJECT_UID, uid } from '../version-compare/fixtures';

const NAMES = new Map([
  [uid('doc', 1), { title: 'Пояснительная записка', section: 'AR', stage: 'P' as const }],
  [uid('doc', 2), { title: 'Пояснительная записка, редакция 2', section: 'AR', stage: 'R' as const }],
  [uid('doc', 21), { title: 'Планы этажей', section: 'AR', stage: 'P' as const }],
  [uid('doc', 61), { title: 'Планы этажей, редакция 2', section: 'AR', stage: 'R' as const }],
]);

const pair = (index: number): StagePair => ({
  pair_id: uid('stp', index), project_uid: PROJECT_UID, left_document_uid: uid('doc', index), right_document_uid: uid('doc', index + 1),
  completeness: 'unknown', state: 'confirmed', created_at: '2026-10-29T00:00:00Z',
});
const hint = (index: number, reason = 'section_designation_exact'): StagePairSuggestion => ({
  left_document_uid: uid('doc', 20 + index), right_document_uid: uid('doc', 60 + index), reason, score: 1,
});

interface Seed {
  readonly pairs?: readonly StagePair[];
  readonly suggestions?: readonly StagePairSuggestion[];
  readonly expert?: boolean;
  readonly suggestionCursor?: string | null;
}

/** The catalog alone, as the screen mounts it, with the reads given: a static render never runs a query, so each is a cache entry. */
function catalog({ pairs = [pair(1), pair(3)], suggestions = [hint(1)], expert = true, suggestionCursor = null }: Seed = {}): string {
  const client = newClient();
  client.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), { items: pairs, page: { next_cursor: null }, unpaired_p_count: 1, unpaired_r_count: 1 });
  client.setQueryData(STAGE_PAIR_KEYS.suggestions(PROJECT_UID), { items: suggestions, page: { next_cursor: suggestionCursor } });
  client.setQueryData(STAGE_PAIR_KEYS.documents(PROJECT_UID), NAMES);
  return renderScreen(client, createElement(StagePairCatalog, { projectUid: PROJECT_UID, mayAct: expert })).replace(/<!-- -->/g, '');
}

/** The rows of the table as markup, in order, each with its key. */
function rowsOf(html: string): { readonly key: string; readonly html: string }[] {
  return [...html.matchAll(/<tr [^>]*data-row-key="([^"]+)"[^>]*>(.*?)<\/tr>/g)].map((match) => ({ key: match[1] as string, html: match[2] as string }));
}

describe('one table of pairs', () => {
  it('draws one table, and the possible pairs are rows of it after the confirmed ones', () => {
    const html = catalog();
    expect((html.match(/<table/g) ?? []).length).toBe(1);
    const rows = rowsOf(html);
    expect(rows.map((row) => row.key)).toEqual([
      `pair:${uid('stp', 1)}`, `pair:${uid('stp', 3)}`, `suggestion:${hint(1).left_document_uid}|${hint(1).right_document_uid}`,
    ]);
  });

  it('draws no block «Возможные пары» under the table, and no row of the old kind', () => {
    const html = catalog();
    expect(html).not.toContain('Возможные пары');
    expect(html).not.toContain('stage-suggestions-heading');
    expect(html).not.toContain('Проверить связь');
    expect(html).not.toContain('Подтвердить связь документов');
    expect(html).not.toContain('<article');
  });

  it('names the column of the documents «Документ / раздел», and says П and Р in the cell', () => {
    const html = catalog();
    expect(html).toContain('>Документ / раздел<');
    expect(html).not.toContain('Проект / раздел');
    expect(html).toContain('П: <a');
    expect(html).toContain('Р: <a');
  });

  it('marks a suggestion «предложение» with its reason and the documents in the row, and gives it «Подтвердить»', () => {
    const proposed = rowsOf(catalog())[2]!.html;
    expect(proposed).toContain('data-pair-suggestion=""');
    expect(proposed).toContain('>предложение<');
    expect(proposed).toContain('Совпадают раздел и подтверждённый шифр');
    expect(proposed).toContain('П: <a href="/projects/' + PROJECT_UID + '/documents/' + hint(1).left_document_uid);
    expect(proposed).toContain('Планы этажей · AR');
    expect(proposed).toContain('Планы этажей, редакция 2 · AR');
    expect(proposed).toMatch(/data-pair-confirm=""[^>]*>Подтвердить</);
    // A suggestion is not a pair: no run, no «Открыть», no «Управление», no choice for the queue.
    for (const absent of ['data-pair-open', 'data-pair-manage', 'type="checkbox"', 'Не запускалось', 'Полнота не указана']) expect(proposed, absent).not.toContain(absent);
  });

  it('draws no cell for the run data a suggestion does not have, and no dash standing for them', () => {
    const proposed = rowsOf(catalog())[2]!.html;
    expect(proposed).not.toContain('—');
    expect(proposed).not.toContain('…');
    // Its cells of method, date, changes and checks stand empty.
    expect((proposed!.match(/<td[^>]*><\/td>/g) ?? []).length).toBe(4 + 1);
  });

  it('keeps the confirmed pairs as they were: the documents, the run cells, «Открыть» and «Управление» where they apply', () => {
    const first = rowsOf(catalog())[0]!.html;
    expect(first).toContain('Пояснительная записка · AR');
    expect(first).toContain('Полнота не указана');
    expect(first).toContain('data-pair-manage=');
    expect(first).not.toContain('>предложение<');
  });

  it('gives a reader the rows and the reason, and no button to confirm: the decision is the expert\'s', () => {
    const html = catalog({ expert: false });
    expect(rowsOf(html)).toHaveLength(3);
    expect(html).toContain('>предложение<');
    expect(html).not.toContain('data-pair-confirm');
    expect(html).not.toContain('data-confirm-all-open');
    expect(html).not.toContain('Подтвердить');
  });

  it('says once that the expert links the documents, over the table, only while there is a suggestion to say it about', () => {
    expect(catalog()).toContain('Совпадение шифра или названия только подсказывает выбор. Документы связывает эксперт.');
    expect(catalog({ suggestions: [] })).not.toContain('Документы связывает эксперт');
  });

  it('shows only the suggestions when no pair is confirmed yet, and not the empty state', () => {
    const html = catalog({ pairs: [], suggestions: [hint(1), hint(2)] });
    expect(rowsOf(html)).toHaveLength(2);
    expect(html).not.toContain('Подтверждённых пар пока нет');
  });

  it('says there is nothing only when there is neither a pair nor a suggestion', () => {
    const html = catalog({ pairs: [], suggestions: [] });
    expect(html).toContain('Подтверждённых пар пока нет');
    expect(html).not.toContain('<table');
  });

  it('leaves the pager of the suggestions out until there is another page of them', () => {
    expect(catalog()).not.toContain('Страницы возможных пар');
    expect(catalog({ suggestionCursor: 'cur_2' })).toContain('Страницы возможных пар');
  });

  it('marks the open pair by its own row, and not by a suggestion\'s', () => {
    const html = catalog({ pairs: [pair(1)] });
    // One pair opens by itself (the panel under the table), and its row is the current one.
    expect(html).toMatch(/aria-current="true"[^>]*data-row-key="pair:/);
    expect((html.match(/aria-current="true"/g) ?? []).length).toBe(1);
  });
});

describe('the dashed row', () => {
  const css = readFileSync(join(WEB_ROOT, 'src', 'widgets', 'stage-pair-catalog', 'ui', 'stage-pair-catalog.module.css'), 'utf8');
  const declares = (source: string, selector: string, property: string, value: RegExp): boolean =>
    parseRules(source, 'test').some((rule) => rule.selector.split(',').some((part) => part.trim() === selector) && value.test(rule.declarations.get(property) ?? ''));
  const ROW = ".catalog tr[data-row-key^='suggestion:'] > td";

  it('is the row whose key says suggestion, with dashed rules only: its colours and widths are the table\'s', () => {
    expect(declares(css, ROW, 'border-bottom-style', /^dashed$/)).toBe(true);
    const own = parseRules(css, 'test').find((rule) => rule.selector.trim() === ROW);
    expect([...(own?.declarations.keys() ?? [])]).toEqual(['border-bottom-style']);
  });

  it('can fail: a stylesheet without the rule, or with another style, does not read as dashed', () => {
    expect(declares('.catalog { display: grid; }', ROW, 'border-bottom-style', /^dashed$/)).toBe(false);
    expect(declares(`${ROW} { border-bottom-style: solid; }`, ROW, 'border-bottom-style', /^dashed$/)).toBe(false);
  });

  it('is reached by the key the catalog gives a suggestion, and by no pair\'s', () => {
    const keys = rowsOf(catalog()).map((row) => row.key);
    expect(keys.filter((key) => key.startsWith('suggestion:'))).toHaveLength(1);
    expect(keys.filter((key) => key.startsWith('pair:'))).toHaveLength(2);
  });

  it('uses no `:has()` and no `:not()`, which the contrast census does not evaluate', () => {
    expect(parseRules(css, 'test').filter((rule) => /:has\(|:not\(/.test(rule.selector)).map((rule) => rule.selector)).toEqual([]);
    expect(parseRules('.a:has(.b) { display: grid; }', 'test').filter((rule) => /:has\(|:not\(/.test(rule.selector))).toHaveLength(1);
  });
});
