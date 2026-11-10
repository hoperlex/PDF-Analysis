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
import { ApiError, COMPARISON_LAYOUT_KIND_VALUES, queryKeys } from '@/shared/api';
import {
  BLOCK_SCHEMES, COMPARISON_KIND_LABELS, COMPARISON_NONE_NOTE, NAMED_KITS, blockSchemeOf, cellText, comparisonKitCells, comparisonTable, effortsOf, kitCells,
  kitIsOffered, kitModelIds, layoutFailure, layoutRefusalSentence, layoutTable, pairIsInCatalogue, rowOfStageKey,
} from '@/entities/stage-layout';
import {
  LayoutEditorView, LayoutSwitchView, chooseKit, draftChanged, draftProblem, draftRequest, initialDraft, modelOptions, offeredBlockSchemes,
  offeredKits, setBlockScheme, setCellEffort, setCellModel, setComparisonEffort, setComparisonModel,
} from '@/features/manage-stage-layout';
import type { LayoutDraft as LayoutDraftType } from '@/features/manage-stage-layout';
import { WorkersPage } from '@/_pages/workers';
import type { WorkersPageProps } from '@/_pages/workers';
import { ExecutorStageModels, LayoutHistoryView, StageLayoutAdvanced, StageModelsTable } from '@/widgets/executor-stage-models';

import { newClient, renderScreen } from '../screens/harness';
import {
  CATALOGUE, COMPARISON_CELLS, LAYOUT, LAYOUT_CELLS, LAYOUT_COMPARISON, LAYOUT_COMPARISON_KIT, LAYOUT_EMPTY, LAYOUT_OFF, cell, seedHosts, seedLayout,
} from '../workers/hosts-fixtures';

const ALL_MODELS = ['claude-opus-5-5', 'claude-sonnet-5-5', 'gpt-6.1-sol', 'gpt-6-sol', 'gpt-6-astra', 'gpt-6-luna'];
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
  it('are the two tables of the original, the blocks row a scheme, a cell being a model and an effort and nothing else', () => {
    const claude = kitCells('claude_only');
    expect(claude.map((c) => [c.cell_key, c.model_id, c.effort])).toEqual([
      ['text:main', 'claude-sonnet-5-5', 'medium'],
      ['blocks:leg1', 'claude-opus-5-5', 'medium'], ['blocks:judge', 'claude-sonnet-5-5', 'medium'],
      ['cross_check:main', 'claude-sonnet-5-5', 'medium'], ['norms:main', 'claude-sonnet-5-5', 'medium'],
      ['review:main', 'claude-sonnet-5-5', 'medium'], ['correction:main', 'claude-sonnet-5-5', 'medium'],
    ]);
    // `LIMITS-01` (`R-153n`, `R-153o`): no answer length and no timeout on a cell, nothing to carry in a request.
    expect(claude.every((c) => Object.keys(c).sort().join() === 'cell_key,effort,model_id,role,row')).toBe(true);
    const codex = kitCells('codex_only');
    expect(codex.map((c) => [c.cell_key, c.model_id])).toEqual([
      ['text:main', 'gpt-6.1-sol'],
      ['blocks:leg1', 'gpt-6-astra'], ['blocks:leg2', 'gpt-6-sol'], ['blocks:judge', 'gpt-6.1-sol'],
      ['cross_check:main', 'gpt-6-sol'], ['norms:main', 'gpt-6-astra'], ['review:main', 'gpt-6-sol'], ['correction:main', 'gpt-6.1-sol'],
    ]);
    expect(codex.every((c) => c.effort === 'medium')).toBe(true);
    expect([...kitModelIds('claude_only')].sort()).toEqual([...CLAUDE_ONLY_MODELS].sort());
    // The legs and the judge are models of the set: «Только Codex» names the Codex pins, the judge's among them, and gpt-6-luna of the comparison.
    expect([...kitModelIds('codex_only')].sort()).toEqual(['gpt-6-astra', 'gpt-6-luna', 'gpt-6-sol', 'gpt-6.1-sol']);
  });

  it('keep the cells of a draft free of any limit: a draft of a revision read from the server has none to keep', () => {
    // A cell read from the server (an old revision included) carries the model and the effort; choosing a set again gives the same cells.
    const current = LAYOUT_CELLS.map((c) => ({ ...c }));
    expect(kitCells('codex_only').map((c) => c.cell_key)).toEqual(['text:main', 'blocks:leg1', 'blocks:leg2', 'blocks:judge', 'cross_check:main', 'norms:main', 'review:main', 'correction:main']);
    expect(current.every((c) => !('max_output_tokens' in c) && !('timeout_seconds' in c))).toBe(true);
    expect(JSON.stringify(draftRequest({ kit: 'custom', cells: current }))).not.toMatch(/max_output_tokens|timeout_seconds/);
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
    expect(back.cells.map((c) => c.model_id)).toEqual(kitCells('codex_only').map((c) => c.model_id));
    expect(chooseKit(back, 'custom')).toEqual({ kit: 'custom', cells: back.cells, comparison: back.comparison });
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

  it('refuses to save a pair the catalogue does not have and an empty draft', () => {
    expect(draftProblem(initialDraft(LAYOUT, CATALOGUE, ALL_MODELS)!, CATALOGUE)).toBeNull();
    expect(draftProblem({ kit: 'custom', cells: [] }, CATALOGUE)).toContain('пуст');
    expect(draftProblem({ kit: 'custom', cells: [cell('text', 'claude-opus-5-5', 'low')] }, CATALOGUE)).toContain('каталоге');
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
    expect(blockSchemeOf(kitCells('claude_only'))?.id).toBe('claude_opus_judge_sonnet');
    expect(blockSchemeOf(kitCells('codex_only'))?.id).toBe('codex_astra_sol_judge');
    // A single Claude, the Claude ensemble at another effort, and the legs without their judge are not on the list.
    expect(blockSchemeOf([cell('blocks', 'claude-opus-5-5')])).toBeNull();
    expect(blockSchemeOf([cell('blocks', 'claude-opus-5-5', 'high', 'leg1'), cell('blocks', 'claude-sonnet-5-5', 'medium', 'judge')])).toBeNull();
    expect(blockSchemeOf([cell('blocks', 'claude-opus-5-5', 'medium', 'leg1')])).toBeNull();
    expect(blockSchemeOf([cell('text', 'claude-sonnet-5-5')])).toBeNull();
  });

  it('chooses the whole row at once: the other rows stay and the cells become the scheme\'s', () => {
    const tuned = { ...start(), cells: start().cells.map((c) => (c.row === 'text' ? { ...c, model_id: 'gpt-6-sol' } : c)) };
    const chosen = setBlockScheme(tuned, 'claude_opus_judge_sonnet');
    expect(chosen.kit).toBe('custom');
    expect(chosen.cells.map((c) => c.cell_key)).toEqual(['text:main', 'blocks:leg1', 'blocks:judge', 'cross_check:main', 'norms:main', 'review:main', 'correction:main']);
    expect(blockSchemeOf(chosen.cells)?.id).toBe('claude_opus_judge_sonnet');
    // The old `blocks:main` is gone, and the cell of another row is as the person left it.
    expect(chosen.cells.filter((c) => c.row === 'blocks').map((c) => c.cell_key)).toEqual(['blocks:leg1', 'blocks:judge']);
    expect(chosen.cells.find((c) => c.row === 'text')?.model_id).toBe('gpt-6-sol');
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
      onKit: () => {}, onModel: () => {}, onScheme: () => {}, onEffort: () => {}, onSave: () => {}, onCancel: () => {},
    }));
    const markup = view(setBlockScheme(start(), 'codex_astra_sol_judge'));
    const select = markup.match(/<select[^>]*data-layout-scheme="blocks"[^>]*>[\s\S]*?<\/select>/)?.[0] ?? '';
    expect(select).toMatch(/<option value="codex_astra_sol_judge"[^>]*selected=""|<option[^>]*selected=""[^>]*value="codex_astra_sol_judge"/);
    for (const label of ['Opus 5.5, судья Sonnet 5.5', 'gpt-6-astra + gpt-6-sol, судья gpt-6.1-sol', 'gpt-6-astra, без судьи']) expect(select).toContain(label);
    expect(select).not.toContain('не из списка');
    // Nothing but the scheme is chosen for the legs and the judge: no entry per cell, no limit (`LIMITS-01`).
    expect(markup).not.toContain('data-layout-limits');
    const legacy = { ...start(), cells: start().cells.map((c) => (c.row === 'blocks' ? { ...c, model_id: 'claude-opus-5-5' } : c)) };
    expect(view(legacy)).toContain('не из списка');
  });
});

describe('the form «Изменить»', () => {
  const view = (over: Partial<Parameters<typeof LayoutEditorView>[0]> = {}) => renderScreen(newClient(), createElement(LayoutEditorView, {
    draft: initialDraft(LAYOUT, CATALOGUE, ALL_MODELS)!, catalogue: CATALOGUE, availableModelIds: ALL_MODELS, currentKit: 'custom',
    pending: false, problem: null, failure: null, onKit: () => {}, onModel: () => {}, onScheme: () => {}, onEffort: () => {},
    onSave: () => {}, onCancel: () => {}, ...over,
  }));

  it('draws the segments, a model and an effort for each of the six rows, and nothing else to set', () => {
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
    // `LIMITS-01` (`R-153n`, `R-153o`): no «Дополнительно», no answer length and no timeout.
    expect(markup).not.toContain('Дополнительно');
    expect(markup).not.toContain('Ответ, токенов');
    expect(markup).not.toContain('Таймаут');
    expect(markup).not.toContain('<details');
    expect(markup).not.toContain('<input');
    expect(markup).toMatch(/aria-checked="true"[^>]*data-layout-kit="custom"|data-layout-kit="custom"[^>]*aria-checked="true"/);
  });

  it('has, for «Только Codex», three segments, eleven selects and the two buttons: sixteen controls, where it had thirty-three', () => {
    // Counted on the rendered form (R-153f): before `LIMITS-01` the same draft also had the «Дополнительно» summary and two numeric
    // fields for each of the eight cells of the set (the blocks row of «Только Codex» is two legs and a judge): 3 + 11 + 1 + 16 + 2 = 33.
    const markup = view({ draft: chooseKit(initialDraft(LAYOUT, CATALOGUE, ALL_MODELS)!, 'codex_only'), currentKit: 'codex_only' });
    const count = (pattern: RegExp) => (markup.match(pattern) ?? []).length;
    expect({ segments: count(/role="radio"/g), selects: count(/<select/g), inputs: count(/<input/g), summaries: count(/<summary/g), buttons: count(/<button/g) })
      .toEqual({ segments: 3, selects: 11, inputs: 0, summaries: 0, buttons: 5 });
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
    const refusal = new ApiError(422, { contract_version: '1.50.0', error_code: 'validation_failed', message: 'x', correlation_id: 'cid-layout-1', retryable: false, details: { field: 'cells', constraint: 'catalogue' } }, null);
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
    const conflict = (reason: string) => new ApiError(409, { contract_version: '1.50.0', error_code: 'conflict', message: 'x', correlation_id: 'cid-l-2', retryable: false, details: { conflict_reason: reason } }, null);
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

describe('the comparison of versions in the layout (`CMP-WEB-01`)', () => {
  const start = (layout: StageModelLayout = LAYOUT) => initialDraft(layout, CATALOGUE, ALL_MODELS)!;
  const KINDS = [...COMPARISON_LAYOUT_KIND_VALUES];
  /** A catalogue in which Sonnet has no «высокое», to see the effort fall back to one the catalogue allows. */
  const noSonnetHigh: ModelCatalogue = { ...CATALOGUE, items: CATALOGUE.items.map((e) => (e.model_id === 'claude-sonnet-5-5' ? { ...e, efforts: ['low', 'medium'] } : e)) };

  it('names the four kinds in Russian, in the order the server lists them', () => {
    expect(KINDS).toEqual(['comparison_pair_check', 'comparison_sheet_changes', 'comparison_spec', 'comparison_report']);
    expect(KINDS.map((kind) => COMPARISON_KIND_LABELS[kind])).toEqual(['Пары листов', 'Изменения листов', 'Спецификация', 'Отчёт']);
  });

  it('fills «Только Codex» and «Только Claude» with their tables: a model and an effort for each kind, no limit and no window', () => {
    expect(comparisonKitCells('codex_only').map((c) => [c.work_kind, c.model_id, c.effort])).toEqual([
      ['comparison_pair_check', 'gpt-6-luna', 'high'],
      ['comparison_sheet_changes', 'gpt-6.1-sol', 'high'],
      ['comparison_spec', 'gpt-6-luna', 'high'],
      ['comparison_report', 'gpt-6.1-sol', 'high'],
    ]);
    expect(comparisonKitCells('claude_only').map((c) => [c.work_kind, c.model_id, c.effort])).toEqual([
      ['comparison_pair_check', 'claude-sonnet-5-5', 'high'],
      ['comparison_sheet_changes', 'claude-sonnet-5-5', 'high'],
      ['comparison_spec', 'claude-sonnet-5-5', 'high'],
      ['comparison_report', 'claude-sonnet-5-5', 'high'],
    ]);
    // `LIMITS-01`: a comparison cell is the kind, the model and the effort, and nothing the server would refuse as an unknown member.
    expect(comparisonKitCells('claude_only').every((c) => Object.keys(c).sort().join() === 'effort,model_id,work_kind')).toBe(true);
  });

  it('counts the comparison models of a set when it decides whether the set can be offered', () => {
    // Luna is only in the comparison cells of «Только Codex» (at «высокое»; `R-153m`): no row and no blocks scheme uses it.
    const noLunaHigh: ModelCatalogue = { ...CATALOGUE, items: CATALOGUE.items.map((e) => (e.model_id === 'gpt-6-luna' ? { ...e, efforts: ['low', 'medium'] } : e)) };
    expect(kitIsOffered('codex_only', CATALOGUE, ALL_MODELS)).toBe(true);
    expect(kitIsOffered('codex_only', noLunaHigh, ALL_MODELS)).toBe(false);
    expect(kitIsOffered('claude_only', noLunaHigh, ALL_MODELS)).toBe(true);
    expect([...kitModelIds('codex_only')].sort()).toEqual(['gpt-6-astra', 'gpt-6-luna', 'gpt-6-sol', 'gpt-6.1-sol']);
  });

  it('reads the lines of the revision in force in the order of the kinds, and none for a revision that stored none', () => {
    expect(comparisonTable(LAYOUT)).toEqual([]);
    expect(comparisonTable(LAYOUT_EMPTY)).toEqual([]);
    const lines = comparisonTable({ ...LAYOUT_COMPARISON, current: { ...LAYOUT_COMPARISON.current!, comparison_cells: [...COMPARISON_CELLS].reverse() } });
    expect(lines.map((line) => [line.kind, line.label, line.text, line.unavailable])).toEqual([
      ['comparison_pair_check', 'Пары листов', 'gpt-6-astra · высокое', false],
      ['comparison_sheet_changes', 'Изменения листов', 'gpt-6.1-sol · высокое', false],
      ['comparison_spec', 'Спецификация', 'Sonnet 5.5 · среднее', true],
      ['comparison_report', 'Отчёт', 'Opus 5.5 · высокое', false],
    ]);
  });

  describe('the draft', () => {
    it('starts with what the revision stored; a «Свой набор» stored without cells starts with none, and nothing is invented', () => {
      expect(start(LAYOUT).comparison).toEqual([]);
      expect(start(LAYOUT_COMPARISON).comparison).toEqual(COMPARISON_CELLS);
      expect(start(LAYOUT_EMPTY).comparison).toEqual(comparisonKitCells('claude_only'));
    });

    it('fills the four from a set, and «Свой набор» keeps what the draft has', () => {
      const claude = chooseKit(start(LAYOUT), 'claude_only');
      expect(claude.comparison).toEqual(comparisonKitCells('claude_only'));
      const back = chooseKit(claude, 'custom');
      expect(back.comparison).toEqual(claude.comparison);
      expect(chooseKit(start(LAYOUT_COMPARISON), 'custom').comparison).toEqual(COMPARISON_CELLS);
    });

    it('gives a kind a model only when the person chooses one: the high effort the catalogue allows, the other kinds still empty', () => {
      const one = setComparisonModel(start(LAYOUT), 'comparison_report', 'gpt-6-sol', CATALOGUE);
      expect(one.kit).toBe('custom');
      expect(one.comparison).toEqual([{ work_kind: 'comparison_report', model_id: 'gpt-6-sol', effort: 'high' }]);
      expect(setComparisonModel(start(LAYOUT), 'comparison_spec', 'claude-sonnet-5-5', noSonnetHigh).comparison?.[0]?.effort).toBe('medium');
      // An effort of a kind with no model changes nothing: there is nothing to give it to.
      expect(setComparisonEffort(start(LAYOUT), 'comparison_spec', 'low').comparison).toEqual([]);
    });

    it('changes the model and the effort of a kind that has them, and keeps the others as they were', () => {
      const base = start(LAYOUT_COMPARISON);
      const model = setComparisonModel(base, 'comparison_pair_check', 'claude-opus-5-5', CATALOGUE);
      expect(model.comparison?.find((c) => c.work_kind === 'comparison_pair_check')).toMatchObject({ model_id: 'claude-opus-5-5', effort: 'high' });
      // Opus has no «низкое»: a model whose catalogue lacks the effort of the cell takes «среднее».
      const low = setComparisonEffort(base, 'comparison_spec', 'low');
      expect(setComparisonModel(low, 'comparison_spec', 'claude-opus-5-5', CATALOGUE).comparison?.find((c) => c.work_kind === 'comparison_spec')?.effort).toBe('medium');
      expect(model.comparison?.map((c) => c.work_kind)).toEqual(KINDS);
      expect(model.comparison?.filter((c) => c.work_kind !== 'comparison_pair_check')).toEqual(COMPARISON_CELLS.filter((c) => c.work_kind !== 'comparison_pair_check'));
    });

    it('keeps the comparison across an edit of a row and the choice of a block scheme', () => {
      const base = start(LAYOUT_COMPARISON);
      expect(setCellModel(base, 'norms:main', 'gpt-6-sol', CATALOGUE).comparison).toEqual(COMPARISON_CELLS);
      expect(setBlockScheme(base, 'codex_astra_sol_judge').comparison).toEqual(COMPARISON_CELLS);
      expect(setCellEffort(chooseKit(base, 'claude_only'), 'norms:main', 'high').comparison).toEqual(comparisonKitCells('claude_only'));
    });

    it('refuses to save a part of the four and a pair the catalogue lacks, and accepts none or all', () => {
      expect(draftProblem(start(LAYOUT), CATALOGUE)).toBeNull();
      expect(draftProblem(start(LAYOUT_COMPARISON), CATALOGUE)).toBeNull();
      expect(draftProblem(setComparisonModel(start(LAYOUT), 'comparison_spec', 'gpt-6-sol', CATALOGUE), CATALOGUE)).toContain('во всех четырёх строках');
      const three = { ...start(LAYOUT_COMPARISON), comparison: COMPARISON_CELLS.slice(0, 3) };
      expect(draftProblem(three, CATALOGUE)).toContain('во всех четырёх строках');
      expect(draftProblem(setComparisonEffort(start(LAYOUT_COMPARISON), 'comparison_report', 'low'), CATALOGUE)).toContain('сравнения версий');
    });

    it('sends comparison_cells with all four kinds, each once and in the order of the kinds, when they are chosen', () => {
      let draft = start(LAYOUT);
      for (const kind of [...KINDS].reverse()) draft = setComparisonModel(draft, kind, 'gpt-6-astra', CATALOGUE);
      const request = draftRequest(draft);
      expect(request.comparison_cells?.map((c) => c.work_kind)).toEqual(KINDS);
      expect(new Set(request.comparison_cells?.map((c) => c.work_kind)).size).toBe(4);
      expect(draftProblem(draft, CATALOGUE)).toBeNull();
      expect(request.kit).toBe('custom');
      expect(request.cells).toEqual(LAYOUT_CELLS);
      // A named set sends its table.
      expect(draftRequest(chooseKit(start(LAYOUT), 'codex_only')).comparison_cells).toEqual(comparisonKitCells('codex_only'));
    });

    it('sends none for a «Свой набор» with none chosen, so the server stores none and never serves a model nobody chose', () => {
      expect('comparison_cells' in draftRequest(start(LAYOUT))).toBe(false);
      expect(draftRequest(start(LAYOUT))).toEqual({ kit: 'custom', cells: LAYOUT_CELLS });
    });

    it('calls the draft changed when a comparison cell differs from the revision, and unchanged when it does not', () => {
      expect(draftChanged(start(LAYOUT_COMPARISON), LAYOUT_COMPARISON)).toBe(false);
      expect(draftChanged(start(LAYOUT_COMPARISON_KIT), LAYOUT_COMPARISON_KIT)).toBe(false);
      expect(draftChanged(setComparisonEffort(start(LAYOUT_COMPARISON), 'comparison_spec', 'high'), LAYOUT_COMPARISON)).toBe(true);
      expect(draftChanged(setComparisonModel(start(LAYOUT_COMPARISON), 'comparison_pair_check', 'claude-opus-5-5', CATALOGUE), LAYOUT_COMPARISON)).toBe(true);
      // A model chosen for one kind of a revision that stored none is a change, though the six rows are the same.
      expect(draftChanged(setComparisonModel(start(LAYOUT), 'comparison_spec', 'gpt-6-sol', CATALOGUE), LAYOUT)).toBe(true);
    });
  });

  describe('the group in the form «Изменить»', () => {
    const view = (draft = start(LAYOUT_COMPARISON), over: Partial<Parameters<typeof LayoutEditorView>[0]> = {}) => renderScreen(newClient(), createElement(LayoutEditorView, {
      draft, catalogue: CATALOGUE, availableModelIds: ALL_MODELS, currentKit: 'custom', pending: false, problem: null, failure: null,
      onKit: () => {}, onModel: () => {}, onScheme: () => {}, onEffort: () => {},
      onComparisonModel: () => {}, onComparisonEffort: () => {}, onSave: () => {}, onCancel: () => {}, ...over,
    }));
    const select = (markup: string, attribute: string) => markup.match(new RegExp(`<select[^>]*${attribute}[^>]*>[\\s\\S]*?</select>`))?.[0] ?? '';

    it('draws under «Свой набор» one small group of four rows: the kind in Russian, a model and an effort', () => {
      const markup = view();
      expect(markup.match(/data-layout-comparison-group/g)).toHaveLength(1);
      expect(markup).toContain('aria-label="Сравнение версий"');
      expect(markup.match(/data-layout-comparison-model=/g)).toHaveLength(4);
      expect(markup.match(/data-layout-comparison-effort=/g)).toHaveLength(4);
      for (const kind of KINDS) expect(markup).toContain(`data-comparison-kind="${kind}"`);
      for (const label of ['Пары листов', 'Изменения листов', 'Спецификация', 'Отчёт']) expect(markup).toContain(`>${label}<`);
      expect(select(markup, 'data-layout-comparison-model="comparison_spec"')).toMatch(/<option[^>]*value="claude-sonnet-5-5"[^>]*>Sonnet 5.5<\/option>/);
      expect(select(markup, 'data-layout-comparison-effort="comparison_spec"')).toMatch(/<option(?=[^>]*selected="")[^>]*>среднее<\/option>/);
      // The six rows are unchanged beside it.
      expect(markup.match(/data-layout-model=/g)).toHaveLength(5);
      expect(markup).not.toContain('data-layout-comparison-none');
    });

    it('offers a kind the models some server serves, and the one it has even when no server serves it', () => {
      const markup = view(start(LAYOUT_COMPARISON), { availableModelIds: CLAUDE_ONLY_MODELS });
      const pair = select(markup, 'data-layout-comparison-model="comparison_pair_check"');
      expect(pair).toContain('value="gpt-6-astra"');
      expect(pair).toContain('value="claude-opus-5-5"');
      expect(pair).not.toContain('value="gpt-6-sol"');
    });

    it('offers an effort only from the model\'s list: Opus has no «низкое»', () => {
      const markup = view(setComparisonModel(start(LAYOUT_COMPARISON), 'comparison_report', 'claude-opus-5-5', CATALOGUE));
      const report = select(markup, 'data-layout-comparison-effort="comparison_report"');
      expect(report).toContain('среднее');
      expect(report).toContain('высокое');
      expect(report).not.toContain('низкое');
    });

    it('draws nothing of it under a named set: the set\'s table applies', () => {
      for (const kit of ['claude_only', 'codex_only'] as const) {
        const markup = view(chooseKit(start(LAYOUT_COMPARISON), kit), { currentKit: kit });
        expect(markup, kit).not.toContain('data-layout-comparison');
        expect(markup, kit).not.toContain('data-comparison-kind');
        expect(markup, kit).not.toContain('Сравнение версий');
        expect(markup, kit).toContain('data-layout-editor');
      }
      expect(view(start(LAYOUT_COMPARISON_KIT), { currentKit: 'codex_only' })).not.toContain('Сравнение версий');
    });

    it('shows a stored «Свой набор» without cells with four empty rows and one line saying the comparison will not run; it invents no model', () => {
      const markup = view(start(LAYOUT));
      expect(markup).toContain(COMPARISON_NONE_NOTE);
      expect(markup).toContain('Сравнения версий не запустятся, пока модели не выбраны');
      expect(markup.match(/data-layout-comparison-none/g)).toHaveLength(1);
      for (const kind of KINDS) {
        const model = select(markup, `data-layout-comparison-model="${kind}"`);
        expect(model, kind).toMatch(/<option(?=[^>]*selected="")[^>]*>не выбрана<\/option>/);
        expect(select(markup, `data-layout-comparison-effort="${kind}"`), kind).toMatch(/disabled=""/);
      }
      expect(markup).not.toContain('data-layout-comparison-limits');
    });

    it('has no limit and no timeout for a chosen kind either: the four rows are a model and an effort and the form has no numeric field', () => {
      const markup = view();
      expect(markup).not.toContain('data-layout-comparison-limits');
      expect(markup).not.toContain('Дополнительно');
      expect(markup).not.toContain('<input');
      expect(markup.match(/data-layout-comparison-model=/g)).toHaveLength(4);
    });

    it('says in words what stops a partial choice and disables saving', () => {
      const partial = setComparisonModel(start(LAYOUT), 'comparison_spec', 'gpt-6-sol', CATALOGUE);
      const problem = draftProblem(partial, CATALOGUE);
      expect(problem).toContain('во всех четырёх строках');
      const markup = view(partial, { problem });
      expect(markup).toContain('data-layout-problem');
      expect(markup).toMatch(/data-layout-save[^>]*disabled=""|disabled=""[^>]*data-layout-save/);
    });
  });

  describe('the table of «Модели по этапам»', () => {
    const table = (layout: StageModelLayout, admin = false) => renderScreen(newClient(), createElement(StageModelsTable, { layout, admin, ...(admin ? { onEdit: () => {} } : {}) }));

    it('folds one line «Сравнение версий» under the six rows, with a line for each kind, to an expert and an administrator alike', () => {
      for (const admin of [false, true]) {
        const markup = table(LAYOUT_COMPARISON, admin);
        expect(markup.match(/<details[^>]*data-layout-comparison-group/g)).toHaveLength(1);
        expect(markup).toMatch(/<summary>Сравнение версий<\/summary>/);
        expect(markup.match(/data-comparison-kind=/g)).toHaveLength(4);
        expect(markup).toContain('Пары листов: gpt-6-astra · высокое');
        expect(markup).toContain('Отчёт: Opus 5.5 · высокое');
        // The six rows are the same six.
        expect(markup.match(/data-layout-cell=/g)).toHaveLength(6);
      }
    });

    it('is closed by default and adds no control: no button, no select, no input for an expert', () => {
      const markup = table(LAYOUT_COMPARISON);
      expect(markup).not.toMatch(/<details[^>]*\sopen/);
      expect(markup).not.toContain('<select');
      expect(markup).not.toContain('<input');
      expect(markup).not.toContain('<button');
    });

    it('marks only the kind whose model no server serves', () => {
      const markup = table(LAYOUT_COMPARISON);
      const spec = markup.match(/<li[^>]*data-comparison-kind="comparison_spec"[\s\S]*?<\/li>/)?.[0] ?? '';
      expect(spec).toContain('⚠ нет на серверах');
      expect(spec).toContain('data-host-reason="not_on_any_server"');
      const pair = markup.match(/<li[^>]*data-comparison-kind="comparison_pair_check"[\s\S]*?<\/li>/)?.[0] ?? '';
      expect(pair).not.toContain('нет на серверах');
      // The row of the critic is marked in the table above, as before; the comparison adds one mark more and no more.
      expect(markup.match(/нет на серверах/g)).toHaveLength(2);
    });

    it('reads the lines of a named set the same way', () => {
      const markup = table(LAYOUT_COMPARISON_KIT);
      expect(markup.match(/data-comparison-kind=/g)).toHaveLength(4);
      expect(markup).toContain('Спецификация: gpt-6.1-sol · высокое');
    });

    it('says in one sentence that nothing will run when a «Свой набор» stored none, and folds nothing', () => {
      const markup = table(LAYOUT);
      expect(markup).toContain(COMPARISON_NONE_NOTE);
      expect(markup.match(/data-layout-comparison-none/g)).toHaveLength(1);
      expect(markup).not.toContain('<details');
      expect(markup).not.toContain('data-comparison-kind');
    });

    it('draws nothing of the comparison before a revision exists', () => {
      const markup = table(LAYOUT_EMPTY, true);
      expect(markup).not.toContain('Сравнен');
      expect(markup).not.toContain('data-comparison-kind');
    });
  });
});
