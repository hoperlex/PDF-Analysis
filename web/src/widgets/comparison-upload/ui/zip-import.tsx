'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { ComparisonUpload, ProjectUid } from '@/shared/api';
import { importComparisonZip, newIdempotencyKey } from '@/shared/api';
import { COMPARISON_KEYS, comparisonFailure } from '@/entities/version-series';

export function ZipImport({ projectUid, disabled, onImported }: {
  readonly projectUid: ProjectUid; readonly disabled: boolean; readonly onImported: (upload: ComparisonUpload) => void;
}) {
  const client = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const key = useRef(newIdempotencyKey());
  const call = useMutation({ mutationFn: async () => {
    if (file === null) throw new Error('Выберите ZIP');
    // Member names are retained in the archive. A local Cyrillic filename must
    // not be sent as a raw HTTP header (Fetch rejects non-Latin-1 header values).
    return (await importComparisonZip({ path: { project_uid: projectUid }, body: file, idempotencyKey: key.current })).data;
  }, onSuccess: (upload) => {
    void client.invalidateQueries({ queryKey: COMPARISON_KEYS.all }); onImported(upload);
  } });
  return <section role="group" aria-label="Импорт ZIP с версиями" data-comparison-zip-import="">
    <label>ZIP с PDF версий <input type="file" accept=".zip,application/zip" disabled={disabled || call.isPending} onChange={(event) => {
      const chosen = event.target.files?.[0] ?? null;
      key.current = newIdempotencyKey(); call.reset(); setFile(chosen);
      setProblem(chosen !== null && chosen.size === 0 ? 'Выберите непустой ZIP.' : null);
    }} /></label>
    <p className="am-note">Временный режим сбора статистики: прикладные лимиты объёма ZIP и количества PDF сняты. Допустим один уровень вложенных ZIP. Посторонние файлы и __MACOSX отклоняются; все PDF проверяются до импорта. ZIP и отдельные PDF загружаются раздельно.</p>
    <button type="button" className="am-button am-button--quiet am-button--small" disabled={disabled || file === null || problem !== null || call.isPending} onClick={() => call.mutate()}>Импортировать ZIP</button>
    {call.isPending ? <p role="status">Проверяем архив и PDF, затем создаём предложение комплектов…</p> : null}
    {problem === null ? null : <p role="alert">{problem}</p>}
    {call.error === null ? null : <p role="alert">{comparisonFailure(call.error).detail} Повтор использует тот же ключ и продолжает принятую загрузку.</p>}
  </section>;
}
