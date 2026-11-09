/**
 * `D-495`: the «Память решений» tab keeps its filters and its open case in the address, and the knowledge base's own address knows
 * the tab as a fourth «Тип».
 *
 * Each case can fail: the value outside a closed set is the default and is never echoed; the default is the ABSENT parameter; a
 * case id is read against the contract's pattern; a parameter of another screen is carried through; leaving the tab takes the tab's
 * parameters off the address and nothing else.
 */

import { describe, expect, it } from 'vitest';

import { DEFAULT_KB_ADDRESS, KB_KINDS, readKbAddress, writeKbAddress } from '@/_pages/knowledge-base/model/address';
import {
  DEFAULT_MEMORY_ADDRESS,
  MEMORY_PARAMS,
  readMemoryAddress,
  writeMemoryAddress,
} from '@/_pages/knowledge-base/model/memory-address';
import { NO_MEMORY_FILTERS, memoryFiltersNarrow, memoryListQuery } from '@/entities/decision-memory';

import { CASE_A, PROJECT } from './memory-fixtures';

const read = (query: string) => readMemoryAddress(new URLSearchParams(query));
const write = (query: string, next: Parameters<typeof writeMemoryAddress>[1]) =>
  writeMemoryAddress(new URLSearchParams(query), next).toString();

describe('the memory tab’s address, read', () => {
  it('names the five filters and the open case; an empty address is the whole list', () => {
    expect(read(`mstatus=withdrawn&mverdict=rejected&mcategory=roof&msection=KJ&mclass=real&mcase=${CASE_A}`)).toEqual({
      filters: { status: 'withdrawn', verdict: 'rejected', category: 'roof', section: 'KJ', dataClass: 'real' },
      caseId: CASE_A,
    });
    expect(read('')).toEqual(DEFAULT_MEMORY_ADDRESS);
    expect(read('mstatus=&mverdict=&mcategory=&msection=&mclass=&mcase=')).toEqual(DEFAULT_MEMORY_ADDRESS);
  });

  it('drops a value outside the closed sets instead of echoing it', () => {
    expect(read('mstatus=deleted&mverdict=pending&mcategory=weather&msection=ZZ&mclass=demo')).toEqual(DEFAULT_MEMORY_ADDRESS);
    expect(read('mstatus=ACTIVE').filters.status).toBe('all');
  });

  it('reads a case id against the contract pattern, so the address cannot make the page ask for anything else', () => {
    expect(read('mcase=dmc_short').caseId).toBeNull();
    expect(read(`mcase=${CASE_A}x`).caseId).toBeNull();
    expect(read('mcase=prj_01M2545JSD15ETSNNV904X991F').caseId).toBeNull();
    expect(read(`mcase=${CASE_A}`).caseId).toBe(CASE_A);
  });
});

describe('the memory tab’s address, written', () => {
  it('writes what is not the default, and the default is the absent parameter', () => {
    expect(write('', { ...DEFAULT_MEMORY_ADDRESS, filters: { ...NO_MEMORY_FILTERS, status: 'withdrawn', dataClass: 'real' } })).toBe(
      'mstatus=withdrawn&mclass=real',
    );
    expect(write('mstatus=withdrawn&mcase=' + CASE_A, DEFAULT_MEMORY_ADDRESS)).toBe('');
    expect(write('', { ...DEFAULT_MEMORY_ADDRESS, caseId: CASE_A })).toBe(`mcase=${CASE_A}`);
  });

  it('carries the project, the type and any other parameter through', () => {
    expect(write(`project=${PROJECT}&kind=memory&foo=bar`, { ...DEFAULT_MEMORY_ADDRESS, caseId: CASE_A })).toBe(
      `project=${PROJECT}&kind=memory&foo=bar&mcase=${CASE_A}`,
    );
  });

  it('round-trips every value of every filter', () => {
    for (const status of ['all', 'active', 'withdrawn', 'forgotten'] as const) {
      for (const verdict of ['all', 'accepted', 'rejected'] as const) {
        for (const dataClass of ['all', 'test', 'real'] as const) {
          const next = { filters: { status, verdict, category: 'fire_safety', section: 'PS', dataClass }, caseId: CASE_A };
          expect(read(write('', next))).toEqual(next);
        }
      }
    }
  });
});

describe('the knowledge base’s address knows the tab', () => {
  it('«Память решений» is a «Тип» of the closed set, and not the default', () => {
    expect(KB_KINDS).toContain('memory');
    expect(readKbAddress(new URLSearchParams('kind=memory')).kind).toBe('memory');
    expect(readKbAddress(new URLSearchParams('kind=archive')).kind).toBe(DEFAULT_KB_ADDRESS.kind);
    expect(writeKbAddress(new URLSearchParams(''), { ...DEFAULT_KB_ADDRESS, kind: 'memory' }).toString()).toBe('kind=memory');
  });

  it('leaving the tab takes its filters and its open case off the address, and nothing else', () => {
    const inTab = `project=${PROJECT}&kind=memory&mstatus=withdrawn&mcase=${CASE_A}&foo=bar`;
    expect(writeKbAddress(new URLSearchParams(inTab), { ...DEFAULT_KB_ADDRESS, kind: 'findings' }).toString()).toBe(
      `project=${PROJECT}&foo=bar`,
    );
    // Staying in the tab leaves them alone (a change of the journal’s own view does not reach them).
    expect(writeKbAddress(new URLSearchParams(inTab), { ...DEFAULT_KB_ADDRESS, kind: 'memory', view: 'events' }).toString()).toBe(
      `project=${PROJECT}&kind=memory&mstatus=withdrawn&mcase=${CASE_A}&foo=bar&view=events`,
    );
  });

  it('removes every parameter the tab owns', () => {
    const all = new URLSearchParams(MEMORY_PARAMS.map((name) => `${name}=x`).join('&'));
    expect(writeKbAddress(all, DEFAULT_KB_ADDRESS).toString()).toBe('');
  });
});

describe('the list query', () => {
  it('leaves out what is «all», and sends the project as the origin', () => {
    expect(memoryListQuery(NO_MEMORY_FILTERS, null)).toEqual({});
    expect(
      memoryListQuery({ status: 'withdrawn', verdict: 'accepted', category: 'roof', section: 'AR', dataClass: 'real' }, PROJECT, 'cur'),
    ).toEqual({
      status: 'withdrawn',
      verdict: 'accepted',
      category: 'roof',
      section_code: 'AR',
      data_class: 'real',
      origin_project_uid: PROJECT,
      cursor: 'cur',
    });
  });

  it('knows when a filter narrows the list', () => {
    expect(memoryFiltersNarrow(NO_MEMORY_FILTERS)).toBe(false);
    expect(memoryFiltersNarrow({ ...NO_MEMORY_FILTERS, section: 'KJ' })).toBe(true);
  });
});
