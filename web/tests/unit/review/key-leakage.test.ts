/**
 * No object key, bucket name, storage URL or credential reaches the browser.
 *
 * `P3-WEB-02` requires a leakage check with a fixture carrying an `s3://` value in an
 * unexpected field, and requires that the check can actually fail. The contract makes the
 * leak structurally unlikely — `streamDocumentVersionContent` returns bytes, there is no
 * presigned link and no redirect, because a URL into object storage is the internal address
 * the contract forbids in a response and would outlive the request that authorized it — but
 * "unlikely by contract" is not the same as "this UI would not print it".
 *
 * The scanner below is the guard. `LEAKAGE_PATTERNS` is what it looks for; the tests feed
 * it markup rendered from fixtures that carry a storage value in fields the API would never
 * populate that way, and assert the screen stays clean. The last test in this file is the
 * proof the scanner is not vacuous: the same value placed in a field the viewer *does*
 * render is caught.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { FindingList } from '@/widgets/finding-list';
import { groupByCategory } from '@/entities/finding';

import { evidence, finding, observation, provenance, render } from './fixtures';

const LEAKED_VALUE = 's3://auditmanager-prod-documents/versions/ver_01J9/content.pdf';

/** Anything that would mean an internal storage address reached the page. */
const LEAKAGE_PATTERNS: readonly RegExp[] = [
  /s3:\/\//i,
  /X-Amz-/i,
  /\bpresign/i,
  /\bminio\b/i,
  /[a-z0-9.-]+\.s3\.[a-z0-9.-]*amazonaws\.com/i,
  /\bAKIA[0-9A-Z]{16}\b/,
];

/** The patterns that matched, so a failure names what leaked rather than only that it did. */
export function findLeaks(markup: string): readonly string[] {
  return LEAKAGE_PATTERNS.filter((pattern) => pattern.test(markup)).map((p) => p.source);
}

const OBJECT_URL = 'blob:https://app.test/11111111-2222-3333-4444-555555555555';

describe('the rendered review screen leaks no storage address', () => {
  it('keeps the viewer clean when a storage value sits in an unexpected field', () => {
    // `block_id` is a secondary anchor into the version's block index and is explicitly
    // "not a contract identifier". A backend bug that put an object key there is exactly
    // the "unexpected field" this check is for.
    const observed = observation({
      evidence: [evidence({ block_id: LEAKED_VALUE })],
      provenance: provenance({ model_identity: LEAKED_VALUE }),
    });

    const markup = render(
      createElement(EvidenceViewer, {
        observation: observed,
        activePage: 7,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    // This check earned its place: the viewer originally printed `block_id` on the anchor
    // line and this assertion went red on the first run. `block_id` is now not rendered at
    // all — it is an internal index handle, not a contract identifier, and it told the
    // reviewer nothing the page and character range do not.
    expect(findLeaks(markup)).toEqual([]);
    // The value itself, not the word — `<blockquote>` is the quotation element.
    expect(markup).not.toContain(LEAKED_VALUE);
    expect(markup).not.toContain('blk_');
  });

  it('keeps the finding list clean when provenance carries a storage value', () => {
    const listed = finding({
      observation: observation({ provenance: provenance({ model_identity: LEAKED_VALUE }) }),
    });

    const markup = render(
      createElement(FindingList, {
        groups: groupByCategory([listed]),
        selectedFindingUid: null,
        onSelect: () => {},
      }),
    );

    expect(findLeaks(markup)).toEqual([]);
  });

  it('renders only a blob: URL for the document, never a storage host', () => {
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observation(),
        activePage: 7,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    expect(markup).toContain('blob:');
    expect(findLeaks(markup)).toEqual([]);
  });
});

describe('the leakage check can fail', () => {
  it('catches a storage address placed in a field the viewer does render', () => {
    // The quotation is rendered verbatim by design, so it is the one field guaranteed to
    // reach the page. If the scanner cannot catch a leak here it cannot catch one anywhere,
    // and the three tests above would be passing for no reason.
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observation({ evidence: [evidence({ quote: LEAKED_VALUE })] }),
        activePage: 7,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    expect(findLeaks(markup)).toContain('s3:\\/\\/');
  });

  it('catches each pattern it claims to catch', () => {
    expect(findLeaks('X-Amz-Signature=deadbeef')).toHaveLength(1);
    expect(findLeaks('https://bucket.s3.eu-central-1.amazonaws.com/key')).not.toHaveLength(0);
    expect(findLeaks('AKIAIOSFODNN7EXAMPLE')).toHaveLength(1);
    expect(findLeaks('a presigned url')).not.toHaveLength(0);
    expect(findLeaks('nothing to see here')).toEqual([]);
  });
});
