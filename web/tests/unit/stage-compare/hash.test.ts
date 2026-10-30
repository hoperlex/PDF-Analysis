import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';

import { StageSha256, hashStageFile } from '@/_pages/stage-compare/model/hash';

const reference = (data: Uint8Array) => createHash('sha256').update(data).digest('hex');

describe('stage upload file digest', () => {
  it('matches SHA-256 at padding and block boundaries', () => {
    for (const size of [0, 1, 3, 55, 56, 63, 64, 65, 127, 128, 129, 1024]) {
      const bytes = Uint8Array.from({ length: size }, (_, index) => index % 251);
      const digest = new StageSha256();
      for (let offset = 0; offset < bytes.length; offset += 17) {
        digest.update(bytes.subarray(offset, offset + 17));
      }
      expect(digest.hex()).toBe(reference(bytes));
    }
  });

  it('hashes a file in slices without reading it as one buffer', async () => {
    const bytes = Uint8Array.from({ length: 1024 * 1024 + 71 }, (_, index) => index % 251);
    const steps: number[] = [];
    const digest = await hashStageFile(new Blob([bytes]), (read) => steps.push(read));
    expect(digest).toBe(reference(bytes));
    expect(steps).toEqual([1024 * 1024, bytes.length]);
  });
});
