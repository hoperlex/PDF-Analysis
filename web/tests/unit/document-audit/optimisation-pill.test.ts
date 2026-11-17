/**
 * `D-361` (contract 1.43.0, `UI-A-46` second half): the original's second pill on a document card, «Оптимизация N [метка]».
 *
 * The server counts (`DocumentAudit.optimisation_proposal_count` and `optimisation_undecided_count`: the proposals of the version's
 * latest optimisation pass and those with no decision in force); the screen words them. Held, each with a case that shows it can fail:
 *
 *   - the model says the count and, only while some wait for an expert, the marker; it says nothing where the server read no
 *     optimisation (the counts are absent -- never a zero) and nothing for a pass that produced no proposal;
 *   - the card draws the pill as its second mark beside «Замечания N» (`UIP-S02-02`: «Оптимизация N» with a sign, ✓ every proposal decided,
 *     · some still wait for an expert, — no pass or no proposal), with the counts as attributes and the sentence as its tooltip;
 *   - the pill is a fact beside the audit chip: the chip's words are the ones they were with and without it;
 *   - `D-461`: where the screen gives an address the pill is a link to the document's «Оптимизация» tab, with no `pass` (the counts are
 *     the latest pass's); without an address it stays a plain figure, and a mark with no proposal is never a link. The section page and
 *     the project's document list give it.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DocumentAudit } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { routes } from '@/shared/lib';
import { DOCUMENT_PAGE_LIMIT, DocumentCardGrid, auditChip, optimisationPill } from '@/entities/document-version';
import { SectionDetailPage } from '@/_pages/section-detail';
import { ProjectSections } from '@/widgets/project-sections';

import { newClient, renderWith } from '../screens/harness';
import { DOCUMENT_UID, PROJECT_UID, classification, otherVersion, page, version } from '../sections/fixtures';

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
  /** The whole element of the mark, closing tag included: its inner spans are counted, so the first `</span>` does not end it. */
  const mark = (markup: string): string => {
    const start = markup.search(/<(?:span|a) [^>]*data-card-mark="optimisation"/);
    if (start < 0) return '';
    const tag = markup.startsWith('<a', start) ? 'a' : 'span';
    const tags = new RegExp(`<${tag}[ >]|</${tag}>`, 'g');
    tags.lastIndex = start;
    let depth = 0;
    for (let found = tags.exec(markup); found !== null; found = tags.exec(markup)) {
      depth += found[0].startsWith('</') ? -1 : 1;
      if (depth === 0) return markup.slice(start, found.index + found[0].length);
    }
    return markup.slice(start);
  };

  it('draws the mark beside «Замечания N» with its counts and its sign for a document that has an optimisation pass', () => {
    const markup = card({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 });
    const open = mark(markup);
    expect(open).toContain('data-card-optimisation="7"');
    expect(open).toContain('data-card-optimisation-undecided="3"');
    expect(open).toContain('data-card-mark-state="open"');
    expect(open).toContain('title="Оптимизация: 7, без решения эксперта: 3"');
    expect(open).toMatch(/<span[^>]*>Оптимизация<\/span><span[^>]*>7<\/span><span[^>]*aria-hidden="true">·<\/span><span[^>]*>есть нерешённое<\/span>/);
    expect(markup.indexOf('data-card-findings')).toBeLessThan(markup.indexOf('data-card-optimisation'));
  });

  it('signs it ✓ when all are decided, and — with no count where there is no pass or the pass has no proposal', () => {
    const decided = mark(card({ optimisation_proposal_count: 4, optimisation_undecided_count: 0 }));
    expect(decided).toContain('data-card-mark-state="done"');
    expect(decided).toContain('>✓<');
    expect(decided).not.toContain('не решено');
    for (const [over, words] of [
      [{}, 'проход не запускался'],
      [{ optimisation_proposal_count: 0, optimisation_undecided_count: 0 }, 'предложений нет'],
    ] as const) {
      const none = mark(card(over));
      expect(none).toContain('data-card-mark-state="none"');
      expect(none).toContain('>—<');
      expect(none).not.toContain('data-card-optimisation=');
      expect(none).toContain(`title="Оптимизация: ${words}"`);
    }
  });

  it('is a fact beside the chip: the chip says what it said without the counts', () => {
    const without = auditChip(audit());
    const withPill = auditChip(audit({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 }));
    expect(withPill).toEqual(without);
    expect(card({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 })).toContain('>Ждёт решения: 1<');
  });

  it('draws the mark on a document with no findings too: the optimisation does not wait for them', () => {
    const markup = card({ state: 'clean', finding_count: 0, undecided_finding_count: 0, optimisation_proposal_count: 2, optimisation_undecided_count: 2 });
    expect(markup).toContain('data-card-findings="0"');
    expect(markup).toContain('data-card-optimisation="2"');
  });

  it('draws no mark of either kind where the answer carried no audit: an operation that reads no runs says nothing', () => {
    const markup = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [version({ classification: classification() })], addresses }));
    expect(markup).not.toContain('data-card-mark');
    expect(markup).not.toContain('Оптимизация');
  });
});

describe('`D-461`: the pill as a link to the document’s «Оптимизация» tab', () => {
  const TAB = `/projects/${PROJECT_UID}/documents/${DOCUMENT_UID}?tab=optimisation`;
  const counted = audit({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 });
  const withAddress = (documents = [version({ classification: classification(), audit: counted })]) =>
    renderWith(newClient(), createElement(DocumentCardGrid, {
      documents,
      addresses,
      optimisationAddress: (v) => routes.documentOptimisation(PROJECT_UID, v.document_uid),
    }));

  it('links the pill to the tab the helper builds, with no pass, and keeps its counts and sign', () => {
    const markup = withAddress();
    const pill = markup.match(/<a [^>]*data-card-optimisation="7"[^>]*>.*?<\/a>/)?.[0];
    expect(pill).toBeDefined();
    expect(pill).toContain(`href="${TAB}"`);
    expect(pill).toContain('data-card-optimisation-undecided="3"');
    expect(pill).toContain('data-card-mark-state="open"');
    expect(pill).not.toContain('pass=');
    expect(TAB).toBe(routes.documentOptimisation(PROJECT_UID, DOCUMENT_UID));
  });

  it('stays a plain figure where the screen gives no address, and is no link for a document with no proposals', () => {
    expect(card({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 })).toMatch(/<span [^>]*data-card-optimisation="7"/);
    expect(card({ optimisation_proposal_count: 7, optimisation_undecided_count: 3 })).not.toMatch(/<a [^>]*data-card-optimisation/);
    const none = withAddress([version({ classification: classification(), audit: audit({}) })]);
    expect(none).not.toContain('data-card-optimisation=');
    expect(none).not.toMatch(/<a [^>]*data-card-mark="optimisation"/);
  });

  it('asks the address of each card for its own document', () => {
    const other = otherVersion('C', { classification: classification(), audit: audit({ optimisation_proposal_count: 2, optimisation_undecided_count: 0 }) });
    const markup = withAddress([version({ classification: classification(), audit: counted }), other]);
    const pills = [...markup.matchAll(/<a [^>]*data-card-optimisation="[^>]*>/g)].map((match) => match[0]);
    const hrefs = pills.map((tag) => /href="([^"]*)"/.exec(tag)?.[1]);
    expect(hrefs).toEqual([TAB, `/projects/${PROJECT_UID}/documents/${other.document_uid}?tab=optimisation`]);
  });

  it('is given by the section page', () => {
    const client = newClient();
    client.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit'),
      page([version({ classification: classification({ section_code: 'AR' }), audit: counted })]),
    );
    const markup = renderWith(client, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain(`href="${TAB}"`);
    expect(markup).toMatch(/<a [^>]*data-card-optimisation="7"/);
  });

  it('is given by the project’s document list', () => {
    const client = newClient();
    client.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, undefined, false, undefined, undefined, 'audit'),
      page([version({ classification: classification({ section_code: 'AR' }), audit: counted })]),
    );
    client.setQueryData(queryKeys.projects.tags(PROJECT_UID), { items: [] });
    const markup = renderWith(client, createElement(ProjectSections, { projectUid: PROJECT_UID }));
    expect(markup).toContain(`href="${TAB}"`);
    expect(markup).toMatch(/<a [^>]*data-card-optimisation="7"/);
  });
});
