import type { StageChainRun, VersionUid } from '@/shared/api';
import { object } from './report';

export interface V3PackageSource { readonly versionUid: VersionUid; readonly side: 'OLD' | 'NEW' }

/** Only the complete persisted catalogue identifies the original PDFs. A list
 * of card evidence can omit a PDF with no generated event and is insufficient. */
export function packageSources(run: StageChainRun | undefined): readonly V3PackageSource[] {
  const catalogue = object(object(run?.experimental_progress)?.source_report)?.source_catalogue;
  if (!Array.isArray(catalogue) || catalogue.length === 0) {
    throw new Error('Полный ZIP недоступен: каталог исходных PDF ещё не сохранён. Отдельные отчёты можно скачать ниже.');
  }
  const sources = new Map<string, V3PackageSource>();
  for (const value of catalogue) {
    const source = object(value);
    if (source === null || typeof source.version_uid !== 'string' || source.version_uid.trim() === '') {
      throw new Error('Полный ZIP недоступен: в каталоге не указана версия одного из исходных PDF.');
    }
    const side = source.side === 'left' ? 'OLD' : source.side === 'right' ? 'NEW'
      : source.original_side === 'OLD' || source.original_side === 'NEW' ? source.original_side : null;
    if (side === null || (source.original_side !== undefined && source.original_side !== side)
        || (source.side !== undefined && source.side !== 'left' && source.side !== 'right')) {
      throw new Error('Полный ZIP недоступен: сторона одного из исходных PDF не определена однозначно.');
    }
    sources.set(`${side}:${source.version_uid}`, { versionUid: source.version_uid, side });
  }
  const values = [...sources.values()];
  if (!values.some((source) => source.side === 'OLD') || !values.some((source) => source.side === 'NEW')) {
    throw new Error('Полный ZIP недоступен: в сохранённом каталоге отсутствуют исходные PDF одной из сторон.');
  }
  return values;
}
