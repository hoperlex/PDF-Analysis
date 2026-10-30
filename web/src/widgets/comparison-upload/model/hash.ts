/**
 * The SHA-256 of a file, as the contract declares it (`ComparisonUploadFileDeclaration.sha256`, 64 lower-case hex digits).
 *
 * Files are hashed in 1 MiB slices so the temporary intake does not allocate
 * the entire PDF in the browser. The digest parameter is retained for tests.
 */

import { hashStageFile } from '@/shared/lib/sha256-file';

export type Digest = (data: ArrayBuffer) => Promise<ArrayBuffer>;

const subtleDigest: Digest = (data) => crypto.subtle.digest('SHA-256', data);

export function hex(buffer: ArrayBuffer): string {
  return [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

export async function sha256Hex(blob: Blob, digest: Digest = subtleDigest): Promise<string> {
  return digest === subtleDigest ? hashStageFile(blob) : hex(await digest(await blob.arrayBuffer()));
}
