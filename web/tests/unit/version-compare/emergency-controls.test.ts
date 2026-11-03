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

  it('states the archive policy and requires a file before importing', () => {
    const markup = renderScreen(newClient(), createElement(ZipImport, { projectUid: PROJECT_UID, disabled: false, onImported: () => undefined }));
    // `SECTION-STATS-UNCAPPED-1030` (hotfix `af581631`): the temporary statistics mode lifted the
    // application's limits on the archive's size and on the number of PDFs (16 MiB, 100 PDF and 256 MiB
    // before it), so the screen says that they are lifted and keeps the rules that remain: one level of
    // nested archives, and a foreign file or `__MACOSX` refused.
    for (const sentence of [
      'прикладные лимиты объёма ZIP и количества PDF сняты', 'Допустим один уровень вложенных ZIP',
      '__MACOSX отклоняются', 'Импортировать ZIP',
    ]) expect(markup).toContain(sentence);
    // And it does not state a limit the server no longer holds.
    for (const lifted of ['16 МиБ', '100 PDF', '256 МиБ']) expect(markup).not.toContain(lifted);
    expect(markup).toMatch(/disabled=""[^>]*>Импортировать ZIP/);
  });

  it('a reader cannot select or submit an archive', () => {
    const markup = renderScreen(newClient(), createElement(ZipImport, { projectUid: PROJECT_UID, disabled: true, onImported: () => undefined }));
    expect(markup).toMatch(/type="file"[^>]*disabled=""/);
    expect(markup).toMatch(/disabled=""[^>]*>Импортировать ZIP/);
  });
});
