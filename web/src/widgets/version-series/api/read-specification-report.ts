import { getComparisonSpecification, listComparisonSpecificationChanges } from '@/shared/api';
import type { ComparisonSpecification, ComparisonSpecChange, ComparisonTransitionId, Cursor } from '@/shared/api';
import type { SpecificationReport } from '../model/specification-report';

export class SpecificationReportError extends Error {}
const MAX_BYTES = 64 * 1024 * 1024;
function cancelled(signal?: AbortSignal): void { if (signal?.aborted) throw new DOMException('Выгрузка отменена.', 'AbortError'); }
function identity(item: ComparisonSpecification): string {
  return JSON.stringify([item.transition_id, item.comparison_id, item.extraction_a_id, item.extraction_b_id, item.state, item.updated_at,
    item.method, item.phase, item.reason, item.sheets_a, item.sheets_b,
    item.coverage_a?.blocks_total, item.coverage_a?.blocks_covered, item.coverage_a?.rows_total, item.coverage_a?.rows_unresolved,
    item.coverage_b?.blocks_total, item.coverage_b?.blocks_covered, item.coverage_b?.rows_total, item.coverage_b?.rows_unresolved,
    item.totals?.changed, item.totals?.added, item.totals?.removed, item.totals?.unclear, item.totals?.renumbered, item.totals?.moved]);
}

/** Read every page of the public projection, refusing a changed comparison or incomplete read. */
export async function readSpecificationReport(transitionId: ComparisonTransitionId, options: {
  readonly signal?: AbortSignal; readonly onProgress?: (value: { readonly received: number; readonly pages: number }) => void;
} = {}): Promise<SpecificationReport> {
  cancelled(options.signal);
  const requestOptions = options.signal === undefined ? {} : { signal: options.signal };
  const before = (await getComparisonSpecification({ path: { comparison_transition_id: transitionId } }, requestOptions)).data;
  if (before.state !== 'completed' && before.state !== 'incomplete') throw new SpecificationReportError('Выгрузка доступна для сохранённого завершённого или неполного результата. Обновите состояние.');
  const changes: ComparisonSpecChange[] = [];
  const visited = new Set<string>();
  const ids = new Set<string>();
  const encoder = new TextEncoder();
  let bytes = encoder.encode(JSON.stringify(before)).length;
  let cursor: Cursor | undefined;
  let pages = 0;
  for (;;) {
    cancelled(options.signal);
    const result = (await listComparisonSpecificationChanges({ path: { comparison_transition_id: transitionId },
      query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } }, requestOptions)).data;
    for (const change of result.items) {
      if (ids.has(change.change_id)) throw new SpecificationReportError('Получены повторные идентификаторы позиций. Результат мог измениться; неполная выгрузка не создана. Повторите чтение.');
      ids.add(change.change_id);
      bytes += encoder.encode(JSON.stringify(change)).length + 1;
      if (bytes > MAX_BYTES) throw new SpecificationReportError('Полученная API-проекция превышает 64 МиБ. Файл не создан; позиции не исключались.');
      changes.push(change);
    }
    pages += 1;
    options.onProgress?.({ received: changes.length, pages });
    const next = result.page.next_cursor;
    if (next === undefined || next === null) break;
    if (visited.has(next)) throw new SpecificationReportError('API повторил курсор. Полное чтение не подтверждено; файл не создан.');
    visited.add(next); cursor = next;
  }
  cancelled(options.signal);
  const after = (await getComparisonSpecification({ path: { comparison_transition_id: transitionId } }, requestOptions)).data;
  if (identity(before) !== identity(after)) throw new SpecificationReportError('Сравнение изменилось во время чтения. Смешанная выгрузка не создана; повторите для текущего результата.');
  return { format: 'whole-specification-api-projection/1', received_at: new Date().toISOString(), specification: before, changes,
    limitations: [
      'Полная полученная API-проекция изменений позиций: прочитаны все страницы текущего сохранённого результата. Неизменённые позиции этим списком не возвращаются.',
      'Поля ограничены контрактом; отмеченные многоточием сокращения не восстанавливаются этой выгрузкой. Это не полный raw-источник спецификации.',
      'Покрытие блоков и неразобранные строки приведены как сохранены. Неполная сторона не объявляется отсутствующей.',
      'Детальные пакеты извлечения этим API не передаются. Модельные позиции и изменения не подтверждены инженером.',
    ] };
}
