/**
 * Which local file is which declared file.
 *
 * The server answers `createComparisonUpload` with the batch and each file's identity; the browser then has to send the
 * bytes of the right file under the right identity. A name is a hint and never an identity, so the match is by what the
 * declaration carried: the SHA-256 and the size, and — when two files are byte-equal — the declared name, then the order.
 * After a reload the same function matches the files a reader picks *again* to the files an unfinished batch still waits
 * for, and names the ones it could not match.
 */

export interface Declared {
  readonly fileId: string;
  readonly sha256: string;
  readonly sizeBytes: number;
  readonly displayName: string;
}

export interface Local<T> {
  readonly sha256: string;
  readonly sizeBytes: number;
  readonly displayName: string;
  readonly value: T;
}

export interface Matched<T> {
  readonly fileId: string;
  readonly value: T;
}

export interface Matching<T> {
  readonly matched: readonly Matched<T>[];
  /** Declared files with no local file: the batch cannot be finished without them. */
  readonly missing: readonly string[];
  /** Local files that no declared file wants. */
  readonly extra: readonly T[];
}

export function matchFiles<T>(declared: readonly Declared[], local: readonly Local<T>[]): Matching<T> {
  const unused = [...local];
  const matched: Matched<T>[] = [];
  const missing: string[] = [];
  for (const file of declared) {
    const equal = unused.filter((candidate) => candidate.sha256 === file.sha256 && candidate.sizeBytes === file.sizeBytes);
    const chosen = equal.find((candidate) => candidate.displayName === file.displayName) ?? equal[0];
    if (chosen === undefined) {
      missing.push(file.fileId);
      continue;
    }
    unused.splice(unused.indexOf(chosen), 1);
    matched.push({ fileId: file.fileId, value: chosen.value });
  }
  return { matched, missing, extra: unused.map((candidate) => candidate.value) };
}
