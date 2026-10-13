/**
 * Four statements this UI makes about bytes and about files, none of which could be told
 * from a deleted rule before the `W12-WEB` sweep.
 *
 * - `CSV_ENCODING.charset` — the panel prints it to the user, and changing it to
 *   `windows-1251` reddened nothing. The seam document fixes it, so the seam document is
 *   what it is checked against here; the sibling contract suite already pins the BOM, the
 *   delimiter, the line ending and the null projection, and `charset` was the one fact of
 *   the five that nothing read.
 * - `hasZipExtension` — `endsWith('.zip')` became `includes('.zip')` with the suite green,
 *   so `bundle.zip.exe` announced by a browser that declares no media type would have
 *   passed the pre-check. (Until `W55B-INGEST-01` the check was the PDF's, and the same.)
 * - the declared media type is lower-cased before comparison — dropping `.toLowerCase()`
 *   reddened nothing, and a browser that reports `APPLICATION/ZIP` would have been told
 *   its archive is not an archive.
 * - `UPLOAD_ENVELOPE_RULES` names the one-archive rule — dropping the line reddened
 *   nothing, although the contract refuses a bare PDF and any file outside the bundle's
 *   member set with `validation_failed` and the panel exists to state each refusal before
 *   the file is chosen.
 * - `deliverDownload` revokes **after** saving — swapping the two reddened nothing, and a
 *   URL revoked before the anchor is clicked downloads nothing at all.
 *
 * The contract document and the seam document are read from this file's location, which is
 * the authority case: they are what the constants are checked *against*.
 */

import { describe, expect, it } from 'vitest';

import { CSV_ENCODING } from '@/shared/api';
import { UPLOAD_ENVELOPE_RULES, precheckUploadFile } from '@/entities/document-version';
import type { DownloadSink } from '@/features/export-run';
import { deliverDownload } from '@/features/export-run';
import { CONTRACT_PATH, SEAMS_PATH, readText } from '../../guards/lib/repo';

const contract = readText(CONTRACT_PATH);
const seams = readText(SEAMS_PATH);

/** Section 6 of the seam document, which is where `OD-11` fixes the CSV bytes. */
function csvSection(): string {
  const start = seams.indexOf('## 6. The CSV column contract');
  const end = seams.indexOf('## 7. API seam');
  expect(start, 'section 6 of P02_SEAMS.md was not found').toBeGreaterThan(-1);
  expect(end).toBeGreaterThan(start);
  return seams.slice(start, end);
}

describe('the charset the panel states is the charset the seam document fixes', () => {
  it('is utf-8', () => {
    expect(CSV_ENCODING.charset).toBe('utf-8');
  });

  it('is the charset section 6 names, and section 6 names exactly one', () => {
    const section = csvSection().toLowerCase();
    expect(section).toContain('utf-8 with a byte-order mark');
    // Nothing else may be offered as the export charset.
    expect(section).not.toContain('windows-1251');
    expect(section).not.toContain('utf-16');
    expect(section).not.toContain('cp1251');
  });

  it('is not a legacy code page, whatever the constant is set to', () => {
    // The concrete failure this exists for: Excel opens a Cyrillic CSV correctly because
    // the file is UTF-8 with a BOM. A panel announcing a code page announces a different
    // file from the one the server sends.
    expect(CSV_ENCODING.charset.toLowerCase()).not.toContain('1251');
    expect(CSV_ENCODING.charset.toLowerCase()).not.toContain('ascii');
  });
});

describe('the ZIP extension fallback matches the end of the name, not the middle', () => {
  it('refuses a double extension when the browser declares nothing', () => {
    expect(precheckUploadFile({ name: 'annual-report.zip.exe', size: 4096, type: '' })).toBe(
      'not_zip',
    );
    expect(precheckUploadFile({ name: 'report.zip.pdf', size: 4096, type: '' })).toBe('not_zip');
  });

  it('refuses a name that merely mentions the extension', () => {
    expect(precheckUploadFile({ name: 'about.zip.txt', size: 4096, type: '' })).toBe('not_zip');
    expect(precheckUploadFile({ name: '.zip-notes', size: 4096, type: '' })).toBe('not_zip');
  });

  it('still accepts a name that genuinely ends in the extension', () => {
    expect(precheckUploadFile({ name: 'annual-report.zip', size: 4096, type: '' })).toBeNull();
  });
});

describe('the media type the browser declares is compared case-insensitively', () => {
  it('accepts an upper-case declaration', () => {
    // Nothing in the platform guarantees the case of `File.type`; a pre-check that refused
    // `APPLICATION/ZIP` would refuse a legal file on a browser nobody tested on.
    expect(precheckUploadFile({ name: 'ar.zip', size: 4096, type: 'APPLICATION/ZIP' })).toBeNull();
    expect(precheckUploadFile({ name: 'ar.zip', size: 4096, type: 'Application/X-Zip-Compressed' })).toBeNull();
  });

  it('accepts a declaration with surrounding whitespace', () => {
    expect(precheckUploadFile({ name: 'ar.zip', size: 4096, type: '  application/zip  ' })).toBeNull();
  });

  it('still refuses a different media type whatever its case', () => {
    expect(precheckUploadFile({ name: 'ar.zip', size: 4096, type: 'APPLICATION/PDF' })).toBe(
      'not_zip',
    );
  });
});

describe('the stated envelope names the one-archive rule the contract enforces', () => {
  it('is a rule the contract actually has', () => {
    // `W55B-SEAL-01`: the contract's rule is the bundle's member set.
    expect(contract).toContain('Anything else in the archive is refused');
    expect(contract).toContain('portal_bundle_required');
  });

  it('is on screen before a file is chosen', () => {
    const text = UPLOAD_ENVELOPE_RULES.join(' ');
    expect(text).toContain('Один ZIP-архив за загрузку');
    expect(text).toContain('Отдельный PDF не принимается');
    expect(text.toLowerCase()).toContain('любой другой файл отклоняется');
  });

  it('leaves the other rules in place beside it', () => {
    // So that dropping this one line cannot be repaired by dropping the check instead.
    expect(UPLOAD_ENVELOPE_RULES).toHaveLength(6);
  });
});

describe('a downloaded blob is handed over before its URL is released', () => {
  it('creates, then saves, then revokes — in that order', () => {
    const calls: string[] = [];
    const sink: DownloadSink = {
      createObjectUrl: () => {
        calls.push('create');
        return 'blob:https://app.test/abc';
      },
      saveAs: (url) => {
        calls.push(`save:${url}`);
      },
      revokeObjectUrl: (url) => {
        calls.push(`revoke:${url}`);
      },
    };

    deliverDownload(sink, new Blob(['a']), 'run-findings.csv');

    expect(calls).toEqual([
      'create',
      'save:blob:https://app.test/abc',
      'revoke:blob:https://app.test/abc',
    ]);
  });

  it('is still holding a live URL at the moment the anchor is clicked', () => {
    // The observable consequence of the order. A URL revoked first is already dead when
    // the browser follows it, and the download silently produces nothing.
    let revoked = false;
    let liveAtSave: boolean | null = null;
    const sink: DownloadSink = {
      createObjectUrl: () => 'blob:https://app.test/abc',
      saveAs: () => {
        liveAtSave = !revoked;
      },
      revokeObjectUrl: () => {
        revoked = true;
      },
    };

    deliverDownload(sink, new Blob(['a']), 'run-findings.csv');

    expect(liveAtSave).toBe(true);
    expect(revoked).toBe(true);
  });
});
