'use client';

import { useMemo, useState } from 'react';
import { ObservationList } from './observation-list';
import styles from './extended-review.module.css';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }

function GroupOrigins({ group, observations, rawRecords, sources, fallbackVersion, projectUid }: {
  readonly group: RecordValue; readonly observations: readonly RecordValue[]; readonly sources: readonly RecordValue[];
  readonly rawRecords: unknown; readonly fallbackVersion: string; readonly projectUid?: string;
}) {
  const [open, setOpen] = useState(false);
  const [originPage, setOriginPage] = useState(0);
  const origins = objects(group.origin_records);
  const resolved = origins.flatMap((origin) => {
    const index = origin.raw_index;
    if (typeof index !== 'number' || !Number.isSafeInteger(index) || index < 0) return [];
    const item = object((Array.isArray(rawRecords) ? rawRecords : observations)[index]);
    if (item === null || (origin.observation_id ?? null) !== (item.observation_id ?? null) || (origin.window_id ?? null) !== (item.window_id ?? null)
      || group.title !== item.title || group.description !== item.description) return [];
    return [{ origin, item, index }];
  });
  const pages = Math.max(1, Math.ceil(resolved.length / 25));
  const current = Math.min(originPage, pages - 1);
  const shown = resolved.slice(current * 25, (current + 1) * 25);
  return <details onToggle={(event) => setOpen(event.currentTarget.open)}><summary>Исходные записи и отдельные рекомендации · {origins.length}</summary>
    {open ? <>
      {resolved.length !== origins.length ? <p role="status">Часть ссылок группы не разрешилась в этой записи. Для проверки откройте «Все исходные» или полную выгрузку; отсутствующие связи не подменяются.</p> : null}
      <p>Рекомендации и нормативные статусы показаны отдельно у каждого исходного наблюдения. Общее модельное решение для группы не создаётся.</p>
      <details><summary>Происхождение группы · по 25 связей</summary><ul>{shown.map(({ origin, index }, ordinal) => <li key={`${index}:${ordinal}`}>Исходная запись №{index + 1}; окно <code>{text(origin.window_id) || 'Не передано'}</code>; наблюдение <code>{text(origin.observation_id) || 'Не передано'}</code>; SHA256 <code>{text(origin.observation_sha256) || 'Не передан'}</code>.</li>)}</ul>{resolved.length > 25 ? <nav className={styles.toolbar} aria-label="Страницы происхождения группы"><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setOriginPage(current - 1)}>Предыдущие связи</button><span>{current + 1} из {pages}</span><button type="button" className="am-button am-button--quiet" disabled={current + 1 >= pages} onClick={() => setOriginPage(current + 1)}>Следующие связи</button></nav> : null}</details>
      <ObservationList observations={resolved.map(({ item }) => item)} sources={sources} fallbackVersion={fallbackVersion} anchorId={`extended-group-${text(group.group_id)}-origins`} {...(projectUid === undefined ? {} : { projectUid })} />
    </> : null}
  </details>;
}

export function ConsolidatedObservations({ groups: value, consolidation: reading, observations, rawRecords, sources, fallbackVersion, projectUid }: {
  readonly groups: unknown; readonly consolidation: unknown; readonly observations: readonly RecordValue[];
  readonly rawRecords: unknown; readonly sources: readonly RecordValue[]; readonly fallbackVersion: string; readonly projectUid?: string;
}) {
  const [view, setView] = useState<'groups' | 'raw'>('groups');
  const [search, setSearch] = useState('');
  const [pageSize, setPageSize] = useState(25);
  const [page, setPage] = useState(0);
  const groups = useMemo(() => objects(value), [value]);
  const consolidation = object(reading);
  const needle = search.trim().toLocaleLowerCase('ru');
  const matches = groups.filter((group) => !needle || [group.title, group.description, group.group_id,
    ...(Array.isArray(group.source_ids) ? group.source_ids : []), ...(Array.isArray(group.window_ids) ? group.window_ids : [])].map(text).join('\n').toLocaleLowerCase('ru').includes(needle));
  const pages = Math.max(1, Math.ceil(matches.length / pageSize));
  const current = Math.min(page, pages - 1);
  const shown = matches.slice(current * pageSize, (current + 1) * pageSize);
  return <section id="extended-observations" className={styles.candidatePanel} aria-label="Группы повторяющихся наблюдений">
    <h3>Наблюдения между окнами</h3>
    <p>Группировка объединяет только записи с совпадающими текстом и категорией и общим фактическим источником. Похожие формулировки с разными источниками остаются отдельными. Все исходные записи сохранены.</p>
    <p>Исходных записей: {count(consolidation?.raw_count)} · групп: {count(consolidation?.group_count)} · объединённых групп: {count(consolidation?.merged_group_count)} · снято повторных представлений: {count(consolidation?.coalesced_count)}.</p>
    <p>Это представление повторов. Оно не создаёт канонических находок, общего решения критика или решений эксперта. Полные выгрузки содержат все исходные данные, независимо от выбранного вида.</p>
    <div className={styles.toolbar} role="group" aria-label="Вид наблюдений"><button type="button" className="am-button am-button--quiet" aria-pressed={view === 'groups'} onClick={() => setView('groups')}>Группы повторов</button><button type="button" className="am-button am-button--quiet" aria-pressed={view === 'raw'} onClick={() => setView('raw')}>Все исходные · {observations.length}</button></div>
    {view === 'raw' ? <ObservationList observations={observations} sources={sources} fallbackVersion={fallbackVersion} anchorId="extended-all-raw-observations" {...(projectUid === undefined ? {} : { projectUid })} /> : <>
      <div className={styles.filters}><label>Поиск группы, исходного текста или источника<input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} /></label><label>Групп на странице<select value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(0); }}><option value={25}>25</option><option value={50}>50</option><option value={100}>100</option></select></label></div>
      <p aria-live="polite">По поиску: {matches.length} из {groups.length}. Показано {shown.length === 0 ? 0 : current * pageSize + 1}–{current * pageSize + shown.length}.</p>
      {shown.length === 0 ? <p>Групп по этому поиску нет. Все исходные записи доступны в соседнем виде.</p> : <ol className={styles.observations} start={current * pageSize + 1}>{shown.map((group, index) => <li key={text(group.group_id) || index} data-consolidated-group={text(group.group_id)}>
        <h4>{text(group.title) || 'Группа без заголовка'}</h4><p className={styles.description}>{text(group.description)}</p>
        <p>Исходных записей: {count(group.origin_count)} · источников: {count(group.source_count)}. Окна: {Array.isArray(group.window_ids) ? group.window_ids.map(text).filter(Boolean).join(', ') || 'Не переданы' : 'Не переданы'}.</p>
        {group.grouping_status === 'source_binding_unavailable' ? <p>Запись оставлена отдельно: подтверждённая связь с источником отсутствует или противоречива. Это не подтверждённый повтор.</p> : null}
        <GroupOrigins group={group} observations={observations} rawRecords={rawRecords} sources={sources} fallbackVersion={fallbackVersion} {...(projectUid === undefined ? {} : { projectUid })} />
      </li>)}</ol>}
      {matches.length > pageSize ? <nav className={styles.toolbar} aria-label="Страницы групп повторов"><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие группы</button><span>Страница {current + 1} из {pages}</span><button type="button" className="am-button am-button--quiet" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Следующие группы</button></nav> : null}
    </>}
  </section>;
}
