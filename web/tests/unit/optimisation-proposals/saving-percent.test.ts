/**
 * `UI-B-07` (contract 1.40.0): the percent beside a proposal's saving, as the server computed it.
 *
 * The card words `OptimisationProposal.saving_percent` and does no arithmetic on the prices: a figure that disagrees with
 * the two prices is shown as it came, which is the proof that nothing here divides. It is a difference of prices, so it
 * stands where the saving is «не рассчитана», and a proposal without the field shows nothing in its place.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { describeSaving, describeSavingPercent, formatSavingPercent } from '@/entities/optimisation-proposal';
import { ProposalCard } from '@/widgets/optimisation-proposals';

import { newClient, renderScreen } from '../screens/harness';
import { proposal, tapeProposal } from './fixtures';

const MINUS = '−';

function card(overrides: Parameters<typeof proposal>[0]): string {
  return renderScreen(newClient(), createElement(ProposalCard, { proposal: proposal(overrides), controls: null, history: null }));
}

function tapeCard(overrides: Parameters<typeof tapeProposal>[0]): string {
  return renderScreen(newClient(), createElement(ProposalCard, { proposal: tapeProposal(overrides), controls: null, history: null }));
}

describe('the percent as a text', () => {
  it('is the server’s text with a minus, a decimal comma and the percent sign', () => {
    expect(formatSavingPercent('25')).toBe(`${MINUS}25 %`);
    expect(formatSavingPercent('33.33')).toBe(`${MINUS}33,33 %`);
    expect(formatSavingPercent('0.5')).toBe(`${MINUS}0,5 %`);
    expect(formatSavingPercent('100')).toBe(`${MINUS}100 %`);
  });

  it('has no sign when it rounded to nothing', () => {
    expect(formatSavingPercent('0')).toBe('0 %');
  });

  it('says what it is a percent of, and is null for a proposal that carries none', () => {
    expect(describeSavingPercent(proposal({ saving_percent: '16' }))).toBe(`${MINUS}16 % к цене в прайс-листе`);
    expect(describeSavingPercent(proposal())).toBeNull();
  });
});

describe('the card', () => {
  it('shows the percent beside the saving amount', () => {
    const markup = card({ saving_percent: '16' });
    const saving = describeSaving(proposal({ saving_percent: '16' }));
    expect(saving).toMatch(/^Экономия: 17.998 руб\.$/);
    expect(markup).toContain(saving);
    expect(markup).toContain(`data-saving-percent="16"`);
    expect(markup).toContain(`${MINUS}16 % к цене в прайс-листе`);
    expect(markup.indexOf(saving)).toBeLessThan(markup.indexOf('data-saving-percent'));
  });

  it('shows the percent where the amount is «не рассчитана», and still shows no zero amount', () => {
    const markup = tapeCard({ saving_percent: '12.5' });
    expect(markup).toContain('Экономия не рассчитана: в спецификации количество не записано числом.');
    expect(markup).toContain(`${MINUS}12,5 % к цене в прайс-листе`);
    expect(markup).not.toContain('Экономия: 0');
  });

  it('shows nothing in place of a percent the proposal does not carry', () => {
    for (const markup of [card({}), tapeCard({})]) {
      expect(markup).not.toContain('data-saving-percent');
      expect(markup).not.toContain('к цене в прайс-листе');
    }
    expect(card({})).toContain(describeSaving(proposal()));
  });

  it('does no arithmetic on the prices: a figure that disagrees with them is shown as it came', () => {
    // 25 000 against 21 000,5 is about 16 %, and the card says what the server said.
    const markup = card({ saving_percent: '99' });
    expect(markup).toContain(`${MINUS}99 % к цене в прайс-листе`);
    expect(markup).not.toContain(`${MINUS}16 %`);
  });
});
