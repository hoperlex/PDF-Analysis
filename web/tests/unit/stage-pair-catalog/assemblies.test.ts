import type { DocumentVersion } from '@/shared/api';
import { describe, expect, it } from 'vitest';

import { latestDocuments } from '@/widgets/stage-pair-catalog/model/assemblies';
import { NOW, PROJECT_UID, uid } from '../version-compare/fixtures';

function document(ordinal: number, uidValue = uid('doc', 1)): DocumentVersion {
  return { document_uid: uidValue, version_uid: uid('ver', ordinal), version_ordinal: ordinal,
    project_uid: PROJECT_UID, byte_size: 20, media_type: 'application/pdf', input_manifest: [],
    page_count: 1, published_at: NOW, sha256: 'd'.repeat(64) };
}

describe('assembly document choices', () => {
  it('uses canonical document identity and the newest ordinal even when titles match', () => {
    const older = { ...document(1), display_title: 'План' };
    const latest = { ...document(3), display_title: 'План новый' };
    const another = { ...document(2, uid('doc', 2)), display_title: 'План' };
    expect(latestDocuments([latest, older, another])).toEqual([latest, another]);
  });
});
