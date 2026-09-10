/**
 * The evidence viewer: the exact quotation, on the declared page.
 *
 * `P3-WEB-02` names the three assertions this suite has to make — the rendered quotation is
 * byte-identical to the API string, the viewer requests only the version-content route, and
 * the declared page index is the page opened.
 *
 * Byte-identity is the one that needs the awkward fixtures. Any of the usual "tidying"
 * transforms — trim, whitespace collapse, smart quotes, truncation, NFC normalization —
 * looks harmless and breaks the only property the viewer exists to demonstrate: that this
 * string is present, verbatim, at that anchor in that document.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { declaredPages, quotationText } from '@/entities/finding-observation';
import { objectUrlOf, pdfPageUrl } from '@/features/open-evidence';
import { streamDocumentVersionContent } from '@/shared/api';
import { EvidenceViewer } from '@/widgets/evidence-viewer';

import { AWKWARD_QUOTES, VERSION_UID, evidence, observation, render } from './fixtures';

const OBJECT_URL = 'blob:https://app.test/0f0e9d8c-7b6a-5948-3726-150413021100';

describe('the quotation is the API string, unmodified', () => {
  it.each(AWKWARD_QUOTES)('renders %j byte-for-byte', (quote) => {
    const item = evidence({ quote });
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observation({ evidence: [item] }),
        activePage: item.page_number,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    // The attribute carries the same string the element's text does, so the assertion is
    // on the value rather than on markup this test would have to un-escape by hand.
    const attribute = markup.match(/data-evidence-quote="([^"]*)"/)?.[1] ?? '';
    const decoded = attribute
      .replaceAll('&quot;', '"')
      .replaceAll('&#x27;', "'")
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>')
      .replaceAll('&amp;', '&');

    expect(decoded).toBe(quote);
    expect(quotationText(item)).toBe(quote);
    // Nothing trimmed: the fixture with surrounding whitespace keeps it.
    expect(decoded.length).toBe(quote.length);
  });

  it('renders every quotation on the page, not only the first', () => {
    const observed = observation({
      evidence: [
        evidence({ evidence_ordinal: 1, page_number: 4, quote: 'first quotation' }),
        evidence({ evidence_ordinal: 2, page_number: 4, quote: 'second quotation' }),
      ],
    });
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observed,
        activePage: 4,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    expect(markup).toContain('first quotation');
    expect(markup).toContain('second quotation');
    // Ordered by `evidence_ordinal`, which is the order the CSV rows follow.
    expect(markup.indexOf('first quotation')).toBeLessThan(markup.indexOf('second quotation'));
  });
});

describe('the declared page is the page opened', () => {
  it('addresses the fragment of the declared page', () => {
    const item = evidence({ page_number: 11 });
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observation({ evidence: [item] }),
        activePage: 11,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    expect(markup).toContain(`${OBJECT_URL}#page=11`);
    expect(markup).toContain('data-active-page="11"');
  });

  it('falls back to the first declared page when asked for one that is not declared', () => {
    // Not a cosmetic fallback: showing page 3 of the PDF for a finding that cited page 7
    // puts text in front of the reviewer that this finding never quoted.
    const observed = observation({
      evidence: [evidence({ page_number: 7 }), evidence({ evidence_ordinal: 2, page_number: 9 })],
    });
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observed,
        activePage: 3,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    expect(markup).toContain('data-active-page="7"');
    expect(markup).toContain(`${OBJECT_URL}#page=7`);
    expect(markup).not.toContain('#page=3');
  });

  it('offers navigation only to the declared pages', () => {
    const observed = observation({
      evidence: [
        evidence({ page_number: 7 }),
        evidence({ evidence_ordinal: 2, page_number: 2 }),
        evidence({ evidence_ordinal: 3, page_number: 7 }),
      ],
    });

    // De-duplicated and numerically sorted: three quotations on two pages is two buttons,
    // and 2 comes before 7 rather than lexicographically.
    expect(declaredPages(observed)).toEqual([2, 7]);

    const markup = render(
      createElement(EvidenceViewer, {
        observation: observed,
        activePage: 2,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    expect(markup.match(/data-page="\d+"/g)).toEqual(['data-page="2"', 'data-page="7"']);
  });

  it('refuses to build a fragment for something that is not a page number', () => {
    // `#page=0` and `#page=NaN` make a viewer fall back to page 1 silently, which is the
    // failure mode this whole restriction exists to avoid.
    expect(() => pdfPageUrl(OBJECT_URL, 0)).toThrow(RangeError);
    expect(() => pdfPageUrl(OBJECT_URL, -1)).toThrow(RangeError);
    expect(() => pdfPageUrl(OBJECT_URL, 1.5)).toThrow(RangeError);
    expect(() => pdfPageUrl(OBJECT_URL, Number.NaN)).toThrow(RangeError);
  });

  it('strips the fragment before revoking, so the blob is actually released', () => {
    expect(objectUrlOf(pdfPageUrl(OBJECT_URL, 7))).toBe(OBJECT_URL);
    expect(objectUrlOf(OBJECT_URL)).toBe(OBJECT_URL);
  });
});

describe('the viewer requests only the version-content route', () => {
  it('calls GET /versions/{version_uid}/content and nothing else', async () => {
    const calls: { url: string; method: string | undefined }[] = [];

    await streamDocumentVersionContent(
      { path: { version_uid: VERSION_UID } },
      {
        baseUrl: 'https://api.test',
        fetch: async (url, init) => {
          calls.push({ url, method: init.method });
          return new Response(new Blob([new Uint8Array([0x25, 0x50, 0x44, 0x46])]), {
            status: 200,
            headers: { 'Content-Type': 'application/pdf', 'X-Correlation-Id': 'corr-1' },
          });
        },
      },
    );

    expect(calls).toEqual([
      { url: `https://api.test/versions/${VERSION_UID}/content`, method: 'GET' },
    ]);
    // No presigned link, no redirect, no storage host: the contract has none, so the
    // browser only ever learns this path.
    expect(calls[0]?.url).not.toContain('s3');
    expect(calls[0]?.url).not.toContain('X-Amz');
  });
});

describe('a failure is explicit, never a blank page', () => {
  it('renders an error rather than an empty pane when the bytes are missing', () => {
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observation(),
        activePage: 7,
        onPageChange: () => {},
        documentUrl: null,
      }),
    );

    expect(markup).toContain('The page could not be displayed');
    expect(markup).not.toContain('<object');
  });

  it('renders the presented failure with its correlation id', () => {
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observation(),
        activePage: 7,
        onPageChange: () => {},
        documentUrl: null,
        error: { title: 'The document page could not be loaded', correlationId: 'corr-77' },
      }),
    );

    expect(markup).toContain('The document page could not be loaded');
    expect(markup).toContain('corr-77');
  });

  it('reports a finding with no evidence instead of rendering an empty viewer', () => {
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observation({ evidence: [] }),
        activePage: 1,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    expect(markup).toContain('Data integrity fault');
    expect(markup).not.toContain('<object');
  });
});
