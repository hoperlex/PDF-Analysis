import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { SpecificationPanel } from '@/widgets/version-series/ui/specification-panel';
import { ZipImport } from '@/widgets/comparison-upload/ui/zip-import';
import { newClient, renderScreen } from '../screens/harness';
import { PROJECT_UID } from './fixtures';

describe('explicit version comparison controls', () => {
  it('offers whole-spec access without mounting an estimate or starting a paid job', () => {
    const markup = renderScreen(newClient(), createElement(SpecificationPanel, { seriesId: 'csr_01J00000000000000000000000', mayAct: true }));
    expect(markup).toContain('Полные спецификации (СО)');
    expect(markup).toContain('aria-expanded="false"');
    expect(markup).not.toContain('data-estimate-panel');
  });

  it('states archive bounds and rejection policy and requires a file before importing', () => {
    const markup = renderScreen(newClient(), createElement(ZipImport, { projectUid: PROJECT_UID, disabled: false, onImported: () => undefined }));
    for (const sentence of ['16 МиБ', '100 PDF', '256 МиБ', '__MACOSX отклоняются', 'Импортировать ZIP']) expect(markup).toContain(sentence);
    expect(markup).toMatch(/disabled=""[^>]*>Импортировать ZIP/);
  });

  it('a reader cannot select or submit an archive', () => {
    const markup = renderScreen(newClient(), createElement(ZipImport, { projectUid: PROJECT_UID, disabled: true, onImported: () => undefined }));
    expect(markup).toMatch(/type="file"[^>]*disabled=""/);
    expect(markup).toMatch(/disabled=""[^>]*>Импортировать ZIP/);
  });
});
