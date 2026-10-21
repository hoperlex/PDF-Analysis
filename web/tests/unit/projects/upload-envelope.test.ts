/**
 * The PC-01 input envelope (a portal bundle), and the honest limits of a browser-side
 * pre-check.
 *
 * Three things are asserted here that a rendering test could not: that the numbers on
 * screen are the contract's numbers rather than numbers someone typed, that the pre-check
 * refuses to claim anything about the archive's members, encryption, page count or the
 * text layer — the properties a browser cannot read without opening the archive and
 * parsing the PDF — and that every constraint the contract registers for a refused upload
 * has a Russian sentence on this client.
 */

import { describe, expect, it } from 'vitest';

import {
  PC01_UPLOAD_ENVELOPE,
  UPLOAD_CONSTRAINTS_STATED,
  UPLOAD_ENVELOPE_RULES,
  formatBytes,
  precheckProblemMessage,
  precheckUploadFile,
  uploadConstraintSentence,
} from '@/entities/document-version';
import { CONTRACT_PATH, REPO_ROOT, WEB_ROOT, readJson, readText, repoRelative, walkFiles } from '../../guards/lib/repo';
import { join } from 'node:path';

const contract = readText(CONTRACT_PATH);

/** The portal-bundle constraint values, in the order `W55B-SEAL-01` registered them. */
const BUNDLE_CONSTRAINTS = [
  'portal_bundle_required',
  'bundle_unreadable',
  'bundle_entry_count',
  'bundle_directory_entry',
  'bundle_member_name',
  'bundle_symlink',
  'bundle_encrypted_member',
  'bundle_compression_method',
  'bundle_duplicate_member',
  'bundle_stem_mismatch',
  'bundle_member_set',
  'bundle_member_size',
  'bundle_total_size',
  'bundle_compression_ratio',
  'blocks_json_invalid',
  'blocks_page_count',
  // `W55B-FIX` (X-4): the block ceilings.
  'blocks_count',
  'results_blocks_mismatch',
  'stamp_audit_invalid',
] as const;

/** The PDF member's own constraint names, which a bundle keeps. */
const PDF_MEMBER_CONSTRAINTS = [
  'pdf_magic_bytes',
  'parseable_pdf',
  'not_encrypted',
  'every_page_has_extractable_text',
  'max_bytes',
  // `W55B-FIX`: the two the envelope always raised and the note did not name (Y-4), and the
  // reader's three bounds (X-1).
  'non_empty',
  'plain_base_name',
  'pdf_page_content',
  'pdf_document_content',
  'pdf_reader_limits',
] as const;

/** The registered values, read out of the contract note rather than copied from it. */
function registeredBundleConstraints(): string[] {
  const catalog = readJson<{ codes: { validation_failed: { notes: string[] } } }>(
    join(REPO_ROOT, 'contracts', 'domain', 'v1', 'error-codes.json'),
  );
  const note = catalog.codes.validation_failed.notes.find((entry) =>
    entry.includes('portal_bundle_required'),
  );
  expect(note, 'the portal-bundle note is gone from error-codes.json').toBeDefined();
  const body = (note ?? '').split('The registered values, all with field file:')[1] ?? '';
  const registered = body.split('The PDF member keeps')[0] ?? '';
  return [...registered.matchAll(/\b([a-z][a-z_]*)\s+\(/g)].map((match) => match[1] ?? '');
}

describe('the envelope the user is shown is the envelope the contract declares', () => {
  it('states 250 MiB in bytes, not megabytes', () => {
    expect(PC01_UPLOAD_ENVELOPE.maxBytes).toBe(250 * 1024 * 1024);
    expect(PC01_UPLOAD_ENVELOPE.maxBytes).toBe(262_144_000);
    expect(PC01_UPLOAD_ENVELOPE.maxBytesLabel).toBe('250 MiB');
  });

  it('states 500 pages and one ZIP archive', () => {
    expect(PC01_UPLOAD_ENVELOPE.maxPages).toBe(500);
    expect(PC01_UPLOAD_ENVELOPE.fileCount).toBe(1);
    expect(PC01_UPLOAD_ENVELOPE.mediaType).toBe('application/zip');
    expect(PC01_UPLOAD_ENVELOPE.mediaTypes).toEqual(['application/zip', 'application/x-zip-compressed']);
  });

  it('lets the file control offer a ZIP by extension and by both media types', () => {
    expect(PC01_UPLOAD_ENVELOPE.accept.split(',')).toEqual([
      '.zip',
      'application/zip',
      'application/x-zip-compressed',
    ]);
  });

  it('takes those numbers from the contract document, not from this file', () => {
    // The generator emits identifier patterns but not prose limits, so the envelope text
    // is the only place these two numbers can be checked against their source.
    expect(contract).toContain('at most 500 pages, and the whole upload at most 250 MiB');
    expect(contract).toContain('every page must carry an embedded text layer or at least one portal block');
  });

  it('names every refusal reason before a file is chosen', () => {
    const text = UPLOAD_ENVELOPE_RULES.join(' ');
    expect(text).toContain('ZIP-архив');
    expect(text).toContain('Отдельный PDF не принимается');
    // The five suffixes of the bundle, in the order the contract lists them.
    for (const suffix of ['_blocks.json', '_results.md', '_results.html', '_stamp_audit.json']) {
      expect(text).toContain(suffix);
    }
    expect(text).toContain('250 MiB');
    expect(text).toContain('500 страниц');
    expect(text).not.toContain('25 MiB');
    expect(text).not.toContain('30 страниц');
    expect(text.toLowerCase()).toContain('без пароля');
    // The text-layer rule is wider than it was: a portal block also carries a page.
    expect(text.toLowerCase()).toContain('извлекаемый встроенный текст');
    expect(text.toLowerCase()).toContain('блок портала');
    // OCR is never silently substituted, and the panel says so up front.
    expect(text.toLowerCase()).toContain('оптическим распознаванием');
  });
});

describe('the pre-check refuses only what a browser can actually see', () => {
  const bundle = { name: 'ar-2024.zip', size: 1_000_000, type: 'application/zip' };

  it('accepts a ZIP inside the size bound', () => {
    expect(precheckUploadFile(bundle)).toBeNull();
  });

  it('accepts the media type a Windows browser declares for a ZIP', () => {
    expect(precheckUploadFile({ ...bundle, type: 'application/x-zip-compressed' })).toBeNull();
  });

  it('accepts a file exactly at the bound and refuses one byte more', () => {
    expect(precheckUploadFile({ ...bundle, size: PC01_UPLOAD_ENVELOPE.maxBytes })).toBeNull();
    expect(precheckUploadFile({ ...bundle, size: PC01_UPLOAD_ENVELOPE.maxBytes + 1 })).toBe('too_large');
  });

  it('refuses a bare PDF before it is sent, whatever its name says', () => {
    expect(precheckUploadFile({ name: 'ar.pdf', size: 10, type: 'application/pdf' })).toBe('not_zip');
    expect(precheckUploadFile({ name: 'ar.pdf', size: 10, type: '' })).toBe('not_zip');
    expect(precheckUploadFile({ name: 'ar.zip', size: 10, type: 'application/pdf' })).toBe('not_zip');
  });

  it('falls back to the extension only when the browser declares nothing', () => {
    expect(precheckUploadFile({ name: 'ar.zip', size: 10, type: '' })).toBeNull();
    expect(precheckUploadFile({ name: 'AR.ZIP', size: 10, type: '' })).toBeNull();
    expect(precheckUploadFile({ name: 'ar.txt', size: 10, type: '' })).toBe('not_zip');
  });

  it('refuses an empty file', () => {
    expect(precheckUploadFile({ ...bundle, size: 0 })).toBe('empty_file');
  });

  it('claims nothing about the members, encryption, page count or the text layer', () => {
    // A 501-page, password-protected archive of legal size with the wrong members passes
    // here, because the browser cannot see any of those things without opening the
    // archive. The server refuses it, and the screen renders that refusal. A pre-check
    // that guessed would either block a legal file or promise one that will be rejected.
    const problem = precheckUploadFile({ name: 'scanned.zip', size: 5_000_000, type: 'application/zip' });
    expect(problem).toBeNull();
  });

  it('gives every problem a message that offers no retry', () => {
    for (const problem of ['not_zip', 'too_large', 'empty_file'] as const) {
      const message = precheckProblemMessage(problem);
      expect(message.length).toBeGreaterThan(0);
      expect(message.toLowerCase()).not.toContain('try again');
    }
  });

  it('tells a person who chose a bare PDF what to upload instead', () => {
    const message = precheckProblemMessage('not_zip');
    expect(message).toContain('ZIP-архив');
    expect(message).toContain('Отдельный PDF не принимается');
  });

  it('states the size limit in the contract unit', () => {
    expect(precheckProblemMessage('too_large')).toBe('Этот файл больше, чем 250 MiB.');
  });
});

describe('byte sizes read in the contract unit', () => {
  it('formats in binary units', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(1024)).toBe('1.0 KiB');
    expect(formatBytes(25 * 1024 * 1024)).toBe('25.0 MiB');
  });

  it('does not invent a size for a nonsense input', () => {
    expect(formatBytes(-1)).toBe('—');
    expect(formatBytes(Number.NaN)).toBe('—');
  });
});

describe('every constraint a refused upload can carry has its own Russian sentence', () => {
  it('registers exactly the nineteen the contract registers', () => {
    expect(registeredBundleConstraints()).toEqual([...BUNDLE_CONSTRAINTS]);
  });

  it('names every PDF member and upload-name constraint in the catalogue note (W55B-FIX, Y-4)', () => {
    const catalog = readJson<{ codes: { validation_failed: { notes: string[] } } }>(
      join(REPO_ROOT, 'contracts', 'domain', 'v1', 'error-codes.json'),
    );
    const notes = catalog.codes.validation_failed.notes.join(' ');
    for (const constraint of PDF_MEMBER_CONSTRAINTS) {
      expect(new RegExp(`\\b${constraint}\\b`).test(notes), constraint).toBe(true);
    }
  });

  it('has a sentence for each of them and for the PDF member constraints, as the panel shows it', () => {
    // `uploadConstraintSentence` is what the upload panel prints, for every constraint: since
    // `D-173` it is the only table, so the six `W55B-FIX` registered after the first
    // nineteen are in it like the rest.
    for (const constraint of [...BUNDLE_CONSTRAINTS, ...PDF_MEMBER_CONSTRAINTS]) {
      expect(UPLOAD_CONSTRAINTS_STATED, constraint).toContain(constraint);
      const sentence = uploadConstraintSentence(constraint);
      expect(sentence, constraint).not.toBeNull();
      expect(/[а-яА-ЯёЁ]/u.test(sentence ?? ''), constraint).toBe(true);
    }
  });

  it('gives no two constraints the same sentence', () => {
    const sentences = UPLOAD_CONSTRAINTS_STATED.map((constraint) => uploadConstraintSentence(constraint));
    expect(new Set(sentences).size).toBe(sentences.length);
  });

  it('states exactly the constraints the contract registers, and nothing for an unknown name', () => {
    expect([...UPLOAD_CONSTRAINTS_STATED].sort()).toEqual([...BUNDLE_CONSTRAINTS, ...PDF_MEMBER_CONSTRAINTS].sort());
    expect(uploadConstraintSentence('a_constraint_nobody_registered')).toBeNull();
    expect(uploadConstraintSentence('__proto__')).toBeNull();
    expect(uploadConstraintSentence(undefined)).toBeNull();
  });

  it('states the page and size rules in the envelope numbers, not in numbers typed twice', () => {
    expect(uploadConstraintSentence('1 <= page_count <= 500')).toBe(
      `Число страниц PDF вне допустимых границ: от 1 до ${PC01_UPLOAD_ENVELOPE.maxPages}.`,
    );
    expect(uploadConstraintSentence(`byte_size <= ${PC01_UPLOAD_ENVELOPE.maxBytes}`)).toBe(
      `Размер больше допустимого: не более ${PC01_UPLOAD_ENVELOPE.maxBytesLabel}.`,
    );
    // Only the server's current spelling of a bound is a rule. A stale 30-page or 25 MiB
    // spelling is not stated at all, so it cannot print a limit the product no longer has.
    for (const stale of ['page_count', '1 <= page_count <= 30', 'byte_size <= 26214400']) {
      expect(uploadConstraintSentence(stale), stale).toBeNull();
    }
  });

  it('says nothing for a constraint it does not know and for a value that is not a string', () => {
    expect(uploadConstraintSentence('a_constraint_nobody_registered')).toBeNull();
    expect(uploadConstraintSentence('__proto__')).toBeNull();
    expect(uploadConstraintSentence('constructor')).toBeNull();
    expect(uploadConstraintSentence(undefined)).toBeNull();
    expect(uploadConstraintSentence(null)).toBeNull();
    expect(uploadConstraintSentence(30)).toBeNull();
  });

  it('never names a cause the contract does not name', () => {
    // The wording of two sentences a reader could take as a cause: neither says who or what
    // encrypted, copied or renamed anything.
    for (const constraint of BUNDLE_CONSTRAINTS) {
      const sentence = (uploadConstraintSentence(constraint) ?? '').toLowerCase();
      for (const invented of ['вы ', 'вами', 'по ошибке', 'из-за', 'вирус', 'подмен']) {
        expect(sentence, `${constraint}: ${invented}`).not.toContain(invented);
      }
    }
  });
});

/**
 * `D-173` (`WEB-FOLLOWUPS-01`): the rule sentences of an upload live in ONE table.
 *
 * They lived in two -- `upload-envelope.ts` held the bundle's and the PDF member's, and
 * `upload-failure.ts` held six more `W55B-FIX` had registered beside it because the repairing
 * lane's grant did not reach the first file. Two tables is how one rule gets two wordings, and
 * how a constraint added to one is silently missing from the other. This reads the source, not
 * the exports: an export list is satisfied by a second table behind a re-export, and that is
 * the shape the next duplicate would take.
 */
describe('the upload rule sentences have one owner (D-173)', () => {
  const OWNER = 'web/src/entities/document-version/model/upload-envelope.ts';
  // `uploadPriceList` is another operation with its own file constraints (`non_empty` there is
  // «Файл пуст.», a price list's rule, not a bundle's). It is exempt by name, and the exemption
  // is itself asserted below so that it cannot outlive the table it excuses.
  const OTHER_OPERATION = 'web/src/entities/price-list/';
  const everything = walkFiles(join(WEB_ROOT, 'src'), (path) => /\.tsx?$/.test(path)).map((path) => ({
    path: repoRelative(path),
    text: readText(path),
  }));
  const sources = everything.filter((source) => !source.path.startsWith(OTHER_OPERATION));
  const registered = [...new Set([...UPLOAD_CONSTRAINTS_STATED, ...BUNDLE_CONSTRAINTS, ...PDF_MEMBER_CONSTRAINTS])];

  it('reads the sources it claims to read', () => {
    // A scan that found nothing would pass everything below.
    expect(sources.length).toBeGreaterThan(200);
    expect(sources.map((source) => source.path)).toContain(OWNER);
    expect(registered.length).toBeGreaterThanOrEqual(BUNDLE_CONSTRAINTS.length + PDF_MEMBER_CONSTRAINTS.length);
  });

  it('exempts only a table that exists and says something else', () => {
    const priceList = everything.filter((source) => source.path.startsWith(OTHER_OPERATION));
    const keyed = priceList.filter((source) => /^\s*non_empty\s*:/m.test(source.text));
    expect(keyed.length, 'the exemption excuses nothing: delete it').toBeGreaterThan(0);
    for (const source of keyed) {
      expect(source.text, source.path).not.toContain(uploadConstraintSentence('non_empty') ?? 'no sentence');
    }
  });

  /** An object key spelled as `name:` at the start of a line, quoted or not. */
  const keyPattern = (constraint: string) => new RegExp(`^\\s*['"]?${constraint}['"]?\\s*:`, 'm');

  it('keys every registered constraint in exactly one file, and that file is the owner', () => {
    const stray = registered
      .map((constraint) => ({
        constraint,
        files: sources.filter((source) => keyPattern(constraint).test(source.text)).map((source) => source.path),
      }))
      .filter((entry) => entry.files.length !== 1 || entry.files[0] !== OWNER)
      .map((entry) => `${entry.constraint}: ${entry.files.join(', ') || 'nowhere'}`);
    expect(stray).toEqual([]);
  });

  it('states every sentence once in all of web/src', () => {
    // The page and size sentences are built from the envelope's numbers and are not literals;
    // every other sentence is, and a copy of it anywhere is a second wording waiting to drift.
    const copies = registered
      .map((constraint) => ({ constraint, sentence: uploadConstraintSentence(constraint) ?? '' }))
      .filter((entry) => entry.sentence !== '')
      .map((entry) => ({
        constraint: entry.constraint,
        files: sources.filter((source) => source.text.includes(entry.sentence)).map((source) => source.path),
      }))
      .filter((entry) => entry.files.length !== 1)
      .map((entry) => `${entry.constraint}: ${entry.files.join(', ') || 'nowhere'}`);
    expect(copies).toEqual([]);
  });

  it('can fail: a second table keyed by a registered constraint is seen, a mention of the name is not', () => {
    const secondTable = "const MORE: Record<string, string> = {\n  non_empty: 'Пустое значение.',\n  'plain_base_name': 'Имя.',\n};\n";
    expect(keyPattern('non_empty').test(secondTable)).toBe(true);
    expect(keyPattern('plain_base_name').test(secondTable)).toBe(true);
    expect(keyPattern('non_empty').test("expect(sentence('non_empty')).toBe(x);")).toBe(false);
  });
});
