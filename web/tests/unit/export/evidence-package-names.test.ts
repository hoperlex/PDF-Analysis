/**
 * The evidence package refuses a path separator or a control character in a file name and a
 * control character in a media type -- and refuses exactly the strings it refused when those
 * two checks were regular expressions.
 *
 * `no-control-regex` would not let `package.ts` keep `/[\\/\u0000-\u001f\u007f]/u`, so the
 * checks are code-unit scans now. This file is the proof that the rewrite changed nothing:
 * the former regular expression is rebuilt below (from `String.fromCharCode`, because a
 * literal holding the control range is what the lint rule rejects) and every candidate is put
 * to both. The package builder is driven through its public function only; the checks run
 * before any source is read, and the two source reads are stubbed to fail, so a name that
 * passes ends in `source_read_failed` and one that does not ends in `invalid_request`.
 */

import { describe, expect, it, vi } from 'vitest';

import { buildEvidencePackage } from '@/features/export-evidence-package';
import type { EvidencePackageOptions } from '@/features/export-evidence-package';

vi.mock('@/shared/api', () => ({
  getDocumentVersion: vi.fn(() => Promise.reject(new Error('no network in this test'))),
  streamDocumentVersionContent: vi.fn(() => Promise.reject(new Error('no network in this test'))),
}));

const NUL = String.fromCharCode(0x00);
const US = String.fromCharCode(0x1f);
const DEL = String.fromCharCode(0x7f);
/** The pattern the two checks used before the rewrite, as a regular expression. */
const FORMER_NAME_PATTERN = new RegExp(`[\\\\/${NUL}-${US}${DEL}]`, 'u');
const FORMER_MEDIA_PATTERN = new RegExp(`[${NUL}-${US}${DEL}]`, 'u');

const OPTIONS: EvidencePackageOptions = {
  fileName: 'package',
  kind: 'section-analysis',
  runId: 'run-1',
  reports: [{ name: 'report.txt', content: 'x' }],
  sources: [{ versionUid: 'ver_01' as never }],
};

async function codeOf(options: EvidencePackageOptions): Promise<string> {
  try {
    await buildEvidencePackage(options);
    return 'built';
  } catch (error) {
    return (error as { code?: string }).code ?? 'other';
  }
}

/** Every code point below U+00A0 in the middle of a word, plus the separators and some neighbours. */
const CANDIDATES: readonly string[] = [
  ...Array.from({ length: 0xa0 }, (_, code) => `a${String.fromCharCode(code)}b`),
  'plain.txt', 'отчёт №1.xlsx', 'emoji-\u{1F600}.txt', 'lone-\ud800-surrogate', 'line sep', 'nbsp here',
  'back\\slash', 'forward/slash', '..\\..\\x', '/etc/passwd', 'x' + DEL, NUL + 'x',
];

describe('the package name checks refuse exactly what the former regular expressions refused', () => {
  it('reads a broad enough candidate set to include the whole control range and both separators', () => {
    expect(CANDIDATES.filter((s) => FORMER_NAME_PATTERN.test(s)).length).toBeGreaterThan(0x20 + 3);
    expect(CANDIDATES.filter((s) => !FORMER_NAME_PATTERN.test(s)).length).toBeGreaterThan(0x40);
  });

  it.each(CANDIDATES.map((candidate) => [JSON.stringify(candidate), candidate] as const))(
    'file name and report name %s',
    async (_label, candidate) => {
      const refused = FORMER_NAME_PATTERN.test(candidate);
      const expected = refused ? 'invalid_request' : 'source_read_failed';
      expect(await codeOf({ ...OPTIONS, fileName: candidate }), 'package file name').toBe(expected);
      expect(
        await codeOf({ ...OPTIONS, reports: [{ name: candidate, content: 'x' }] }),
        'report name',
      ).toBe(expected);
    },
  );

  it.each(CANDIDATES.map((candidate) => [JSON.stringify(candidate), candidate] as const))(
    'report media type %s',
    async (_label, candidate) => {
      const expected = FORMER_MEDIA_PATTERN.test(candidate) ? 'invalid_request' : 'source_read_failed';
      const code = await codeOf({
        ...OPTIONS,
        reports: [{ name: 'report.txt', content: 'x', mediaType: candidate }],
      });
      expect(code).toBe(expected);
    },
  );
});
