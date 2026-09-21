/**
 * The PC-01 input envelope, and the honest limits of a browser-side pre-check.
 *
 * Two things are asserted here that a rendering test could not: that the numbers on
 * screen are the contract's numbers rather than numbers someone typed, and that the
 * pre-check refuses to claim anything about encryption, page count or the text layer —
 * the three properties a browser cannot read without parsing the PDF.
 */

import { describe, expect, it } from 'vitest';

import {
  PC01_UPLOAD_ENVELOPE,
  UPLOAD_ENVELOPE_RULES,
  formatBytes,
  precheckProblemMessage,
  precheckUploadFile,
} from '@/entities/document-version';
import { CONTRACT_PATH, readText } from '../../guards/lib/repo';

const contract = readText(CONTRACT_PATH);

describe('the envelope the user is shown is the envelope the contract declares', () => {
  it('states 25 MiB in bytes, not megabytes', () => {
    expect(PC01_UPLOAD_ENVELOPE.maxBytes).toBe(25 * 1024 * 1024);
    expect(PC01_UPLOAD_ENVELOPE.maxBytes).toBe(26_214_400);
    expect(PC01_UPLOAD_ENVELOPE.maxBytesLabel).toBe('25 MiB');
  });

  it('states 30 pages and one PDF', () => {
    expect(PC01_UPLOAD_ENVELOPE.maxPages).toBe(30);
    expect(PC01_UPLOAD_ENVELOPE.fileCount).toBe(1);
    expect(PC01_UPLOAD_ENVELOPE.mediaType).toBe('application/pdf');
  });

  it('takes those numbers from the contract document, not from this file', () => {
    // The generator emits identifier patterns but not prose limits, so the envelope text
    // is the only place these two numbers can be checked against their source.
    expect(contract).toContain('at most 25 MiB and at most 30 pages');
    expect(contract).toContain('every page carrying extractable embedded text');
  });

  it('names every refusal reason before a file is chosen', () => {
    const text = UPLOAD_ENVELOPE_RULES.join(' ');
    expect(text).toContain('25 MiB');
    expect(text).toContain('30 страниц');
    expect(text.toLowerCase()).toContain('без пароля');
    expect(text.toLowerCase()).toContain('извлекаемый встроенный текст');
    // OCR is never silently substituted, and the panel says so up front.
    expect(text.toLowerCase()).toContain('оптическим распознаванием');
  });
});

describe('the pre-check refuses only what a browser can actually see', () => {
  const pdf = { name: 'ar-2024.pdf', size: 1_000_000, type: 'application/pdf' };

  it('accepts a PDF inside the size bound', () => {
    expect(precheckUploadFile(pdf)).toBeNull();
  });

  it('accepts a file exactly at the bound and refuses one byte more', () => {
    expect(precheckUploadFile({ ...pdf, size: PC01_UPLOAD_ENVELOPE.maxBytes })).toBeNull();
    expect(precheckUploadFile({ ...pdf, size: PC01_UPLOAD_ENVELOPE.maxBytes + 1 })).toBe('too_large');
  });

  it('refuses a declared non-PDF', () => {
    expect(precheckUploadFile({ name: 'ar.zip', size: 10, type: 'application/zip' })).toBe('not_pdf');
    expect(precheckUploadFile({ name: 'ar.pdf', size: 10, type: 'application/zip' })).toBe('not_pdf');
  });

  it('falls back to the extension only when the browser declares nothing', () => {
    expect(precheckUploadFile({ name: 'ar.pdf', size: 10, type: '' })).toBeNull();
    expect(precheckUploadFile({ name: 'AR.PDF', size: 10, type: '' })).toBeNull();
    expect(precheckUploadFile({ name: 'ar.txt', size: 10, type: '' })).toBe('not_pdf');
  });

  it('refuses an empty file', () => {
    expect(precheckUploadFile({ ...pdf, size: 0 })).toBe('empty_file');
  });

  it('claims nothing about encryption, page count or the text layer', () => {
    // A 31-page, password-protected, image-only PDF of legal size passes here, because
    // the browser cannot see any of those three things. The server refuses it, and the
    // screen renders that refusal. A pre-check that guessed would either block a legal
    // file or promise one that will be rejected.
    const problem = precheckUploadFile({ name: 'scanned.pdf', size: 5_000_000, type: 'application/pdf' });
    expect(problem).toBeNull();
  });

  it('gives every problem a message that offers no retry', () => {
    for (const problem of ['not_pdf', 'too_large', 'empty_file'] as const) {
      const message = precheckProblemMessage(problem);
      expect(message.length).toBeGreaterThan(0);
      expect(message.toLowerCase()).not.toContain('try again');
    }
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
