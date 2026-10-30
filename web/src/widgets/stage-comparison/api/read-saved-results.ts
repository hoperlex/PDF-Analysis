import { getExtendedRunReview, getRunStatus, isApiError, listRunFindings } from '@/shared/api';
import type { Cursor, Finding, RunId, VersionUid } from '@/shared/api';
import type { SavedResultSide } from '../model/saved-results';
import { savedObject } from '../model/saved-results';

export class SavedResultReadError extends Error {}
const MAX_BYTES = 64 * 1024 * 1024;
const MAX_FINDINGS = 20000;
const TERMINAL = new Set(['published', 'partial', 'failed', 'cancelled']);

export async function readSavedResult(runId: RunId, versionUid: VersionUid, signal: AbortSignal,
  progress: (received: number) => void): Promise<SavedResultSide> {
  const before = (await getRunStatus({ path: { run_id: runId } }, { signal })).data;
  if (before.run_id !== runId || before.version_uid !== versionUid || !TERMINAL.has(before.state)) throw new SavedResultReadError('Для сравнения сохранённых результатов нужны завершённые прогоны одной версии.');
  const encoder = new TextEncoder();
  let bytes = 0;
  const account = (value: unknown) => { bytes += encoder.encode(JSON.stringify(value)).length; if (bytes > MAX_BYTES) throw new SavedResultReadError('Сохранённые данные превышают 64 МиБ на прогон. Неполное сравнение не построено.'); };
  const findings: Finding[] | null = typeof before.published_finding_count === 'number' ? [] : null;
  if (findings !== null) {
    let cursor: Cursor | undefined;
    const visited = new Set<string>();
    const ids = new Set<string>();
    let pages = 0;
    for (;;) {
      signal.throwIfAborted();
      if (++pages > 1000) throw new SavedResultReadError('Достигнут предел 1000 страниц списка. Неполное сравнение не построено.');
      const page = (await listRunFindings({ path: { run_id: runId }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } }, { signal })).data;
      for (const row of page.items) {
        if (row.run_id !== runId || row.version_uid !== versionUid || row.project_uid !== before.project_uid || ids.has(row.finding_uid)) throw new SavedResultReadError('Идентичность находок изменилась или повторилась при чтении. Обновите данные и повторите.');
        ids.add(row.finding_uid); findings.push(row); account(row);
        if (findings.length > MAX_FINDINGS) throw new SavedResultReadError('Получено более 20000 находок. Неполное сравнение не построено.');
      }
      progress(findings.length);
      const next = page.page.next_cursor;
      if (next === null || next === undefined) break;
      if (visited.has(next)) throw new SavedResultReadError('Повторился курсор списка находок. Полное чтение не подтверждено.');
      visited.add(next); cursor = next;
    }
    if (findings.length !== before.published_finding_count) throw new SavedResultReadError('Число полученных находок не совпадает с сохранённым итогом прогона. Обновите данные и повторите.');
  }
  let extended: SavedResultSide['extended'] = null;
  let extendedUnavailable = false;
  try {
    extended = (await getExtendedRunReview({ path: { run_id: runId } }, { signal })).data;
    if (extended.run_id !== runId || extended.status === 'running') throw new SavedResultReadError('Расширенный анализ ещё не завершён. Дождитесь итоговой записи и повторите чтение.');
    if (extended.result?.version_uid !== undefined && extended.result.version_uid !== versionUid) throw new SavedResultReadError('Сохранённый анализ относится к другой версии. Сравнение не построено.');
    const observations = extended.result?.observations;
    if (observations !== undefined && (!Array.isArray(observations) || observations.some((row) => savedObject(row) === null))) throw new SavedResultReadError('Сохранённый список предварительных наблюдений имеет неподдерживаемую форму. Сопоставление без этих записей не построено.');
    if (Array.isArray(observations) && observations.length > 20000) throw new SavedResultReadError('Получено более 20000 предварительных наблюдений. Неполное сравнение не построено.');
    const globalStatus = savedObject(extended.result?.global_cross_window)?.status;
    if (globalStatus === 'queued' || globalStatus === 'running') throw new SavedResultReadError('Межоконная сверка ещё не завершена. Повторите чтение после её итоговой записи.');
    account(extended);
  } catch (error) {
    if (signal.aborted || error instanceof SavedResultReadError || !isApiError(error)
      || !['not_found', 'dependency_unavailable'].includes(error.errorCode)) throw error;
    extendedUnavailable = true;
  }
  const after = (await getRunStatus({ path: { run_id: runId } }, { signal })).data;
  if (after.run_id !== before.run_id || after.version_uid !== before.version_uid || after.project_uid !== before.project_uid
    || after.state !== before.state || after.terminal_at !== before.terminal_at || after.published_finding_count !== before.published_finding_count) throw new SavedResultReadError('Прогон изменился во время чтения. Смешанное сравнение не построено.');
  return { run: after, findings, extended, extendedUnavailable, receivedAt: new Date().toISOString() };
}
