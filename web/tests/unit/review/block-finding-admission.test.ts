/**
 * A finding grounded on a portal block is admitted (`D-683`, contract 1.52.0), and a text finding with no evidence is
 * still refused, exactly as before.
 *
 * Contract 1.52.0 lets a `portal_block` observation carry an empty `evidence`: a block finding stands on the finding's
 * `block_evidence`, not on a text span. The admission gate used to refuse every finding with `evidence = []` as
 * `no_evidence`, which would have hidden every finding of a `one_list` run that comes from a drawing or a cross-check.
 * The rule that replaced it is narrow on purpose, and each case below is the one that would go wrong if it widened:
 * the three refusals are pinned beside the one admission.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { Finding } from '@/shared/api';
import { admitFinding, admitFindings, groupByCategory, groundedOnBlocks } from '@/entities/finding';
import { findingPages } from '@/entities/finding-observation';
import { FindingList } from '@/widgets/finding-list';

import { blockEvidence, blockFinding, finding, observation, render } from './fixtures';

const BLOCK_UID = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8D';

describe('the admission of a block finding', () => {
  it('admits a portal_block observation with no text span and at least one block', () => {
    const candidate = blockFinding({ finding_uid: BLOCK_UID });
    expect(candidate.observation.evidence).toEqual([]);
    expect(admitFinding(candidate)).toEqual({ kind: 'admitted', finding: candidate });
  });

  it('still refuses a text finding with no evidence, as it did', () => {
    const empty = finding({ observation: observation({ evidence: [] }) });
    expect(admitFinding(empty)).toEqual({ kind: 'refused', refusal: 'no_evidence' });
  });

  it('refuses a text finding with no evidence even when the server also sent blocks for it', () => {
    // `grounding_kind` is the switch, not the presence of blocks: a text_span (or absent) observation stands on its spans.
    const blocksOnly = finding({ observation: observation({ evidence: [] }), block_evidence: [blockEvidence()] });
    expect(admitFinding(blocksOnly)).toEqual({ kind: 'refused', refusal: 'no_evidence' });
    const spanKind = finding({ observation: observation({ evidence: [], grounding_kind: 'text_span' }), block_evidence: [blockEvidence()] });
    expect(admitFinding(spanKind)).toEqual({ kind: 'refused', refusal: 'no_evidence' });
  });

  it('refuses a portal_block observation that names no block: it is grounded on nothing', () => {
    const noBlocks = blockFinding({ block_evidence: [] });
    expect(admitFinding(noBlocks)).toEqual({ kind: 'refused', refusal: 'no_evidence' });
    const absent = blockFinding();
    delete (absent as { block_evidence?: unknown }).block_evidence;
    expect(admitFinding(absent)).toEqual({ kind: 'refused', refusal: 'no_evidence' });
  });

  it('keeps every other refusal for a block finding: a diagnostic is never a finding', () => {
    expect(admitFinding({ ...blockFinding(), finding_uid: '' } as Finding)).toEqual({ kind: 'refused', refusal: 'not_a_finding' });
    expect(admitFinding({ ...blockFinding(), grounded: false, ungrounded_reason: 'block_not_in_run_geometry' } as unknown as Finding)).toEqual({
      kind: 'refused',
      refusal: 'ungrounded_diagnostic',
    });
  });

  it('admits a block finding next to a text finding, and reports only the impossible one', () => {
    const text = finding();
    const block = blockFinding({ finding_uid: BLOCK_UID });
    const impossible = finding({ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8E', observation: observation({ evidence: [] }) });

    const admitted = admitFindings([text, block, impossible]);

    expect(admitted.findings).toEqual([text, block]);
    expect(admitted.integrityFaults).toEqual([{ findingUid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q8E', refusal: 'no_evidence' }]);
  });

  it('groundedOnBlocks says the same thing the gate does', () => {
    expect(groundedOnBlocks(blockFinding())).toBe(true);
    expect(groundedOnBlocks(blockFinding({ block_evidence: [] }))).toBe(false);
    expect(groundedOnBlocks(finding())).toBe(false);
  });
});

describe('a block finding in the list', () => {
  it('is a row that says the page of its block, not an empty «стр.»', () => {
    const block = blockFinding({
      finding_uid: BLOCK_UID,
      block_evidence: [blockEvidence({ ordinal: 1, page_number: 5 }), blockEvidence({ ordinal: 0, page_number: 3 })],
    });
    expect(findingPages(block)).toEqual([3, 5]);

    const markup = render(createElement(FindingList, { groups: groupByCategory([block]), selectedFindingUid: null, onSelect: () => {} }));

    expect(markup).toContain(`data-finding-uid="${BLOCK_UID}"`);
    expect(markup).toContain('data-pages="3,5"');
    expect(markup).toContain('стр. 3, 5');
    expect(markup).not.toMatch(/стр\.\s*<\/span>/);
  });

  it('says a text finding\'s pages as it always did, from its text spans', () => {
    expect(findingPages(finding())).toEqual([7]);
  });
});
