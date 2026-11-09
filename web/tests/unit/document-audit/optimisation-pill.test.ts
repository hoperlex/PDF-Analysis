/**
 * `D-361` (contract 1.43.0, `UI-A-46` second half): the original's second pill on a document card, «Оптимизация N [метка]».
 *
 * The server counts (`DocumentAudit.optimisation_proposal_count` and `optimisation_undecided_count`: the proposals of the version's
 * latest optimisation pass and those with no decision in force); the screen words them. Held, each with a case that shows it can fail:
 *
 *   - the model says the count and, only while some wait for an expert, the marker; it says nothing where the server read no
 *     optimisation (the counts are absent -- never a zero) and nothing for a pass that produced no proposal;
 *   - the card draws the pill beside «Замечания N», on the card of a document that has one, and no wrapper on any other;
 *   - the pill is a fact beside the audit chip: the chip's words are the ones they were with and without it.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DocumentAudit } from '@/shared/api';
import { DocumentCardGrid, auditChip, optimisationPill } from '@/entities/document-version';

import { newClient, renderWith } from '../screens/harness';
import { classification, version } from '../sections/fixtures';

const RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

function audit(over: Partial<DocumentAudit> = {}): DocumentAudit {
  return { state: 'awaiting_decision', partial: false, result_run_id: RUN, finding_count: 3, undecided_finding_count: 1, ...over };
}

const addresses = () => ({ href: '/v', documentHref: '/d' });
const card = (over: Partial<DocumentAudit>) =>
  renderWith(newClient(), createElement(DocumentCardGrid, { documents: [version({ classification: classification(), audit: audit(over) })], addresses }));

describe('the pill, worded from the server’s counts', () => {
  it('says the proposals and, while some wait for an expert, how many', () => {
    const waiting = optimisationPill(audit({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 }));
    expect(waiting).toMatchObject({ count: 7, undecided: 3, text: 'Оптимизация 7', mark: '3 не решено' });
    expect(waiting?.title).toContain('7');
    expect(waiting?.title).toContain('без решения эксперта: 3');
  });

  it('has no marker once every proposal is decided', () => {
    const decided = optimisationPill(audit({ optimisation_proposal_count: 4, optimisation_undecided_count: 0 }));
    expect(decided).toMatchObject({ count: 4, undecided: 0, text: 'Оптимизация 4', mark: null });
    expect(decided?.title).toContain('по всем есть решение эксперта');
  });

  it('says nothing where the server read no optimisation or the pass has no proposal: absent is not zero', () => {
    expect(optimisationPill(undefined)).toBeNull();
    expect(optimisationPill(audit())).toBeNull();
    expect(optimisationPill(audit({ optimisation_proposal_count: 0, optimisation_undecided_count: 0 }))).toBeNull();
    // One count without the other is not a reading the server makes; it is not guessed at.
    expect(optimisationPill(audit({ optimisation_proposal_count: 2 }))).toBeNull();
  });
});

describe('the card', () => {
  it('draws the pill beside «Замечания N» with its counts for a document that has an optimisation pass', () => {
    const markup = card({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 });
    expect(markup).toMatch(/data-card-optimisation="7" data-card-optimisation-undecided="3"[^>]*>Оптимизация 7<span[^>]*>3 не решено<\/span>/);
    expect(markup.indexOf('data-card-findings')).toBeLessThan(markup.indexOf('data-card-optimisation'));
  });

  it('draws the pill without a marker when all are decided, and no pill at all for a document without a pass', () => {
    const decided = card({ optimisation_proposal_count: 4, optimisation_undecided_count: 0 });
    expect(decided).toMatch(/data-card-optimisation="4"[^>]*>Оптимизация 4<\//);
    expect(decided).not.toMatch(/не решено/);
    for (const markup of [card({}), card({ optimisation_proposal_count: 0, optimisation_undecided_count: 0 })]) {
      expect(markup).not.toContain('data-card-optimisation');
      expect(markup).not.toContain('Оптимизация');
    }
  });

  it('is a fact beside the chip: the chip says what it said without the counts', () => {
    const without = auditChip(audit());
    const withPill = auditChip(audit({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 }));
    expect(withPill).toEqual(without);
    expect(card({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 })).toContain('Ждёт решения: 1');
  });

  it('draws the pill on a document with no findings too: the optimisation does not wait for them', () => {
    const markup = card({ state: 'clean', finding_count: 0, undecided_finding_count: 0, optimisation_proposal_count: 2, optimisation_undecided_count: 2 });
    expect(markup).not.toContain('data-card-findings');
    expect(markup).toContain('data-card-optimisation="2"');
  });
});
