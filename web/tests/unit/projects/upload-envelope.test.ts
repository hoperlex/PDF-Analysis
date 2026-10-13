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
import { CONTRACT_PATH, REPO_ROOT, readJson, readText } from '../../guards/lib/repo';
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
  it('registers exactly the eighteen the contract registers', () => {
    expect(registeredBundleConstraints()).toEqual([...BUNDLE_CONSTRAINTS]);
  });

  it('has a sentence for each of them and for the PDF member constraints it keeps', () => {
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
