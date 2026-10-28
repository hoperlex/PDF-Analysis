/**
 * The chunked transfer of declared files, resumable and stoppable (ADR-0025 decision 10, `CMP-INGEST-01` section 2).
 *
 * A declared file is sent in parts of at most 16 MiB (`uploadComparisonUploadPart`, numbered from 1 with no gap), then
 * completed (`completeComparisonUploadFile`: the server assembles, verifies the whole against the declared SHA-256 and
 * size, publishes, and reads the PDF). Rules, each held by a test:
 *
 *  - **Resume.** A file the server already holds `parts_staged` parts of is sent from the next part; a file all of whose
 *    parts are staged is only completed; a verified file is not touched. Stopping and continuing is therefore the same
 *    call on a refreshed upload.
 *  - **One key per intent.** The `Idempotency-Key` of a part is minted once for (file, part, attempt generation) and
 *    reused on every retry of it, so a part sent twice is one part. A file that failed its integrity check is sent
 *    again from part 1 under a new generation: its bytes may differ from the first try's, and the same key with other
 *    bytes would be `idempotency_key_reuse`.
 *  - **Retry, bounded.** A refusal the contract marks retryable (and a network failure) is tried again with a growing
 *    wait, at most `retries` times; anything else ends that file as failed and the transfer goes on to the next one.
 *  - **Stop.** An abort ends the request in flight and the transfer returns `stopped`; nothing is lost, the staged parts stay.
 *  - **A batch that cannot take a part** (`comparison_upload_state`: paused, cancelled, completed) ends the whole transfer.
 *
 * Plain TypeScript with the transport, the clock and the key minting injected.
 */

import type { ComparisonUploadFileState } from '@/shared/api';

import { PART_SIZE_BYTES, partCount } from './files';

/** The file as the server declared it back, with the local bytes it must be matched to. */
export interface TransferFile {
  readonly fileId: string;
  readonly sizeBytes: number;
  readonly state: ComparisonUploadFileState;
  readonly partsStaged: number;
  readonly failureReason?: string | undefined;
  readonly blob: Blob;
}

export interface TransferPorts {
  readonly putPart: (fileId: string, partNumber: number, body: Blob, idempotencyKey: string, signal: AbortSignal) => Promise<void>;
  readonly complete: (fileId: string, idempotencyKey: string, signal: AbortSignal) => Promise<void>;
  readonly mintKey: () => string;
  /** How a thrown value is to be treated: tried again, or ended for this file, or ends the whole batch. */
  readonly classify: (error: unknown) => 'retry' | 'file' | 'batch';
  readonly sleep: (ms: number, signal: AbortSignal) => Promise<void>;
}

export interface TransferEvents {
  readonly onProgress: (fileId: string, bytesDone: number, bytesTotal: number) => void;
  readonly onFileDone: (fileId: string) => void;
  readonly onFileFailed: (fileId: string, error: unknown) => void;
}

export interface TransferOptions {
  readonly partSize?: number;
  readonly retries?: number;
  readonly retryDelayMs?: number;
}

/** The keys minted so far, so a retry — or a continue after a stop — reuses the key of its intent. */
export class KeyBook {
  private readonly keys = new Map<string, string>();
  private readonly generations = new Map<string, number>();

  constructor(private readonly mint: () => string) {}

  generationOf(fileId: string): number {
    return this.generations.get(fileId) ?? 0;
  }

  /** The file is sent again from the start: new keys for every part, because its bytes may not be the first try's. */
  nextGeneration(fileId: string): void {
    this.generations.set(fileId, this.generationOf(fileId) + 1);
  }

  keyFor(fileId: string, partNumber: number): string {
    const id = `${fileId}|${partNumber}|${this.generationOf(fileId)}`;
    const held = this.keys.get(id);
    if (held !== undefined) return held;
    const minted = this.mint();
    this.keys.set(id, minted);
    return minted;
  }
}

/** The file failed for a reason a second send can mend (`CMP-INGEST-01` `RETRYABLE_FILE_REASONS`). */
export const RETRYABLE_FILE_REASONS: readonly string[] = ['comparison_file_sha256', 'comparison_file_size', 'staged_upload_lost'];

export function isRetryableFailure(file: Pick<TransferFile, 'state' | 'failureReason'>): boolean {
  return file.state === 'failed' && file.failureReason !== undefined && RETRYABLE_FILE_REASONS.includes(file.failureReason);
}

/** Whether a transfer has anything to do for the file. */
export function needsTransfer(file: Pick<TransferFile, 'state' | 'failureReason'>): boolean {
  return file.state === 'declared' || file.state === 'uploading' || isRetryableFailure(file);
}

export type TransferOutcome = 'finished' | 'stopped' | 'batch_refused';

class Stopped extends Error {}
class BatchRefused extends Error {
  readonly refusal: unknown;

  constructor(refusal: unknown) {
    super('batch refused');
    this.refusal = refusal;
  }
}

async function attempt<T>(
  run: () => Promise<T>,
  ports: TransferPorts,
  signal: AbortSignal,
  retries: number,
  delay: number,
): Promise<T> {
  for (let tried = 0; ; tried += 1) {
    if (signal.aborted) throw new Stopped();
    try {
      return await run();
    } catch (error) {
      if (signal.aborted) throw new Stopped();
      const kind = ports.classify(error);
      if (kind === 'batch') throw new BatchRefused(error);
      if (kind === 'retry' && tried < retries) {
        await ports.sleep(delay * 2 ** tried, signal);
        continue;
      }
      throw error;
    }
  }
}

export async function transferFiles(
  files: readonly TransferFile[],
  ports: TransferPorts,
  events: TransferEvents,
  keys: KeyBook,
  signal: AbortSignal,
  options: TransferOptions = {},
): Promise<TransferOutcome> {
  const partSize = options.partSize ?? PART_SIZE_BYTES;
  const retries = options.retries ?? 3;
  const delay = options.retryDelayMs ?? 800;
  for (const file of files) {
    if (!needsTransfer(file)) continue;
    if (isRetryableFailure(file)) keys.nextGeneration(file.fileId);
    const parts = partCount(file.sizeBytes, partSize);
    const first = isRetryableFailure(file) ? 1 : Math.min(file.partsStaged, parts) + 1;
    try {
      events.onProgress(file.fileId, Math.min(file.sizeBytes, (first - 1) * partSize), file.sizeBytes);
      for (let number = first; number <= parts; number += 1) {
        const start = (number - 1) * partSize;
        const body = file.blob.slice(start, Math.min(file.sizeBytes, start + partSize));
        const key = keys.keyFor(file.fileId, number);
        await attempt(() => ports.putPart(file.fileId, number, body, key, signal), ports, signal, retries, delay);
        events.onProgress(file.fileId, Math.min(file.sizeBytes, start + partSize), file.sizeBytes);
      }
      const completion = keys.keyFor(file.fileId, 0);
      await attempt(() => ports.complete(file.fileId, completion, signal), ports, signal, retries, delay);
      events.onFileDone(file.fileId);
    } catch (error) {
      if (error instanceof Stopped) return 'stopped';
      if (error instanceof BatchRefused) {
        events.onFileFailed(file.fileId, error.refusal);
        return 'batch_refused';
      }
      events.onFileFailed(file.fileId, error);
    }
  }
  return 'finished';
}
