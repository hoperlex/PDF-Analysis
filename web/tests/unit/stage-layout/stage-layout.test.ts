/**
 * `HOSTS-WEB-01` — «Модели по этапам»: the table of six rows, read-only for an expert and editable for an administrator, the
 * sets «Только Claude» and «Только Codex», the draft of a revision and the switch «Модели по этапам: включены». The rules of
 * the table, the sets and the draft are functions (`entities/stage-layout`, `features/manage-stage-layout`), so each is a call;
 * the screens are read from a render over a seeded cache.
 */

import { createElement } from 'react';
import type { ComponentType } from 'react';
import { describe, expect, it } from 'vitest';

import type { ModelCatalogue, Role, StageModelLayout } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import {
  BLOCK_SCHEMES, DEFAULT_TIMEOUT_SECONDS, NAMED_KITS, blockSchemeOf, cellText, effortsOf, kitCells, kitIsOffered, kitModelIds, layoutFailure, layoutRefusalSentence, layoutTable, pairIsInCatalogue,
  rowOfStageKey,
} from '@/entities/stage-layout';
import {
  LayoutEditorView, LayoutSwitchView, chooseKit, draftChanged, draftProblem, draftRequest, initialDraft, modelOptions, offeredBlockSchemes,
  offeredKits, setBlockScheme, setCellEffort, setCellModel,
} from '@/features/manage-stage-layout';
import type { LayoutDraft as LayoutDraftType } from '@/features/manage-stage-layout';
import { WorkersPage } from '@/_pages/workers';
import type { WorkersPageProps } from '@/_pages/workers';
import { ExecutorStageModels, LayoutHistoryView, StageLayoutAdvanced, StageModelsTable } from '@/widgets/executor-stage-models';

import { newClient, renderScreen } from '../screens/harness';
import { CATALOGUE, LAYOUT, LAYOUT_CELLS, LAYOUT_EMPTY, LAYOUT_OFF, cell, seedHosts, seedLayout } from '../workers/hosts-fixtures';

const ALL_MODELS = ['claude-opus-5-5', 'claude-sonnet-5-5', 'gpt-6.1-sol', 'gpt-6-sol', 'gpt-6-astra'];
const CLAUDE_ONLY_MODELS = ['claude-opus-5-5', 'claude-sonnet-5-5'];

function seeded(roles: Role[], layout: StageModelLayout = LAYOUT, tab: WorkersPageProps['initialTab'] = 'models'): string {
  const client = newClient();
  seedLayout(client, layout);
  seedHosts(client);
  client.setQueryData(queryKeys.account.me(), { roles });
  return renderScreen(client, createElement(WorkersPage as ComponentType<WorkersPageProps>, { initialTab: tab }));
}

describe('the table of six rows', () => {
  it('lists the six rows in the original\'s order, «строка — модель · усилие», with the effort in Russian', () => {
    const rows = layoutTable(LAYOUT);
    expect(rows.map((row) => row.row)).toEqual(['text', 'blocks', 'cross_check', 'norms', 'review', 'correction']);
    expect(rows.map((row) => row.cells.map((c) => c.text))).toEqual([
      ['Sonnet 5.5 · среднее'], ['gpt-6-astra · среднее'], ['Sonnet 5.5 · среднее'], ['Sonnet 5.5 · среднее'], ['gpt-6-astra · среднее'], ['Sonnet 5.5 · среднее'],
    ]);
    expect(cellText({ model_id: 'gpt-6-sol', effort: 'high' })).toBe('gpt-6-sol · высокое');
  });

  it('marks only the row whose model the server names as served by none', () => {
    expect(layoutTable(LAYOUT).filter((row) => row.problem).map((row) => row.row)).toEqual(['review']);
    expect(layoutTable({ ...LAYOUT, unavailable_cell_keys: [] }).some((row) => row.problem)).toBe(false);
  });

  it('names the cells of an ensemble row in the order of the roles, with the role in front', () => {
    const ensemble: StageModelLayout = {
      ...LAYOUT,
      current: { ...LAYOUT.current!, cells: [
        ...LAYOUT_CELLS.filter((c) => c.row !== 'blocks'),
        cell('blocks', 'claude-sonnet-5-5', 'medium', 'judge'), cell('blocks', 'claude-opus-5-5', 'medium', 'leg1'),
      ] },
    };
    const blocks = layoutTable(ensemble).find((row) => row.row === 'blocks')!;
    expect(blocks.cells.map((c) => c.text)).toEqual(['первая ветка: Opus 5.5 · среднее', 'судья: Sonnet 5.5 · среднее']);
  });

  it('says a row has no cells rather than inventing a model for it', () => {
    const rows = layoutTable({ ...LAYOUT, current: { ...LAYOUT.current!, cells: LAYOUT_CELLS.slice(0, 5) } });
    expect(rows.find((row) => row.row === 'correction')?.cells).toEqual([]);
  });

  it('maps the phases of the code to a row, and the ones with no model to none', () => {
    expect(rowOfStageKey('text_analysis')).toBe('text');
    expect(rowOfStageKey('blocks:12:leg1')).toBe('blocks');
    expect(rowOfStageKey('comprehensive_analysis')).toBe('cross_check');
    expect(rowOfStageKey('norm_verification:3')).toBe('norms');
    expect(rowOfStageKey('finding_review')).toBe('review');
    expect(rowOfStageKey('finding_correction')).toBe('correction');
    expect(rowOfStageKey('finding_merge')).toBeNull();
  });
});

describe('the expert reads the table and has no control', () => {
  it('draws six rows and «⚠ нет на серверах» on the one that needs it, to an expert', () => {
    const markup = seeded(['expert']);
    expect(markup).toContain('data-executor-stage-models');
    expect(markup.match(/data-layout-cell=/g)).toHaveLength(6);
    expect(markup.match(/data-layout-missing=/g)).toHaveLength(1);
    expect(markup).toContain('data-layout-missing="review"');
    expect(markup).toContain('⚠ нет на серверах');
    expect(markup).toContain('gpt-6-astra · среднее');
  });

  it('draws no control to an expert: no button, no select, no input', () => {
    const markup = seeded(['expert']);
    const panel = markup.slice(markup.indexOf('data-workers-panel="models"'));
    expect(panel).not.toContain('data-layout-edit');
    expect(panel).not.toContain('<select');
    expect(panel).not.toContain('<input');
    expect(panel).not.toContain('<button');
    expect(panel).not.toContain('Изменить');
  });

  it('draws an administrator «Изменить», and the table is the same for both', () => {
    const admin = seeded(['admin']);
    expect(admin).toContain('data-layout-edit');
    expect(admin).toContain('>Изменить<');
    expect(admin.match(/data-layout-cell=/g)).toHaveLength(6);
  });

  it('says a row that is served carries no mark', () => {
    const markup = renderScreen(newClient(), createElement(StageModelsTable, { layout: { ...LAYOUT, unavailable_cell_keys: [] }, admin: false }));
    expect(markup).not.toContain('нет на серверах');
    expect(markup).not.toContain('data-layout-missing');
  });

  it('says in a line whether the layout is in force, and keeps «Изменить» for the administrator while it is not', () => {
    const on = renderScreen(newClient(), createElement(StageModelsTable, { layout: LAYOUT, admin: true, onEdit: () => {} }));
    expect(on).toContain('data-layout-state="on"');
    const off = renderScreen(newClient(), createElement(StageModelsTable, { layout: LAYOUT_OFF, admin: true, onEdit: () => {} }));
    expect(off).toContain('data-layout-state="off"');
    expect(off).toContain('Набор не применяется');
    expect(off).toContain('data-layout-edit');
  });

  it('asks an administrator to choose when there is no revision, and tells an expert it is not set', () => {
    expect(renderScreen(newClient(), createElement(StageModelsTable, { layout: LAYOUT_EMPTY, admin: true, onEdit: () => {} }))).toContain('Нажмите «Изменить»');
    const expert = renderScreen(newClient(), createElement(StageModelsTable, { layout: LAYOUT_EMPTY, admin: false }));
    expect(expert).toContain('Набор моделей ещё не задан.');
    expect(expert).not.toContain('Изменить');
  });

  it('can fail: it draws an expert nothing a viewer would not also be drawn', () => {
    const markup = seeded(['viewer']);
    expect(markup).not.toContain('data-layout-cell');
    expect(markup).not.toContain('data-executor-stage-models');
  });
});

describe('the sets', () => {
  it('are the two tables of the original, the blocks row a scheme, with today\'s answer limits for a cell the revision does not have', () => {
    const claude = kitCells('claude_only', []);
    expect(claude.map((c) => [c.cell_key, c.model_id, c.effort])).toEqual([
      ['text:main', 'claude-sonnet-5-5', 'medium'],
      ['blocks:leg1', 'claude-opus-5-5', 'medium'], ['blocks:judge', 'claude-sonnet-5-5', 'medium'],
      ['cross_check:main', 'claude-sonnet-5-5', 'medium'], ['norms:main', 'claude-sonnet-5-5', 'medium'],
      ['review:main', 'claude-sonnet-5-5', 'medium'], ['correction:main', 'claude-sonnet-5-5', 'medium'],
    ]);
    // Review and correction follow the backend's `ROW_DEFAULT_MAX_OUTPUT_TOKENS`: 12000, not 6000; the legs and the judge take the row's 6000.
    expect(claude.map((c) => c.max_output_tokens)).toEqual([16000, 6000, 6000, 6000, 12000, 12000, 12000]);
    const codex = kitCells('codex_only', []);
    expect(codex.map((c) => [c.cell_key, c.model_id])).toEqual([
      ['text:main', 'gpt-6.1-sol'],
      ['blocks:leg1', 'gpt-6-astra'], ['blocks:leg2', 'gpt-6-sol'], ['blocks:judge', 'gpt-6.1-sol'],
      ['cross_check:main', 'gpt-6-sol'], ['norms:main', 'gpt-6-astra'], ['review:main', 'gpt-6-sol'], ['correction:main', 'gpt-6.1-sol'],
    ]);
    expect(codex.map((c) => c.max_output_tokens)).toEqual([16000, 6000, 6000, 6000, 6000, 12000, 12000, 12000]);
    expect(codex.every((c) => c.effort === 'medium')).toBe(true);
    expect([...kitModelIds('claude_only')].sort()).toEqual([...CLAUDE_ONLY_MODELS].sort());
    // The legs and the judge are models of the set: «Только Codex» names all three Codex pins, the judge's among them.
    expect([...kitModelIds('codex_only')].sort()).toEqual(['gpt-6-astra', 'gpt-6-sol', 'gpt-6.1-sol']);
  });

  it('give a cell the revision does not have the timeout the server defaults to: 1800 seconds, not 600', () => {
    expect(DEFAULT_TIMEOUT_SECONDS).toBe(1800);
    for (const kit of NAMED_KITS) {
      expect(kitCells(kit, []).every((c) => c.timeout_seconds === 1800)).toBe(true);
    }
    // A cell the revision has keeps its own timeout, so the default reaches only a cell with none.
    const onlyText = LAYOUT_CELLS.filter((c) => c.row === 'text').map((c) => ({ ...c, timeout_seconds: 99 }));
    expect(kitCells('claude_only', onlyText).map((c) => c.timeout_seconds)).toEqual([99, 1800, 1800, 1800, 1800, 1800, 1800]);
  });

  it('keep the limits of a cell the revision in force already has, the legs and the judge each its own', () => {
    const current = LAYOUT_CELLS.map((c) => ({ ...c, max_output_tokens: 1234, timeout_seconds: 99 }));
    // «Только Codex» has a leg and a judge the revision has no cell for: they take the row's defaults, not another cell's limits.
    const cells = kitCells('codex_only', [...current, cell('blocks', 'gpt-6-astra', 'medium', 'leg1')].map((c) => (c.cell_key === 'blocks:leg1' ? { ...c, max_output_tokens: 777 } : c)));
    expect(cells.find((c) => c.cell_key === 'blocks:leg1')?.max_output_tokens).toBe(777);
    expect(cells.find((c) => c.cell_key === 'blocks:leg2')?.max_output_tokens).toBe(6000);
    expect(cells.find((c) => c.cell_key === 'blocks:judge')?.timeout_seconds).toBe(1800);
    expect(cells.filter((c) => c.row !== 'blocks').every((c) => c.max_output_tokens === 1234 && c.timeout_seconds === 99)).toBe(true);
  });

  it('are offered only when every model they name can be served, and every pair is in the catalogue', () => {
    expect(kitIsOffered('claude_only', CATALOGUE, CLAUDE_ONLY_MODELS)).toBe(true);
    expect(kitIsOffered('codex_only', CATALOGUE, CLAUDE_ONLY_MODELS)).toBe(false);
    expect(kitIsOffered('codex_only', CATALOGUE, ALL_MODELS)).toBe(true);
    // The judge counts: a Codex server that serves the legs but not `gpt-6.1-sol` does not offer the set, though no other row but the text needs it.
    expect(kitIsOffered('codex_only', CATALOGUE, ALL_MODELS.filter((id) => id !== 'gpt-6.1-sol'))).toBe(false);
    expect(kitIsOffered('claude_only', CATALOGUE, ['claude-opus-5-5'])).toBe(false);
    const noOpusMedium: ModelCatalogue = { ...CATALOGUE, items: CATALOGUE.items.map((e) => (e.model_id === 'claude-opus-5-5' ? { ...e, efforts: ['high'] } : e)) };
    expect(kitIsOffered('claude_only', noOpusMedium, ALL_MODELS)).toBe(false);
    expect(NAMED_KITS).toEqual(['claude_only', 'codex_only']);
  });

  it('keep the efforts the catalogue allows: Opus has no «low», and nothing is above «high»', () => {
    expect(effortsOf(CATALOGUE, 'claude-opus-5-5')).toEqual(['medium', 'high']);
    expect(pairIsInCatalogue(CATALOGUE, 'claude-opus-5-5', 'low')).toBe(false);
    expect(pairIsInCatalogue(CATALOGUE, 'claude-sonnet-5-5', 'low')).toBe(true);
    expect(pairIsInCatalogue(CATALOGUE, 'no-such-model', 'medium')).toBe(false);
  });
});

describe('the draft of a revision', () => {
  it('starts from the revision in force, or from the first set that can be offered, or from nothing', () => {
    expect(initialDraft(LAYOUT, CATALOGUE, ALL_MODELS)?.kit).toBe('custom');
    expect(initialDraft(LAYOUT_EMPTY, CATALOGUE, ALL_MODELS)?.kit).toBe('claude_only');
    expect(initialDraft(LAYOUT_EMPTY, CATALOGUE, ['gpt-6-sol'])).toBeNull();
    expect(initialDraft(LAYOUT_EMPTY, CATALOGUE, [])).toBeNull();
  });

  it('offers the sets that can be served, and «Свой набор» always', () => {
    expect(offeredKits(CATALOGUE, CLAUDE_ONLY_MODELS, undefined)).toEqual(['claude_only', 'custom']);
    expect(offeredKits(CATALOGUE, ALL_MODELS, undefined)).toEqual(['claude_only', 'codex_only', 'custom']);
    expect(offeredKits(CATALOGUE, [], undefined)).toEqual(['custom']);
    // The set in force is shown even when no server serves it now: it is what is in force.
    expect(offeredKits(CATALOGUE, [], 'codex_only')).toEqual(['codex_only', 'custom']);
  });

  it('makes any edit «Свой набор», and choosing a set fills every row', () => {
    const start = initialDraft(LAYOUT_EMPTY, CATALOGUE, ALL_MODELS)!;
    const edited = setCellModel(start, 'review:main', 'gpt-6-sol', CATALOGUE);
    expect(edited.kit).toBe('custom');
    expect(edited.cells.find((c) => c.cell_key === 'review:main')?.model_id).toBe('gpt-6-sol');
    const back = chooseKit(edited, 'codex_only');
    expect(back.kit).toBe('codex_only');
    expect(back.cells.map((c) => c.model_id)).toEqual(kitCells('codex_only', []).map((c) => c.model_id));
    expect(chooseKit(back, 'custom')).toEqual({ kit: 'custom', cells: back.cells });
  });

  it('keeps the effort across a change of model only when the new model allows it', () => {
    const start = { kit: 'custom' as const, cells: [cell('text', 'claude-sonnet-5-5', 'low')] };
    // Opus has no «low»: it takes «medium», never an effort the catalogue refuses.
    expect(setCellModel(start, 'text:main', 'claude-opus-5-5', CATALOGUE).cells[0]?.effort).toBe('medium');
    expect(setCellModel(start, 'text:main', 'gpt-6-sol', CATALOGUE).cells[0]?.effort).toBe('low');
    expect(setCellEffort(start, 'text:main', 'high').cells[0]?.effort).toBe('high');
  });

  it('offers a cell the models some server serves and the catalogue names, and the one the cell has', () => {
    const c = cell('text', 'gpt-6-astra');
    expect(modelOptions(c, CATALOGUE, CLAUDE_ONLY_MODELS)).toEqual(['gpt-6-astra', 'claude-opus-5-5', 'claude-sonnet-5-5']);
    expect(modelOptions(cell('text', 'claude-opus-5-5'), CATALOGUE, CLAUDE_ONLY_MODELS)).toEqual(CLAUDE_ONLY_MODELS);
    expect(modelOptions(c, CATALOGUE, ['not-in-the-catalogue'])).toEqual(['gpt-6-astra']);
  });

  it('refuses to save a pair the catalogue does not have, an empty draft and a limit out of range', () => {
    expect(draftProblem(initialDraft(LAYOUT, CATALOGUE, ALL_MODELS)!, CATALOGUE)).toBeNull();
    expect(draftProblem({ kit: 'custom', cells: [] }, CATALOGUE)).toContain('пуст');
    expect(draftProblem({ kit: 'custom', cells: [cell('text', 'claude-opus-5-5', 'low')] }, CATALOGUE)).toContain('каталоге');
    expect(draftProblem({ kit: 'custom', cells: [{ ...cell('text', 'claude-sonnet-5-5'), max_output_tokens: 0 }] }, CATALOGUE)).toContain('Ответ, токенов');
    expect(draftProblem({ kit: 'custom', cells: [{ ...cell('text', 'claude-sonnet-5-5'), timeout_seconds: 7201 }] }, CATALOGUE)).toContain('Таймаут');
  });

  it('builds the request from the draft, and calls an unchanged draft unchanged', () => {
    const draft = initialDraft(LAYOUT, CATALOGUE, ALL_MODELS)!;
    expect(draftChanged(draft, LAYOUT)).toBe(false);
    expect(draftChanged(setCellEffort(draft, 'norms:main', 'high'), LAYOUT)).toBe(true);
    expect(draftChanged(draft, LAYOUT_EMPTY)).toBe(true);
    expect(draftRequest(draft)).toEqual({ kit: 'custom', cells: LAYOUT_CELLS });
  });
});

describe('the blocks row is one of three schemes (`HOSTS-ENSEMBLE-01`)', () => {
  const start = () => initialDraft(LAYOUT, CATALOGUE, ALL_MODELS)!;

  it('has the three schemes of the server\'s closed list, each named by its models', () => {
    expect(BLOCK_SCHEMES.map((scheme) => scheme.id)).toEqual(['claude_opus_judge_sonnet', 'codex_astra_sol_judge', 'codex_astra_single']);
    expect(BLOCK_SCHEMES.map((scheme) => scheme.label)).toEqual([
      'Opus 5.5, судья Sonnet 5.5', 'gpt-6-astra + gpt-6-sol, судья gpt-6.1-sol', 'gpt-6-astra, без судьи',
    ]);
  });

  it('reads a scheme off the blocks cells by role, model and effort, and says none for anything else', () => {
    expect(blockSchemeOf(LAYOUT_CELLS)?.id).toBe('codex_astra_single');
    expect(blockSchemeOf(kitCells('claude_only', []))?.id).toBe('claude_opus_judge_sonnet');
    expect(blockSchemeOf(kitCells('codex_only', []))?.id).toBe('codex_astra_sol_judge');
    // A single Claude, the Claude ensemble at another effort, and the legs without their judge are not on the list.
    expect(blockSchemeOf([cell('blocks', 'claude-opus-5-5')])).toBeNull();
    expect(blockSchemeOf([cell('blocks', 'claude-opus-5-5', 'high', 'leg1'), cell('blocks', 'claude-sonnet-5-5', 'medium', 'judge')])).toBeNull();
    expect(blockSchemeOf([cell('blocks', 'claude-opus-5-5', 'medium', 'leg1')])).toBeNull();
    expect(blockSchemeOf([cell('text', 'claude-sonnet-5-5')])).toBeNull();
  });

  it('chooses the whole row at once: the other rows stay, the cells become the scheme\'s, each keeps the limits it had', () => {
    const tuned = { ...start(), cells: start().cells.map((c) => (c.row === 'blocks' ? { ...c, max_output_tokens: 4321 } : c.row === 'text' ? { ...c, max_output_tokens: 999 } : c)) };
    const chosen = setBlockScheme(tuned, 'claude_opus_judge_sonnet');
    expect(chosen.kit).toBe('custom');
    expect(chosen.cells.map((c) => c.cell_key)).toEqual(['text:main', 'blocks:leg1', 'blocks:judge', 'cross_check:main', 'norms:main', 'review:main', 'correction:main']);
    expect(blockSchemeOf(chosen.cells)?.id).toBe('claude_opus_judge_sonnet');
    // The old `blocks:main` is gone; the new cells had no saved limits, so they take the row's 6000.
    expect(chosen.cells.filter((c) => c.row === 'blocks').map((c) => c.max_output_tokens)).toEqual([6000, 6000]);
    expect(chosen.cells.find((c) => c.row === 'text')?.max_output_tokens).toBe(999);
    // Choosing again a scheme that keeps a cell key keeps that cell's limits.
    const back = setBlockScheme(chosen, 'codex_astra_sol_judge');
    expect(back.cells.filter((c) => c.row === 'blocks').map((c) => c.cell_key)).toEqual(['blocks:leg1', 'blocks:leg2', 'blocks:judge']);
    expect(draftProblem(back, CATALOGUE)).toBeNull();
  });

  it('offers a scheme only when every model of it is served, and always the one the row already is', () => {
    expect(offeredBlockSchemes(start(), CATALOGUE, ALL_MODELS).map((s) => s.id)).toEqual(['claude_opus_judge_sonnet', 'codex_astra_sol_judge', 'codex_astra_single']);
    expect(offeredBlockSchemes(start(), CATALOGUE, CLAUDE_ONLY_MODELS).map((s) => s.id)).toEqual(['claude_opus_judge_sonnet', 'codex_astra_single']);
    expect(offeredBlockSchemes(setBlockScheme(start(), 'claude_opus_judge_sonnet'), CATALOGUE, ['gpt-6-astra']).map((s) => s.id)).toEqual(['claude_opus_judge_sonnet', 'codex_astra_single']);
    expect(offeredBlockSchemes(start(), CATALOGUE, []).map((s) => s.id)).toEqual(['codex_astra_single']);
  });

  it('refuses to save a blocks row that is none of the schemes, as the server does', () => {
    const single = { ...start(), cells: start().cells.map((c) => (c.row === 'blocks' ? { ...c, model_id: 'claude-opus-5-5' } : c)) };
    expect(draftProblem(single, CATALOGUE)).toContain('схем');
    expect(draftProblem(start(), CATALOGUE)).toBeNull();
    expect(draftProblem(chooseKit(start(), 'claude_only'), CATALOGUE)).toBeNull();
    expect(draftProblem(chooseKit(start(), 'codex_only'), CATALOGUE)).toBeNull();
  });

  it('is one select in the form and replaces the model and the effort of the row; a stored pairing off the list says so', () => {
    const view = (draft: LayoutDraftType) => renderScreen(newClient(), createElement(LayoutEditorView, {
      draft, catalogue: CATALOGUE, availableModelIds: ALL_MODELS, currentKit: 'custom', pending: false, problem: null, failure: null,
      onKit: () => {}, onModel: () => {}, onScheme: () => {}, onEffort: () => {}, onLimit: () => {}, onSave: () => {}, onCancel: () => {},
    }));
    const markup = view(setBlockScheme(start(), 'codex_astra_sol_judge'));
    const select = markup.match(/<select[^>]*data-layout-scheme="blocks"[^>]*>[\s\S]*?<\/select>/)?.[0] ?? '';
    expect(select).toMatch(/<option value="codex_astra_sol_judge"[^>]*selected=""|<option[^>]*selected=""[^>]*value="codex_astra_sol_judge"/);
    for (const label of ['Opus 5.5, судья Sonnet 5.5', 'gpt-6-astra + gpt-6-sol, судья gpt-6.1-sol', 'gpt-6-astra, без судьи']) expect(select).toContain(label);
    expect(select).not.toContain('не из списка');
    // The limits of the legs and the judge are in «Дополнительно», one entry per cell, each named by its part.
    expect(markup.match(/data-layout-limits="blocks:/g)).toHaveLength(3);
    expect(markup).toContain('Анализ блоков · судья');
    const legacy = { ...start(), cells: start().cells.map((c) => (c.row === 'blocks' ? { ...c, model_id: 'claude-opus-5-5' } : c)) };
    expect(view(legacy)).toContain('не из списка');
  });
});

describe('the form «Изменить»', () => {
  const view = (over: Partial<Parameters<typeof LayoutEditorView>[0]> = {}) => renderScreen(newClient(), createElement(LayoutEditorView, {
    draft: initialDraft(LAYOUT, CATALOGUE, ALL_MODELS)!, catalogue: CATALOGUE, availableModelIds: ALL_MODELS, currentKit: 'custom',
    pending: false, problem: null, failure: null, onKit: () => {}, onModel: () => {}, onScheme: () => {}, onEffort: () => {}, onLimit: () => {},
    onSave: () => {}, onCancel: () => {}, ...over,
  }));

  it('draws the segments, a model and an effort for each of the six rows, and «Дополнительно» folded', () => {
    const markup = view();
    expect(markup).toContain('>Только Claude<');
    expect(markup).toContain('>Только Codex<');
    expect(markup).toContain('>Свой набор<');
    // Five rows are a model and an effort; the blocks row is one select of three schemes (`HOSTS-ENSEMBLE-01`).
    expect(markup.match(/data-layout-model=/g)).toHaveLength(5);
    expect(markup.match(/data-layout-effort=/g)).toHaveLength(5);
    expect(markup.match(/data-layout-scheme="blocks"/g)).toHaveLength(1);
    expect(markup.match(/data-layout-scheme-id=/g)).toHaveLength(3);
    expect(markup).not.toContain('data-layout-model="blocks"');
    expect(markup).toMatch(/<details[^>]*><summary>Дополнительно<\/summary>/);
    expect(markup).toContain('Ответ, токенов');
    expect(markup).toContain('Таймаут, с');
    expect(markup).toMatch(/aria-checked="true"[^>]*data-layout-kit="custom"|data-layout-kit="custom"[^>]*aria-checked="true"/);
  });

  it('does not offer a set no server can serve, nor a model none can', () => {
    const markup = view({ availableModelIds: CLAUDE_ONLY_MODELS, currentKit: undefined });
    expect(markup).toContain('data-layout-kit="claude_only"');
    expect(markup).not.toContain('data-layout-kit="codex_only"');
    // The critic's current model, gpt-6-astra, is offered because it is in the cell; gpt-6-sol is not.
    expect(markup).toContain('value="gpt-6-astra"');
    expect(markup).not.toContain('value="gpt-6-sol"');
  });

  it('offers an effort only from the model\'s list: Opus has no «низкое»', () => {
    const draft = setCellModel(initialDraft(LAYOUT, CATALOGUE, ALL_MODELS)!, 'norms:main', 'claude-opus-5-5', CATALOGUE);
    const norms = view({ draft }).match(/<select[^>]*data-layout-effort="norms"[^>]*>[\s\S]*?<\/select>/)?.[0] ?? '';
    expect(norms).toContain('среднее');
    expect(norms).toContain('высокое');
    expect(norms).not.toContain('низкое');
  });

  it('says why there is nothing to choose from, and disables saving while a problem stands', () => {
    expect(view({ availableModelIds: [] })).toContain('data-layout-no-models');
    const stuck = view({ problem: 'Набор моделей пуст: выберите модели по этапам.' });
    expect(stuck).toContain('data-layout-problem');
    expect(stuck).toMatch(/data-layout-save[^>]*disabled=""|disabled=""[^>]*data-layout-save/);
  });

  it('shows a refusal of the server in words and never an identifier', () => {
    const refusal = new ApiError(422, { contract_version: '1.46.0', error_code: 'validation_failed', message: 'x', correlation_id: 'cid-layout-1', retryable: false, details: { field: 'cells', constraint: 'catalogue' } }, null);
    expect(layoutRefusalSentence(refusal)).toContain('парой из каталога');
    expect(layoutFailure(refusal, true).kind).toBe('refusal');
    const markup = view({ failure: layoutFailure(refusal, true) });
    expect(markup).toContain('Набор моделей не сохранён');
    expect(markup).not.toContain('validation_failed');
  });

  it('is drawn to an administrator who clicked «Изменить», and read from the servers and the catalogue', () => {
    const client = newClient();
    seedLayout(client);
    seedHosts(client);
    const markup = renderScreen(client, createElement(ExecutorStageModels, { roles: ['admin'], initiallyEditing: true }));
    expect(markup).toContain('data-layout-editor');
    expect(markup).not.toContain('data-layout-edit"');
    const expert = renderScreen(client, createElement(ExecutorStageModels, { roles: ['expert'], initiallyEditing: true }));
    expect(expert).not.toContain('data-layout-editor');
  });
});

describe('the switch «Модели по этапам: включены» and the history', () => {
  const sw = (layout: StageModelLayout, over: Partial<Parameters<typeof LayoutSwitchView>[0]> = {}) =>
    renderScreen(newClient(), createElement(LayoutSwitchView, { layout, pending: false, failure: null, onChange: () => {}, ...over }));

  it('shows the layout\'s own state, and the journal in a fold', () => {
    const on = sw(LAYOUT);
    expect(on).toContain('data-layout-switch="on"');
    expect(on).toContain('Модели по этапам: включены');
    expect(on).toContain('data-layout-journal');
    expect(on).toContain('Включён');
    expect(sw(LAYOUT_OFF)).toContain('data-layout-switch="off"');
    expect(sw(LAYOUT_OFF)).toContain('Переключатель ещё не менялся.');
  });

  it('is blocked, with its reason beside it, until a revision is saved', () => {
    const blocked = sw(LAYOUT_EMPTY);
    expect(blocked).toContain('data-layout-switch-reason');
    expect(blocked).toContain('Включить нельзя: набор моделей ещё не сохранён.');
    expect(blocked).toMatch(/role="switch"[^>]*disabled=""|disabled=""[^>]*role="switch"/);
    expect(sw(LAYOUT_OFF)).not.toContain('data-layout-switch-reason');
    expect(sw(LAYOUT_OFF)).not.toMatch(/role="switch"[^>]*disabled=""/);
  });

  it('says the two refusals of the server in words', () => {
    const conflict = (reason: string) => new ApiError(409, { contract_version: '1.46.0', error_code: 'conflict', message: 'x', correlation_id: 'cid-l-2', retryable: false, details: { conflict_reason: reason } }, null);
    expect(layoutFailure(conflict('no_layout_revision'), true).detail).toContain('набор моделей ещё не сохранён');
    expect(layoutFailure(conflict('provider_source_not_database'), true).detail).toContain('не из базы данных');
    expect(layoutFailure(conflict('something_new'), true).detail).not.toContain('something_new');
  });

  it('lists the revisions newest first and says which one is in force', () => {
    const markup = renderScreen(newClient(), createElement(LayoutHistoryView, { layout: LAYOUT }));
    expect(markup.indexOf('Версия 2')).toBeLessThan(markup.indexOf('Версия 1'));
    expect(markup).toContain('действует');
    expect(renderScreen(newClient(), createElement(LayoutHistoryView, { layout: LAYOUT_EMPTY }))).toContain('Прежних версий нет.');
  });

  it('is drawn to an administrator on the advanced page and to nobody else', () => {
    const client = newClient();
    seedLayout(client);
    expect(renderScreen(client, createElement(StageLayoutAdvanced, { roles: ['admin'] }))).toContain('data-layout-switch');
    for (const roles of [['expert'], ['viewer'], []] as Role[][]) {
      const markup = renderScreen(client, createElement(StageLayoutAdvanced, { roles }));
      expect(markup, roles.join()).not.toContain('data-layout-switch');
      expect(markup, roles.join()).not.toContain('role="switch"');
    }
  });
});
