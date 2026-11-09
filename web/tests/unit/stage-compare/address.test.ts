/**
 * The address of «Сравнение стадий» and of «Сравнение версий» (`UI-B-93`, `UI-B-102`): what is read from a query and what is written
 * back. Pure, so every case is a literal. The properties that matter: a run means nothing without its pair, an unknown tab is the
 * first step, the first step and the table are the absent `tab`, and a write never touches the project or a parameter it does not own.
 */

import { describe, expect, it } from 'vitest';

import { readMapOpen, readStageAddress, writeMapOpen, writeStageAddress } from '@/_pages/stage-compare/model/address';
import { STAGE_TAB_LABELS, stageTabAfterKey } from '@/_pages/stage-compare/model/tabs';
import { readCompareAddress, writeCompareAddress } from '@/_pages/version-compare/model/address';

const q = (text: string): URLSearchParams => new URLSearchParams(text);

describe('the address of «Сравнение стадий»', () => {
  it('reads the pair, the run and the step', () => {
    expect(readStageAddress(q('project=prj_1&pair=stp_1&run=crn_1&tab=changes'))).toEqual({ pairId: 'stp_1', runId: 'crn_1', tab: 'changes' });
  });

  it('reads an empty address as no pair, no run, the first step', () => {
    expect(readStageAddress(q(''))).toEqual({ pairId: '', runId: null, tab: 'documentation' });
  });

  it('drops a run that has no pair, and reads an unknown step as the first', () => {
    expect(readStageAddress(q('run=crn_1&tab=nonsense'))).toEqual({ pairId: '', runId: null, tab: 'documentation' });
  });

  it('writes the three parameters and leaves the project and the rest where they are', () => {
    const written = writeStageAddress(q('project=prj_1&x=1'), { pairId: 'stp_1', runId: 'crn_1', tab: 'sheets' });
    expect(written.toString()).toBe('project=prj_1&x=1&pair=stp_1&run=crn_1&tab=sheets');
  });

  it('writes the first step and a missing run as absent parameters', () => {
    const written = writeStageAddress(q('project=prj_1&pair=stp_1&run=crn_1&tab=changes'), { pairId: 'stp_1', runId: null, tab: 'documentation' });
    expect(written.toString()).toBe('project=prj_1&pair=stp_1');
  });

  it('writes no run and no pair-less step when the pair is cleared', () => {
    const written = writeStageAddress(q('pair=stp_1&run=crn_1&tab=sheets'), { pairId: '', runId: 'crn_1', tab: 'sheets' });
    expect(written.toString()).toBe('tab=sheets');
  });

  it('round-trips', () => {
    const address = { pairId: 'stp_9', runId: 'crn_9', tab: 'journal' } as const;
    expect(readStageAddress(writeStageAddress(q(''), address))).toEqual(address);
  });
});

describe('the keyboard on the four steps', () => {
  it('moves with the arrows, wraps, and answers Home and End', () => {
    expect(stageTabAfterKey('documentation', 'ArrowRight')).toBe('sheets');
    expect(stageTabAfterKey('journal', 'ArrowRight')).toBe('documentation');
    expect(stageTabAfterKey('documentation', 'ArrowLeft')).toBe('journal');
    expect(stageTabAfterKey('changes', 'Home')).toBe('documentation');
    expect(stageTabAfterKey('changes', 'End')).toBe('journal');
  });

  it('ignores every other key', () => {
    expect(stageTabAfterKey('sheets', 'Enter')).toBeNull();
    expect(stageTabAfterKey('sheets', 'a')).toBeNull();
  });

  it('names the steps as the original does', () => {
    expect(Object.values(STAGE_TAB_LABELS)).toEqual(['1. Загрузка документации', '2. Сопоставление листов', '3. Изменения проекта', '4. Отчёт']);
  });
});

describe('the address of «Сравнение версий»', () => {
  it('reads the open set and the tab', () => {
    expect(readCompareAddress(q('project=prj_1&set=doc_1&tab=sheets'))).toEqual({ documentUid: 'doc_1', tab: 'sheets' });
  });

  it('reads the table when there is no set, even if the tab says otherwise', () => {
    expect(readCompareAddress(q('tab=sheets'))).toEqual({ documentUid: null, tab: 'projects' });
    expect(readCompareAddress(q(''))).toEqual({ documentUid: null, tab: 'projects' });
  });

  it('keeps the set but shows the table when the tab is the table', () => {
    expect(readCompareAddress(q('set=doc_1'))).toEqual({ documentUid: 'doc_1', tab: 'projects' });
  });

  it('writes set and tab, and drops the tab for the table', () => {
    expect(writeCompareAddress(q('project=prj_1'), { documentUid: 'doc_1', tab: 'sheets' }).toString()).toBe('project=prj_1&set=doc_1&tab=sheets');
    expect(writeCompareAddress(q('project=prj_1&set=doc_1&tab=sheets'), { documentUid: 'doc_1', tab: 'projects' }).toString()).toBe('project=prj_1&set=doc_1');
    expect(writeCompareAddress(q('project=prj_1&set=doc_1&tab=sheets'), { documentUid: null, tab: 'sheets' }).toString()).toBe('project=prj_1');
  });
});

describe('the fold of the sheet map in the address (UI-B-93)', () => {
  it('reads the map as open unless the address folds it', () => {
    expect(readMapOpen(q(''))).toBe(true);
    expect(readMapOpen(q('map=closed'))).toBe(false);
    expect(readMapOpen(q('map=open'))).toBe(true);
    expect(readMapOpen(q('map=anything'))).toBe(true);
  });

  it('writes the fold as map=closed and the open map as no parameter, carrying every other parameter through', () => {
    expect(writeMapOpen(q('project=prj_1&pair=stp_1&tab=sheets'), false).toString()).toBe('project=prj_1&pair=stp_1&tab=sheets&map=closed');
    expect(writeMapOpen(q('project=prj_1&map=closed&tab=sheets'), true).toString()).toBe('project=prj_1&tab=sheets');
    expect(writeMapOpen(q(''), true).toString()).toBe('');
  });

  it('round-trips, and leaves the pair, the run and the step to their own functions', () => {
    for (const open of [true, false]) expect(readMapOpen(writeMapOpen(q(''), open))).toBe(open);
    const withFold = q('pair=stp_1&run=crn_1&tab=changes&map=closed');
    expect(readStageAddress(withFold)).toEqual({ pairId: 'stp_1', runId: 'crn_1', tab: 'changes' });
    expect(writeStageAddress(withFold, { pairId: 'stp_2', runId: null, tab: 'sheets' }).toString()).toBe('pair=stp_2&tab=sheets&map=closed');
  });
});
