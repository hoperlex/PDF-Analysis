/**
 * The stage dictionary, held to the contracts that decide it (`RUN-SCREEN-01a`).
 *
 * `entities/audit-run/model/stage-dictionary.ts` is the one place that says which code ids a reader's chip covers, what it is
 * called and whether its work calls a model. The rail, the «Этапы анализа раздела» dialog and the extended review's batch panel read
 * it. It restates something `contracts/analysis/v1/stage-registry.json` already declares (which stages are model-routed), and a copy
 * drifts in silence, so this file reads the registry and judges the dictionary against it.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { STAGE_ID_VALUES } from '@/shared/api';
import {
  RUN_CHIP, RUN_CHIPS, RUN_CHIP_IDS, chipById, chipOfStage, phaseFullLabel,
} from '@/entities/audit-run';
import { BatchProgress } from '@/widgets/extended-review/ui/batch-progress';
import { CHIP_ALGORITHMS } from '@/widgets/run-stages-dialog';

import { REPO_ROOT, WEB_ROOT, readJson } from './lib/repo';

interface Registry {
  readonly stages: readonly { readonly stage_id: string; readonly purpose: string; readonly execution?: { readonly model_routed?: boolean } }[];
}

const registry = readJson<Registry>(join(REPO_ROOT, 'contracts', 'analysis', 'v1', 'stage-registry.json'));

/** The extended review's procedure that is a chip of its own but not a contract stage. */
const PROCEDURE_ONLY = ['comprehensive_analysis'];

describe('the eight chips', () => {
  it('are eight, in the rail\'s order, each with an id of its own', () => {
    expect(RUN_CHIPS.map((chip) => chip.id)).toEqual([...RUN_CHIP_IDS]);
    expect(RUN_CHIPS).toHaveLength(8);
    expect(new Set(RUN_CHIPS.map((chip) => chip.id)).size).toBe(8);
    for (const id of RUN_CHIP_IDS) expect(RUN_CHIP[id]).toBe(chipById(id));
  });

  it('name Подготовка, Текст, Блоки, Сверка, Свод, Нормы, Критик and Уточнение on the rail', () => {
    expect(RUN_CHIPS.map((chip) => chip.short)).toEqual([
      'Подготовка', 'Текст', 'Блоки', 'Сверка', 'Свод', 'Нормы', 'Критик', 'Уточнение',
    ]);
  });

  it('are named in the reader\'s language, short and full, and never by an identifier', () => {
    for (const chip of RUN_CHIPS) {
      for (const label of [chip.short, chip.full]) {
        expect({ id: chip.id, cyrillic: /[а-яА-Я]/.test(label) }).toEqual({ id: chip.id, cyrillic: true });
        expect({ id: chip.id, identifier: chip.stageIds.includes(label) || label.includes('_') }).toEqual({ id: chip.id, identifier: false });
      }
      expect({ id: chip.id, fitsAChip: chip.short.length <= 14 }).toEqual({ id: chip.id, fitsAChip: true });
    }
    // The eight carry no Latin word at all.
    for (const chip of RUN_CHIPS) {
      expect({ id: chip.id, latin: /[A-Za-z]/.test(chip.short + chip.full) }).toEqual({ id: chip.id, latin: false });
    }
  });
});

describe('the dictionary is the registry\'s, not a recollection of it', () => {
  it('puts every contract stage into exactly one chip, and covers nothing else but the review\'s own procedure', () => {
    const covered = RUN_CHIPS.flatMap((chip) => [...chip.stageIds]);
    expect(new Set(covered).size, 'an id is in two chips').toBe(covered.length);
    expect([...covered].filter((id) => !PROCEDURE_ONLY.includes(id)).sort()).toEqual([...STAGE_ID_VALUES].sort());
    expect(registry.stages.map((stage) => stage.stage_id).sort()).toEqual([...STAGE_ID_VALUES].sort());
    for (const id of STAGE_ID_VALUES) expect(chipOfStage(id), id).not.toBeNull();
    expect(chipOfStage('comprehensive_analysis')?.id).toBe('cross_check');
  });

  it('says a chip calls a model exactly when the registry routes its stages to one', () => {
    for (const chip of RUN_CHIPS) {
      const routed = registry.stages.filter((stage) => chip.stageIds.includes(stage.stage_id)).map((stage) => stage.execution?.model_routed === true);
      if (routed.length === 0) continue; // the procedure-only chip has no registry row
      expect({ id: chip.id, agree: routed.every((flag) => flag === routed[0]), callsModel: routed[0] }).toEqual({
        id: chip.id, agree: true, callsModel: chip.callsModel,
      });
    }
    // Non-vacuous: the dictionary has both kinds, and the two the plan names as model-free are the ones without.
    expect(RUN_CHIPS.filter((chip) => !chip.callsModel).map((chip) => chip.short)).toEqual(['Подготовка', 'Свод']);
    expect(RUN_CHIP.cross_check.callsModel).toBe(true);
  });

  it('names no chip for the report phase, which has none', () => {
    expect(chipOfStage('report_generation')).toBeNull();
    expect(phaseFullLabel('report_generation')).toBeNull();
    expect(phaseFullLabel('block_analysis')).toBe(RUN_CHIP.blocks.full);
  });
});

describe('«Как устроен этап»', () => {
  it('has a memo for every chip: three or four steps, a one-line summary, the last step the result', () => {
    for (const chip of RUN_CHIPS) {
      const memo = CHIP_ALGORITHMS[chip.id];
      expect({ id: chip.id, steps: memo.steps.length >= 3 && memo.steps.length <= 4 }).toEqual({ id: chip.id, steps: true });
      expect(memo.summary.trim()).not.toBe('');
      for (const text of [memo.summary, ...memo.steps]) expect(/[а-яА-Я]/.test(text), text).toBe(true);
    }
  });

  it('says in its summary which chips call no model, because they are the ones the registry says are central', () => {
    for (const chip of RUN_CHIPS) {
      expect({ id: chip.id, says: CHIP_ALGORITHMS[chip.id].summary.includes('Модель не вызывается') }).toEqual({ id: chip.id, says: !chip.callsModel });
    }
  });
});

describe('one name for one phase, everywhere', () => {
  it('calls the block phase the same on the rail and in the batch panel (it said «Анализ изображений»)', () => {
    const markup = renderToStaticMarkup(createElement(BatchProgress, {
      batches: [], coverage: { block_analysis: { completed: 1, planned: 3, remaining: 2, processed_items: 4, total_items: 9, limit: 3 } },
    }));
    expect(markup).toContain(`<h4>${RUN_CHIP.blocks.full}</h4>`);
    expect(markup).not.toContain('Анализ изображений');
  });

  it('keeps the batch panel\'s source from naming the block phase itself', () => {
    const source = readFileSync(join(WEB_ROOT, 'src', 'widgets', 'extended-review', 'ui', 'batch-progress.tsx'), 'utf8');
    expect(source).toContain('RUN_CHIP.blocks.full');
    expect(source).not.toContain("'Анализ изображений'");
  });
});
