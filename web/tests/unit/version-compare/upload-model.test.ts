/**
 * The upload of «Сравнение версий» without a screen (`CMP-VC-UI-01`): which files go, how they are matched to what the
 * server declared, how a set is confirmed, and the chunked transfer — resumed from the parts the server already holds, one key
 * per intent, retried a bounded number of times, stopped without losing a part.
 *
 * The transfer is driven with an injected transport and clock, so each rule is a state the test builds and a result it reads.
 */

import { describe, expect, it } from 'vitest';

import type { ComparisonProposalSet } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { uploadFailureReasonSentence } from '@/entities/version-series';
import {
  KeyBook,
  PART_SIZE_BYTES,
  PRECHECK_SENTENCES,
  awaitingConfirmation,
  confirmationOf,
  declaredName,
  draftOf,
  groupOf,
  groupsOf,
  hex,
  isPdfName,
  isRetryableFailure,
  matchFiles,
  moveFile,
  needsTransfer,
  partCount,
  pickFiles,
  precheck,
  proposedConfirmation,
  relabel,
  sha256Hex,
  transferFiles,
} from '@/widgets/comparison-upload';
import type { TransferEvents, TransferFile, TransferPorts } from '@/widgets/comparison-upload';

import { DOCUMENT_UID, proposalSets, uid } from './fixtures';

const MIB = 1024 * 1024;

function fakeFile(name: string, size: number, relative = ''): File {
  const file = new File([new Uint8Array(Math.min(size, 16))], name);
  Object.defineProperty(file, 'size', { value: size });
  if (relative !== '') Object.defineProperty(file, 'webkitRelativePath', { value: relative });
  return file;
}

describe('which files go, and under which project', () => {
  it('takes PDFs only and counts the rest', () => {
    const picked = pickFiles([fakeFile('a.pdf', 10), fakeFile('B.PDF', 10), fakeFile('c.zip', 10), fakeFile('d.txt', 10)], 'files');
    expect(picked.files.map((entry) => entry.path)).toEqual(['a.pdf', 'B.PDF']);
    expect(picked.skipped).toBe(2);
    expect(isPdfName('x.Pdf')).toBe(true);
    expect(isPdfName('x.pdf.zip')).toBe(false);
  });

  it('groups by the folder added with «Добавить папку» and by the subfolder with «Добавить папку с проектами»', () => {
    expect(groupOf('Проекты/ЭМ/изм0.pdf', 'one')).toBe('Проекты/ЭМ');
    expect(groupOf('Проекты/ЭМ/изм0.pdf', 'many')).toBe('Проекты/ЭМ');
    expect(groupOf('Проекты/ЭМ/ниже/изм0.pdf', 'many')).toBe('Проекты/ЭМ');
    expect(groupOf('Проекты/ЭМ/ниже/изм0.pdf', 'one')).toBe('Проекты/ЭМ/ниже');
    expect(groupOf('Проекты/изм0.pdf', 'many')).toBe('Проекты');
    expect(groupOf('изм0.pdf', 'many')).toBe('');
  });

  it('lists the picked files by folder with their sizes', () => {
    const picked = pickFiles(
      [fakeFile('a.pdf', 3 * MIB, 'P/A/a.pdf'), fakeFile('b.pdf', MIB, 'P/A/b.pdf'), fakeFile('c.pdf', MIB, 'P/B/c.pdf')],
      'many',
    );
    expect(groupsOf(picked.files).map((group) => [group.group, group.files.length, group.bytes])).toEqual([
      ['P/A', 2, 4 * MIB],
      ['P/B', 1, MIB],
    ]);
  });

  it('declares the tail of a name that is too long, because the end tells files apart', () => {
    const long = `${'д'.repeat(300)}/изм5.pdf`;
    expect(declaredName(long).length).toBe(255);
    expect(declaredName(long).endsWith('/изм5.pdf')).toBe(true);
    expect(declaredName('a/b.pdf')).toBe('a/b.pdf');
  });

  it('refuses before sending what the contract would refuse, in the contract\'s numbers', () => {
    const one = (size: number, name = 'a.pdf') => pickFiles([fakeFile(name, size)], 'files').files;
    expect(precheck([])).toBe('nothing');
    expect(precheck(one(100))).toBeNull();
    expect(precheck(one(0))).toBe('empty_file');
    expect(precheck(one(250 * MIB + 1))).toBe('file_too_large');
    expect(precheck(one(250 * MIB))).toBeNull();
    const many = Array.from({ length: 10_001 }, (_, n) => fakeFile(`f${n}.pdf`, 1));
    expect(precheck(pickFiles(many, 'files').files)).toBe('too_many_files');
    const projects = Array.from({ length: 101 }, (_, n) => fakeFile('a.pdf', 1, `P/${n}/a.pdf`));
    expect(precheck(pickFiles(projects, 'one').files)).toBe('too_many_projects');
    const huge = Array.from({ length: 33 }, (_, n) => fakeFile(`h${n}.pdf`, 250 * MIB));
    expect(precheck(pickFiles(huge, 'files').files)).toBe('batch_too_large');
    for (const sentence of Object.values(PRECHECK_SENTENCES)) expect(sentence).toMatch(/[А-Яа-я]/);
  });

  it('cuts a file into parts of 16 MiB, at least one', () => {
    expect(PART_SIZE_BYTES).toBe(16 * MIB);
    expect(partCount(1)).toBe(1);
    expect(partCount(16 * MIB)).toBe(1);
    expect(partCount(16 * MIB + 1)).toBe(2);
    expect(partCount(250 * MIB)).toBe(16);
  });

  it('hashes with the digest it is given, as lower-case hex', async () => {
    expect(hex(new Uint8Array([0, 15, 255]).buffer)).toBe('000fff');
    const digest = async () => new Uint8Array([1, 2, 3]).buffer;
    expect(await sha256Hex(new Blob(['x']), digest)).toBe('010203');
  });
});

describe('matching the files picked to the files declared', () => {
  const declared = [
    { fileId: 'f1', sha256: 'aa', sizeBytes: 10, displayName: 'one.pdf' },
    { fileId: 'f2', sha256: 'bb', sizeBytes: 20, displayName: 'two.pdf' },
    { fileId: 'f3', sha256: 'bb', sizeBytes: 20, displayName: 'copy.pdf' },
  ];

  it('matches by digest and size, never by name alone', () => {
    const local = [
      { sha256: 'bb', sizeBytes: 20, displayName: 'renamed.pdf', value: 'L-b' },
      { sha256: 'aa', sizeBytes: 10, displayName: 'renamed-too.pdf', value: 'L-a' },
    ];
    const result = matchFiles(declared.slice(0, 2), local);
    expect(result.matched).toEqual([
      { fileId: 'f1', value: 'L-a' },
      { fileId: 'f2', value: 'L-b' },
    ]);
    expect(result.missing).toEqual([]);
    expect(result.extra).toEqual([]);
  });

  it('gives byte-equal files each its own, preferring the declared name, then the order', () => {
    const local = [
      { sha256: 'bb', sizeBytes: 20, displayName: 'copy.pdf', value: 'second' },
      { sha256: 'bb', sizeBytes: 20, displayName: 'two.pdf', value: 'first' },
    ];
    expect(matchFiles(declared.slice(1), local).matched).toEqual([
      { fileId: 'f2', value: 'first' },
      { fileId: 'f3', value: 'second' },
    ]);
  });

  it('names the declared file nothing matched, and the local file nothing wanted', () => {
    const result = matchFiles(declared, [{ sha256: 'aa', sizeBytes: 11, displayName: 'one.pdf', value: 'wrong size' }]);
    expect(result.missing).toEqual(['f1', 'f2', 'f3']);
    expect(result.extra).toEqual(['wrong size']);
  });
});

describe('confirming a set', () => {
  const set: ComparisonProposalSet = proposalSets()[2] as ComparisonProposalSet;

  it('lists exactly the set\'s own files in the proposed order, with the proposed labels', () => {
    expect(draftOf(set).files).toEqual([
      { fileId: uid('cuf', 2), label: 'Версия 1 Изм.0 15.01.2026' },
      { fileId: uid('cuf', 1), label: 'Версия 2 Изм.1 12.02.2026' },
    ]);
    expect(proposedConfirmation(set)).toEqual({
      files: [
        { file_id: uid('cuf', 2), version_label: 'Версия 1 Изм.0 15.01.2026' },
        { file_id: uid('cuf', 1), version_label: 'Версия 2 Изм.1 12.02.2026' },
      ],
      designation: '133/23-ГК-ЭМ3',
      project_stage: 'P',
      section_code: 'EOM',
    });
  });

  it('applies what the reader changed: the order, a label, the designation, the existing document', () => {
    let draft = draftOf(set);
    draft = moveFile(draft, 0, 1);
    draft = relabel(draft, 0, '  первая  ');
    draft = { ...draft, designation: ' ЭМ-2 ', addToExisting: true };
    const body = confirmationOf(set, draft);
    expect(body.files).toEqual([
      { file_id: uid('cuf', 1), version_label: 'первая' },
      { file_id: uid('cuf', 2), version_label: 'Версия 1 Изм.0 15.01.2026' },
    ]);
    expect(body.designation).toBe('ЭМ-2');
    expect(body.existing_document_uid).toBe(DOCUMENT_UID);
  });

  it('sends the stage and the section together or not at all, and the existing document only when chosen', () => {
    const off = confirmationOf(set, { ...draftOf(set), confirmClassification: false });
    expect('project_stage' in off).toBe(false);
    expect('section_code' in off).toBe(false);
    expect('existing_document_uid' in confirmationOf(set, draftOf(set))).toBe(false);
    const half = { ...set } as { project_stage?: string; section_code?: string };
    delete half.section_code;
    const body = confirmationOf(half as ComparisonProposalSet, draftOf(half as ComparisonProposalSet));
    expect('project_stage' in body).toBe(false);
  });

  it('leaves a label out when it is blank, and moves nothing off either end', () => {
    const blank = relabel(draftOf(set), 0, '   ');
    expect(confirmationOf(set, blank).files[0]).toEqual({ file_id: uid('cuf', 2) });
    expect(moveFile(draftOf(set), 0, -1)).toEqual(draftOf(set));
    expect(moveFile(draftOf(set), 1, 1)).toEqual(draftOf(set));
  });

  it('«Подтвердить порядок во всех проектах» acts on the sets that wait for a word, and on no other', () => {
    expect(awaitingConfirmation(proposalSets()).map((entry) => entry.state)).toEqual(['needs_confirmation']);
  });
});

describe('the sentence of a file that failed', () => {
  const envelope = (constraint: string) => (constraint === 'not_encrypted' ? 'Документ зашифрован.' : null);

  it('says the retryable reasons, the PDF envelope\'s own refusal, and a reason it does not know', () => {
    expect(uploadFailureReasonSentence('comparison_file_sha256', envelope)).toMatch(/Контрольная сумма/);
    expect(uploadFailureReasonSentence('staged_upload_lost', envelope)).toMatch(/Отправьте файл заново/);
    expect(uploadFailureReasonSentence('content_not_encrypted', envelope)).toBe('Документ зашифрован.');
    expect(uploadFailureReasonSentence('content_a_rule_from_the_future', envelope)).toMatch(/Причина не описана/);
    expect(uploadFailureReasonSentence(undefined, envelope)).toBe('');
  });
});

// ------------------------------------------------------------------------------------- the transfer

interface Call {
  readonly kind: 'put' | 'complete';
  readonly fileId: string;
  readonly part?: number;
  readonly key: string;
  readonly bytes?: number;
}

function ports(script: (call: Call, attempt: number) => unknown = () => undefined) {
  const calls: Call[] = [];
  const attempts = new Map<string, number>();
  let minted = 0;
  const run = async (call: Call): Promise<void> => {
    calls.push(call);
    const id = `${call.kind}|${call.fileId}|${call.part ?? 0}`;
    const attempt = (attempts.get(id) ?? 0) + 1;
    attempts.set(id, attempt);
    const outcome = script(call, attempt);
    if (outcome !== undefined) throw outcome;
  };
  const transport: TransferPorts = {
    putPart: (fileId, part, body, key) => run({ kind: 'put', fileId, part, key, bytes: body.size }),
    complete: (fileId, key) => run({ kind: 'complete', fileId, key }),
    mintKey: () => `key-${(minted += 1)}`,
    classify: (error) => (error instanceof ApiError ? (error.retryable ? 'retry' : error.errorCode === 'conflict' ? 'batch' : 'file') : 'file'),
    sleep: async () => undefined,
  };
  return { calls, transport, keys: () => new KeyBook(transport.mintKey) };
}

function refusal(code: 'dependency_unavailable' | 'conflict' | 'storage_integrity_error', retryable: boolean): ApiError {
  return new ApiError(
    code === 'conflict' ? 409 : code === 'dependency_unavailable' ? 503 : 422,
    { contract_version: '1.12.0', error_code: code, message: 'm', correlation_id: 'c', retryable },
    'c',
  );
}

function transferFile(over: Partial<TransferFile> & { fileId: string }): TransferFile {
  return { sizeBytes: 40, state: 'declared', partsStaged: 0, blob: new Blob([new Uint8Array(40)]), ...over };
}

const noEvents: TransferEvents = { onProgress: () => undefined, onFileDone: () => undefined, onFileFailed: () => undefined };
const run = (files: TransferFile[], transport: TransferPorts, keys: KeyBook, signal = new AbortController().signal, events: TransferEvents = noEvents) =>
  transferFiles(files, transport, events, keys, signal, { partSize: 16, retries: 2, retryDelayMs: 1 });

describe('the chunked transfer', () => {
  it('sends every part in order from 1 and completes the file', async () => {
    const { calls, transport, keys } = ports();
    expect(await run([transferFile({ fileId: 'f1' })], transport, keys())).toBe('finished');
    expect(calls.map((call) => [call.kind, call.part, call.bytes])).toEqual([
      ['put', 1, 16], ['put', 2, 16], ['put', 3, 8], ['complete', undefined, undefined],
    ]);
  });

  it('resumes from the parts the server already holds, and only completes a file whose parts are all staged', async () => {
    const { calls, transport, keys } = ports();
    await run([transferFile({ fileId: 'f1', state: 'uploading', partsStaged: 2 }), transferFile({ fileId: 'f2', state: 'uploading', partsStaged: 3 })], transport, keys());
    expect(calls.map((call) => [call.fileId, call.kind, call.part])).toEqual([
      ['f1', 'put', 3], ['f1', 'complete', undefined], ['f2', 'complete', undefined],
    ]);
  });

  it('leaves a verified file and a file refused for good alone', async () => {
    const { calls, transport, keys } = ports();
    await run(
      [
        transferFile({ fileId: 'v', state: 'verified', partsStaged: 3 }),
        transferFile({ fileId: 'x', state: 'failed', failureReason: 'content_not_encrypted' }),
      ],
      transport,
      keys(),
    );
    expect(calls).toEqual([]);
    expect(needsTransfer({ state: 'failed', failureReason: 'content_not_encrypted' })).toBe(false);
    expect(needsTransfer({ state: 'declared' })).toBe(true);
  });

  it('sends a file that failed its integrity again from part 1 under NEW keys, the other files under the same', async () => {
    const book = ports();
    const keys = book.keys();
    await run([transferFile({ fileId: 'f1' })], book.transport, keys);
    const first = book.calls.filter((call) => call.kind === 'put').map((call) => call.key);
    book.calls.length = 0;
    await run([transferFile({ fileId: 'f1', state: 'failed', failureReason: 'comparison_file_sha256', partsStaged: 3 })], book.transport, keys);
    const again = book.calls.filter((call) => call.kind === 'put');
    expect(again.map((call) => call.part)).toEqual([1, 2, 3]);
    expect(again.map((call) => call.key).some((key) => first.includes(key))).toBe(false);
    expect(isRetryableFailure({ state: 'failed', failureReason: 'comparison_file_sha256' })).toBe(true);
  });

  it('reuses the key of a part on a retry and after a stop, so a part sent twice is one part', async () => {
    const book = ports((call, attempt) => (call.kind === 'put' && call.part === 2 && attempt < 3 ? refusal('dependency_unavailable', true) : undefined));
    expect(await run([transferFile({ fileId: 'f1' })], book.transport, book.keys())).toBe('finished');
    const second = book.calls.filter((call) => call.kind === 'put' && call.part === 2);
    expect(second.length).toBe(3);
    expect(new Set(second.map((call) => call.key)).size).toBe(1);
  });

  it('continues after a stop with the key the part had before it, so the part the stop interrupted is one part', async () => {
    const controller = new AbortController();
    const book = ports((call) => {
      if (call.kind === 'put' && call.part === 2 && !controller.signal.aborted) controller.abort();
      return undefined;
    });
    const keys = book.keys();
    expect(await run([transferFile({ fileId: 'f1' })], book.transport, keys, controller.signal)).toBe('stopped');
    const interrupted = book.calls.find((call) => call.kind === 'put' && call.part === 2)?.key;
    expect(interrupted).toBeDefined();
    book.calls.length = 0;
    // The server holds part 1 only, as it would after the stop: the next run starts at part 2 and reuses its key.
    expect(await run([transferFile({ fileId: 'f1', state: 'uploading', partsStaged: 1 })], book.transport, keys)).toBe('finished');
    expect(book.calls.find((call) => call.kind === 'put' && call.part === 2)?.key).toBe(interrupted);
    expect(book.calls.map((call) => call.kind === 'put' ? call.part : 'complete')).toEqual([2, 3, 'complete']);
  });

  it('tries a retryable refusal a bounded number of times, then ends that file and goes on to the next', async () => {
    const failed: string[] = [];
    const done: string[] = [];
    const book = ports((call) => (call.fileId === 'bad' && call.kind === 'put' ? refusal('dependency_unavailable', true) : undefined));
    const outcome = await run([transferFile({ fileId: 'bad' }), transferFile({ fileId: 'good' })], book.transport, book.keys(), new AbortController().signal, {
      onProgress: () => undefined,
      onFileDone: (id) => done.push(id),
      onFileFailed: (id) => failed.push(id),
    });
    expect(outcome).toBe('finished');
    expect(failed).toEqual(['bad']);
    expect(done).toEqual(['good']);
    expect(book.calls.filter((call) => call.fileId === 'bad').length).toBe(3);
  });

  it('ends the whole transfer when the batch cannot take a part in its state', async () => {
    const failed: string[] = [];
    const book = ports((call) => (call.kind === 'put' ? refusal('conflict', false) : undefined));
    const outcome = await run([transferFile({ fileId: 'a' }), transferFile({ fileId: 'b' })], book.transport, book.keys(), new AbortController().signal, {
      onProgress: () => undefined,
      onFileDone: () => undefined,
      onFileFailed: (id) => failed.push(id),
    });
    expect(outcome).toBe('batch_refused');
    expect(failed).toEqual(['a']);
    expect(book.calls.filter((call) => call.fileId === 'b')).toEqual([]);
  });

  it('stops on an abort, keeps what was staged and does not call the file failed', async () => {
    const controller = new AbortController();
    const failed: string[] = [];
    const book = ports((call) => {
      if (call.kind === 'put' && call.part === 2) controller.abort();
      return undefined;
    });
    const outcome = await run([transferFile({ fileId: 'f1' })], book.transport, book.keys(), controller.signal, {
      onProgress: () => undefined,
      onFileDone: () => undefined,
      onFileFailed: (id) => failed.push(id),
    });
    expect(outcome).toBe('stopped');
    expect(failed).toEqual([]);
    expect(book.calls.filter((call) => call.kind === 'complete')).toEqual([]);
  });

  it('reports the bytes sent as it goes', async () => {
    const seen: number[] = [];
    const book = ports();
    await run([transferFile({ fileId: 'f1' })], book.transport, book.keys(), new AbortController().signal, {
      onProgress: (_id, done) => seen.push(done),
      onFileDone: () => undefined,
      onFileFailed: () => undefined,
    });
    expect(seen).toEqual([0, 16, 32, 40]);
  });
});
