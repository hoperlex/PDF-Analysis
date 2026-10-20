/**
 * How a pass and its proposals are said (`W60-OPT-PROPOSALS-01`): every label table covers its
 * contract enum exactly, every figure is the API's exact text regrouped and never a rounded
 * number, and an absent saving is said to be unknown — never `0`.
 */

import { describe, expect, it } from 'vitest';

import {
  PROPOSAL_ANALOG_BASIS_VALUES,
  PROPOSAL_DECISION_STATE_VALUES,
  PROPOSAL_MATCH_BASIS_VALUES,
  PROPOSAL_VERDICT_VALUES,
  VENDOR_LIST_SCOPE_VALUES,
} from '@/shared/api';
import {
  ANALOG_BASIS_LABELS,
  DECISION_STATES,
  DECISION_STATE_LABELS,
  MATCH_BASIS_LABELS,
  VENDOR_LIST_SCOPE_LABELS,
  VERDICT_LABELS,
  describeCounts,
  describeProvenance,
  describeQuantity,
  describeSaving,
  formatAmount,
  formatDecimal,
  proposalsCsvFileName,
} from '@/entities/optimisation-proposal';

import { pass, proposal, tapeProposal } from './fixtures';

describe('the label tables', () => {
  it('cover exactly the contract’s enums, so a new member is a type error and a red test', () => {
    expect(Object.keys(DECISION_STATE_LABELS).sort()).toEqual([...PROPOSAL_DECISION_STATE_VALUES].sort());
    expect(Object.keys(VERDICT_LABELS).sort()).toEqual([...PROPOSAL_VERDICT_VALUES].sort());
    expect(Object.keys(MATCH_BASIS_LABELS).sort()).toEqual([...PROPOSAL_MATCH_BASIS_VALUES].sort());
    expect(Object.keys(ANALOG_BASIS_LABELS).sort()).toEqual([...PROPOSAL_ANALOG_BASIS_VALUES].sort());
    expect(Object.keys(VENDOR_LIST_SCOPE_LABELS).sort()).toEqual([...VENDOR_LIST_SCOPE_VALUES].sort());
    expect([...DECISION_STATES].sort()).toEqual([...PROPOSAL_DECISION_STATE_VALUES].sort());
  });

  it('are Russian words, not the API’s identifiers', () => {
    const all = [
      ...Object.values(DECISION_STATE_LABELS),
      ...Object.values(VERDICT_LABELS),
      ...Object.values(MATCH_BASIS_LABELS),
      ...Object.values(ANALOG_BASIS_LABELS),
      ...Object.values(VENDOR_LIST_SCOPE_LABELS),
    ];
    for (const label of all) expect(label).not.toMatch(/[A-Za-z_]/);
  });
});

describe('exact figures', () => {
  it('regroups the digits and turns the point into the decimal comma, without rounding', () => {
    expect(formatDecimal('17998')).toBe('17 998');
    expect(formatDecimal('21000.5')).toBe('21 000,5');
    expect(formatDecimal('0.6666')).toBe('0,6666');
    expect(formatDecimal('0.0000025')).toBe('0,0000025');
    expect(formatDecimal('12345678.123456')).toBe('12 345 678,123456');
    expect(formatAmount('650', 'EUR')).toBe('650 евро');
    expect(formatAmount('1', 'XYZ')).toBe('1 XYZ');
  });

  it('says a saving where the API states one, in the price list’s currency', () => {
    expect(describeSaving(proposal())).toBe('Экономия: 17 998 руб.');
  });

  it('says an absent saving is not computed, and never shows a zero for it', () => {
    const said = describeSaving(tapeProposal());
    expect(said).toBe('Экономия не рассчитана: в спецификации количество не записано числом.');
    expect(said).not.toMatch(/\b0\b/);
    expect(describeSaving(proposal({ quantity: '0', saving: '0' }))).toBe('Экономия: 0 руб.');
  });

  it('shows a numeric quantity with its unit and a non-numeric one as the specification wrote it', () => {
    expect(describeQuantity(proposal())).toBe('4 шт');
    expect(describeQuantity(tapeProposal())).toBe('«-» (не число), единица: компл');
    expect(describeQuantity(tapeProposal({ quantity_text: null }))).toBe('«не указано» (не число), единица: компл');
  });

  it('says where the row is in the drawings', () => {
    expect(describeProvenance(proposal())).toBe('страница 2, лист 10, строки 3–4, позиция 1');
    expect(describeProvenance(proposal({ sheet_label: null, line_end: 3, row_position: null }))).toBe(
      'страница 2, строка 3',
    );
  });

  it('counts the proposals by decision, in the order of the states', () => {
    expect(describeCounts(pass())).toBe('не решено — 1, принято — 0, отклонено — 0, на доработку — 1');
  });

  it('suggests a file name from the pass identity alone', () => {
    expect(proposalsCsvFileName('opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8N')).toBe(
      'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8N-proposals.csv',
    );
  });
});
