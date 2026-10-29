/**
 * The SHA-256 of a file, as the contract declares it (`ComparisonUploadFileDeclaration.sha256`, 64 lower-case hex digits).
 *
 * The browser has no streaming hash without a package, so a file is read whole and digested by `crypto.subtle`; the
 * envelope's 250 MiB per file bounds what is held, and files are hashed one at a time. The digest function is a
 * parameter so a test can supply its own.
 */

export type Digest = (data: ArrayBuffer) => Promise<ArrayBuffer>;

const subtleDigest: Digest = (data) => crypto.subtle.digest('SHA-256', data);

export function hex(buffer: ArrayBuffer): string {
  return [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

export async function sha256Hex(blob: Blob, digest: Digest = subtleDigest): Promise<string> {
  return hex(await digest(await blob.arrayBuffer()));
}
