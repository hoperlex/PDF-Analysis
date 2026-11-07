/**
 * One answer of `getSectionSpecification`, rendered (`W63-SECTION-FORM7-01`). Pure: the
 * container (`section-specification-section.tsx`) owns the queries and the filters, this owns
 * the reading.
 *
 * **The section is a filter, not an identity.** What is shown is project by project: each
 * project with the sets of it whose *current* version an expert confirmed in the section, its
 * own price list and its own totals. The rows below carry their project, set, version, sheet
 * and page on every line, and two projects listing the same product are two rows — nothing is
 * merged, and there is no total for the section. Totals are per project and per currency.
 *
 * **A state is said, never shown as an empty table.** A set without a published run or a saved
 * text, a project without a price list, a bound that stops the read, a current version nobody
 * classified — each is a sentence saying what is missing and where it is done.
 *
 * **The money rule is the screen's too.** A price and an amount appear only on a row that
 * counts in its project's total — matched to one position of that project's price list, in the
 * same unit, with a numeric quantity (`amount` present). Every other row shows a dash and says
 * why. Amounts are the server's exact decimals, grouped for reading and never rounded.
 */

import Link from 'next/link';
import { Fragment, useState } from 'react';

import type {
  SectionSpecification,
  SectionSpecificationProject,
  SectionSpecificationRow,
  SectionSpecificationSource,
} from '@/shared/api';
import { routes } from '@/shared/lib';
import { EmptyState } from '@/shared/ui';
import { pluralRu } from '@/entities/document-version';
import {
  sectionExclusionLabel,
  sectionLimitMessage,
  sectionPriceStateMessage,
  sectionRowStatusLabel,
  sectionSourceStateMessage,
  stageMark,
} from '@/entities/section-specification';
import {
  formatDecimal,
  formatMoney,
  quantityIssueLabel,
  specificationBasisLabel,
  specificationExclusionLabel,
  specificationReasonLabel,
  specificationUnitLabel,
} from '@/entities/specification-price';

import styles from './section-specification.module.css';

export interface SectionSpecificationAnswerProps {
  readonly answer: SectionSpecification;
  /** Move to another page of rows; `null` while a page is loading. */
  readonly onPage: ((offset: number) => void) | null;
  /** Narrow the section to one project; `null` when the project is already the filter. */
  readonly onSelectProject: ((projectUid: string) => void) | null;
  /**
   * `form7` (the default) is the original's table: the nine columns of the GOST form, the rows grouped under their project.
   * `priced` adds the four columns the original lacks — the match against the project's price list, the position, the price and
   * the amount — to the same grouped table. The choice is the reader's (`UI-B-23`).
   */
  readonly columns?: SectionSpecificationColumns | undefined;
}

export type SectionSpecificationColumns = 'form7' | 'priced';

const SET_WORD = ['комплект', 'комплекта', 'комплектов'] as const;
const ROW_WORD = ['строка', 'строки', 'строк'] as const;

/** The nine columns of Form 7, as the original numbers them (`GOST`, graph 1–9). */
const FORM7_HEADINGS = [
  'Позиция',
  'Наименование и техническая характеристика',
  'Тип, марка, обозначение документа, опросного листа',
  'Код оборудования, изделия, материала',
  'Завод-изготовитель',
  'Единица измерения',
  'Количество',
  'Масса единицы, кг',
  'Примечание',
] as const;
const PRICED_HEADINGS = ['Сопоставление', 'Позиция прайс-листа проекта', 'Цена', 'Сумма'] as const;

const STATUS_TONES: Readonly<Record<string, string>> = {
  matched: 'am-badge--ok',
  ambiguous: 'am-badge--degraded',
  unmatched: 'am-badge--inert',
  price_list_missing: 'am-badge--inert',
};

/** What a row's address needs from the answer: the project's name and the set's title. */
interface Addresses {
  readonly project: ReadonlyMap<string, SectionSpecificationProject>;
  readonly source: ReadonlyMap<string, SectionSpecificationSource>;
}

function addressesOf(answer: SectionSpecification): Addresses {
  const project = new Map<string, SectionSpecificationProject>();
  const source = new Map<string, SectionSpecificationSource>();
  for (const item of answer.projects) {
    project.set(item.project_uid, item);
    for (const entry of item.sources) source.set(entry.version_uid, entry);
  }
  return { project, source };
}

function skippedCount(source: SectionSpecificationSource): number {
  const counts = source.skipped_by_reason;
  return counts === null ? 0 : Object.values(counts).reduce((sum, count) => sum + count, 0);
}

function Sources({ project }: { readonly project: SectionSpecificationProject }) {
  return (
    <ul className={styles.list} data-section-sources={project.sources.length}>
      {project.sources.map((source) => {
        const skipped = skippedCount(source);
        return (
          <li key={source.version_uid} data-section-source-state={source.state}>
            <Link href={routes.document(project.project_uid, source.document_uid)}>{source.display_title}</Link>
            {' '}(<Link href={routes.documentOptimisation(project.project_uid, source.document_uid)}>оптимизация комплекта</Link>)
            {' '}— версия {source.version_ordinal}, стадия {stageMark(source.project_stage)}, страниц: {source.page_count}:{' '}
            {sectionSourceStateMessage(source.state)}
            {source.state === 'ready'
              ? `; таблиц: ${source.table_count ?? 0}, строк: ${source.row_count ?? 0}`
              : null}
            {skipped > 0 ? (
              <span className={styles.hint}>
                {' '}
                (не прочитано строк таблиц: {skipped}; причины — в «Спецификации и ценах» комплекта, на вкладке «Оптимизация» проекта)
              </span>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

function Totals({ project }: { readonly project: SectionSpecificationProject }) {
  const matching = project.matching;
  if (matching === null) {
    return (
      <p data-section-total="none" className={styles.hint}>
        Итогов по проекту нет: {project.price_state === 'price_list_missing' ? 'у проекта нет прайс-листа.' : 'прайс-лист не читался.'}
      </p>
    );
  }
  const excluded = Object.entries(matching.excluded).filter(([, count]) => count > 0);
  const excludedTotal = excluded.reduce((sum, [, count]) => sum + count, 0);
  return (
    <div data-section-totals={project.project_uid}>
      <h4 className={styles.subheading}>Итого по проекту — по однозначно сопоставленным строкам</h4>
      {matching.totals.length === 0 ? (
        <p data-section-total="none">
          Итога нет: ни одна строка проекта не сопоставлена с одной позицией его прайс-листа в той же единице
          измерения и с числовым количеством.
        </p>
      ) : (
        <ul className={styles.list}>
          {matching.totals.map((total) => (
            <li key={total.currency} data-section-total={total.currency}>
              <strong>{formatMoney(total.amount, total.currency)}</strong> — строк: {total.row_count}
            </li>
          ))}
        </ul>
      )}
      {matching.totals.length > 1 ? (
        <p className="am-note">Итоги в разных валютах не складываются и не пересчитываются.</p>
      ) : null}
      <p data-section-excluded={excludedTotal}>
        Сопоставлено: {matching.counts.matched}, неоднозначно: {matching.counts.ambiguous}, не сопоставлено:{' '}
        {matching.counts.unmatched}.{' '}
        {excludedTotal === 0
          ? 'В итог вошли все строки проекта.'
          : `Не вошли в итог строк: ${excludedTotal} — ${excluded
              .map(([reason, count]) => `${specificationExclusionLabel(reason)}: ${count}`)
              .join('; ')}.`}
      </p>
    </div>
  );
}

function ProjectPanel({
  project,
  onSelectProject,
}: {
  readonly project: SectionSpecificationProject;
  readonly onSelectProject: ((projectUid: string) => void) | null;
}) {
  const list = project.price_list;
  return (
    <article className={styles.project} data-section-project={project.project_uid} data-section-price-state={project.price_state}>
      <h3 className={styles.subheading}>
        <Link href={routes.project(project.project_uid)}>{project.name}</Link>
        {' '}
        <span className={styles.hint}>
          (<Link href={routes.projectOptimisation(project.project_uid)}>вкладка «Оптимизация» проекта</Link>)
        </span>
      </h3>
      <p data-section-price-list={list?.price_list_id ?? 'none'}>
        {list === null
          ? sectionPriceStateMessage(project.price_state)
          : `Прайс-лист «${list.source_filename}», редакция ${list.revision_number}, позиций: ${list.position_count}: ${sectionPriceStateMessage(project.price_state)}.`}
      </p>
      <Sources project={project} />
      <p data-section-project-rows={project.row_count}>Строк спецификации проекта: {project.row_count}.</p>
      <Totals project={project} />
      {onSelectProject === null ? null : (
        <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => onSelectProject(project.project_uid)}>
          Показать только этот проект
        </button>
      )}
    </article>
  );
}

function Excluded({ answer }: { readonly answer: SectionSpecification }) {
  if (answer.excluded_count === 0) return null;
  return (
    <details className={styles.details} data-section-excluded-versions={answer.excluded_count}>
      <summary>Текущие версии без подтверждённого раздела: {answer.excluded_count}. В сводку они не входят.</summary>
      <ul className={styles.list}>
        {answer.excluded.map((item) => (
          <li key={item.version_uid}>
            <Link href={routes.project(item.project_uid)}>{item.project_name}</Link>
            {' / '}
            <Link href={routes.document(item.project_uid, item.document_uid)}>{item.display_title}</Link>
            {' '}— версия {item.version_ordinal}: {sectionExclusionLabel(item.reason)}
          </li>
        ))}
      </ul>
      {answer.excluded.length < answer.excluded_count ? (
        <p className="am-note">Показаны первые {answer.excluded.length}; счёт полный.</p>
      ) : null}
    </details>
  );
}

function Quantity({ row }: { readonly row: SectionSpecificationRow }) {
  if (row.quantity !== null) return <>{formatDecimal(row.quantity)}</>;
  return (
    <>
      {row.quantity_text ?? '—'}
      {row.quantity_issue === null ? null : (
        <span className={styles.hint}> ({quantityIssueLabel(row.quantity_issue)})</span>
      )}
    </>
  );
}

function Match({ row }: { readonly row: SectionSpecificationRow }) {
  const tone = STATUS_TONES[row.price_status] ?? 'am-badge--inert';
  return (
    <>
      <span className={`am-badge ${tone}`}>{sectionRowStatusLabel(row.price_status)}</span>
      <span className={styles.hint}>
        {row.basis !== null ? ` ${specificationBasisLabel(row.basis)}` : null}
        {row.reason !== null ? ` — ${specificationReasonLabel(row.reason)}` : null}
        {row.price_status === 'ambiguous' ? `; кандидатов: ${row.candidate_count}` : null}
      </span>
    </>
  );
}

function PricePosition({ row }: { readonly row: SectionSpecificationRow }) {
  const position = row.price_position;
  if (position === null) return <>—</>;
  const extras = [position.mark, position.code].filter((value): value is string => value !== null);
  return (
    <>
      {position.name}
      {extras.length === 0 ? null : <span className={styles.hint}> ({extras.join(', ')})</span>}
      <span className={styles.hint}>, строка прайс-листа {position.row_number}</span>
    </>
  );
}

function Row({ row, addresses, columns }: { readonly row: SectionSpecificationRow; readonly addresses: Addresses; readonly columns: SectionSpecificationColumns }) {
  const counted = row.amount !== null && row.price_position !== null;
  const source = addresses.source.get(row.version_uid);
  const place = row.sheet_label === null ? `с. ${row.page_number}` : `л. ${row.sheet_label} / с. ${row.page_number}`;
  return (
    <tr
      data-section-row={row.row_id}
      data-section-row-project={row.project_uid}
      data-section-status={row.price_status}
      data-section-counted={counted ? 'yes' : 'no'}
    >
      <td className={`${styles.cell} ${styles.center}`} title={`строки ${row.line_start}–${row.line_end}`}>{row.position ?? '—'}</td>
      <td className={styles.cell}>
        {row.name}
        {/* The address every row keeps (`W63-SECTION-FORM7-01`): the set, its version, the sheet and the page, one muted line under the name. */}
        <span className={styles.address} data-section-row-address="">
          <Link href={routes.document(row.project_uid, row.document_uid)}>{source?.display_title ?? 'Комплект'}</Link>
          {' '}— версия {source?.version_ordinal ?? '—'}, {place}
          {' '}(<Link href={routes.documentOptimisation(row.project_uid, row.document_uid)}>оптимизация</Link>)
        </span>
      </td>
      {/* Graphs 3–5 are not separated from the name in the saved text; the form's columns stay, and say so below the table. */}
      <td className={styles.cell}>—</td>
      <td className={styles.cell}>—</td>
      <td className={styles.cell}>—</td>
      <td className={`${styles.cell} ${styles.center}`}>{row.unit !== null ? specificationUnitLabel(row.unit) : (row.unit_text ?? '—')}</td>
      <td className={`${styles.cell} ${styles.center}`}><Quantity row={row} /></td>
      <td className={`${styles.cell} ${styles.center}`}>{row.mass_text ?? '—'}</td>
      <td className={styles.cell}>{row.note ?? '—'}</td>
      {columns === 'priced' ? (
        <>
          <td className={styles.cell}><Match row={row} /></td>
          <td className={styles.cell}><PricePosition row={row} /></td>
          <td className={`${styles.cell} ${styles.number}`} data-section-price={counted ? row.price_position?.unit_price : 'none'}>
            {counted ? formatMoney(row.price_position?.unit_price ?? null, row.price_position?.currency ?? null) : '—'}
          </td>
          <td className={`${styles.cell} ${styles.number}`} data-section-amount={row.amount ?? 'none'}>
            {counted ? formatMoney(row.amount, row.price_position?.currency ?? null) : '—'}
            {!counted && row.excluded_reason !== null ? (
              <span className={styles.hint}> ({specificationExclusionLabel(row.excluded_reason)})</span>
            ) : null}
          </td>
        </>
      ) : null}
    </tr>
  );
}

function Pager({ answer, onPage }: Pick<SectionSpecificationAnswerProps, 'answer' | 'onPage'>) {
  const rows = answer.rows;
  if (rows === null || rows.total <= rows.limit) return null;
  const last = rows.offset + rows.items.length;
  return (
    <div className="am-pager" data-section-pager="">
      <span>Строки {rows.offset + 1}–{last} из {rows.total}</span>
      <button
        type="button"
        className="am-button am-button--quiet"
        disabled={onPage === null || rows.offset === 0}
        onClick={() => onPage?.(Math.max(0, rows.offset - rows.limit))}
      >
        Предыдущие
      </button>
      <button
        type="button"
        className="am-button am-button--quiet"
        disabled={onPage === null || rows.next_offset === null}
        onClick={() => rows.next_offset !== null && onPage?.(rows.next_offset)}
      >
        Следующие
      </button>
    </div>
  );
}

/** One project's rows of this page, in the order the server sent them; a project of the answer with none still has its group. */
interface RowGroup {
  readonly projectUid: string;
  readonly project: SectionSpecificationProject | undefined;
  readonly rows: readonly SectionSpecificationRow[];
}

/**
 * The rows of the page grouped under their project, the projects in the answer's order (`UI-B-23`). A row whose project the
 * answer does not list is kept under its own group and never dropped.
 */
export function groupRowsByProject(answer: SectionSpecification): readonly RowGroup[] {
  const byProject = new Map<string, SectionSpecificationRow[]>();
  for (const row of answer.rows?.items ?? []) {
    const held = byProject.get(row.project_uid);
    if (held === undefined) byProject.set(row.project_uid, [row]);
    else held.push(row);
  }
  const groups: RowGroup[] = answer.projects.map((project) => ({
    projectUid: project.project_uid,
    project,
    rows: byProject.get(project.project_uid) ?? [],
  }));
  const listed = new Set(answer.projects.map((project) => project.project_uid as string));
  for (const [projectUid, rows] of byProject) {
    if (!listed.has(projectUid)) groups.push({ projectUid, project: undefined, rows });
  }
  return groups;
}

function GroupHeader({
  group, span, collapsed, onToggle,
}: {
  readonly group: RowGroup;
  readonly span: number;
  readonly collapsed: boolean;
  readonly onToggle: () => void;
}) {
  const project = group.project;
  const missing = project !== undefined && project.row_count === 0;
  const sets = project?.sources.length ?? 0;
  return (
    <tr className={styles.groupRow} data-section-group-row={group.projectUid} data-section-group-collapsed={collapsed ? 'yes' : 'no'}>
      <td colSpan={span} className={styles.groupCell}>
        <button type="button" className={styles.groupToggle} aria-expanded={!collapsed} onClick={onToggle}>
          <span className={styles.caret} aria-hidden="true">{collapsed ? '›' : '⌄'}</span>
          <span className={missing ? styles.missing : styles.groupName}>{project?.name ?? 'Проект'}</span>
          {project === undefined ? null : (
            <span className={styles.hint}>
              {' '}· {sets} {pluralRu(sets, SET_WORD)}
              {missing ? '' : ` · ${project.row_count} ${pluralRu(project.row_count, ROW_WORD)}`}
            </span>
          )}
        </button>
        {' '}
        <span className={styles.hint}>
          (<Link href={routes.project(group.projectUid)}>проект</Link>,{' '}
          <Link href={routes.projectOptimisation(group.projectUid)}>вкладка «Оптимизация» проекта</Link>)
        </span>
      </td>
    </tr>
  );
}

function GroupBody({
  group, span, addresses, columns, searched, otherRows,
}: {
  readonly group: RowGroup;
  readonly span: number;
  readonly addresses: Addresses;
  readonly columns: SectionSpecificationColumns;
  readonly searched: boolean;
  /** True when the page holds rows of another project: this one's rows may be on a page before or after it. */
  readonly otherRows: boolean;
}) {
  const project = group.project;
  if (group.rows.length === 0) {
    const none = project !== undefined && project.row_count === 0;
    return (
      <tr className={styles.noteRow} data-section-group-empty={none ? 'missing' : 'page'}>
        <td />
        <td colSpan={span - 1}>
          {none
            ? 'Спецификация отсутствует'
            : searched
              ? 'По текущему поиску строки спецификации этого проекта на этой странице не найдены.'
              : otherRows
                ? 'Строки этого проекта — на другой странице списка.'
                : 'Строк спецификации этого проекта нет.'}
        </td>
      </tr>
    );
  }
  return (
    <>
      {group.rows.map((row, index) => (
        <Fragment key={row.row_id}>
          {/* The original's category row: where the form's heading changes inside a project. */}
          {row.group !== null && row.group !== group.rows[index - 1]?.group ? (
            <tr className={styles.categoryRow} data-section-category={row.group}>
              <td />
              <td colSpan={span - 1}><span>{row.group}</span></td>
            </tr>
          ) : null}
          <Row row={row} addresses={addresses} columns={columns} />
        </Fragment>
      ))}
    </>
  );
}

function RowsTable({ answer, onPage, columns }: Pick<SectionSpecificationAnswerProps, 'answer' | 'onPage'> & { readonly columns: SectionSpecificationColumns }) {
  // The projects the reader folded; held by identity so a fold survives another page, and forgotten with the section (the
  // container keys this table by it). Expanded by default, as the original.
  const [folded, setFolded] = useState<ReadonlySet<string>>(new Set());
  const rows = answer.rows;
  if (rows === null) return null;
  const searched = answer.query !== null;
  if (rows.total === 0) {
    return (
      <EmptyState
        title={searched ? 'По запросу строк не найдено' : 'Строк спецификации в разделе нет'}
        detail={
          searched
            ? 'Поиск идёт по позиции, наименованию, названию группы, единице измерения и примечанию строк. Итоги проектов от поиска не зависят.'
            : answer.row_count > 0
              ? 'Строки есть, но не на этой странице.'
              : 'Таблиц спецификации с графами «Наименование» и «Кол.» в сохранённом тексте текущих версий раздела не найдено или текст ещё не прочитан — состояние каждого комплекта указано выше.'
        }
      />
    );
  }
  const addresses = addressesOf(answer);
  const groups = groupRowsByProject(answer);
  const span = FORM7_HEADINGS.length + (columns === 'priced' ? PRICED_HEADINGS.length : 0);
  const toggle = (projectUid: string) =>
    setFolded((held) => {
      const next = new Set(held);
      if (next.has(projectUid)) next.delete(projectUid);
      else next.add(projectUid);
      return next;
    });
  return (
    <>
      <div className={styles.frame}>
        <table className={styles.table} aria-label="Сводная спецификация раздела: форма 7" data-section-columns={columns}>
          <thead>
            <tr>
              <th className={styles.cell} scope="col">
                <span className={styles.positionHeading}>
                  <span>{FORM7_HEADINGS[0]}</span>
                  <span className={styles.allToggle} role="group" aria-label="Управление всеми проектами">
                    <button type="button" title="Развернуть все проекты" aria-label="Развернуть все проекты" data-section-expand-all="" onClick={() => setFolded(new Set())}>+</button>
                    <button
                      type="button"
                      title="Свернуть все проекты"
                      aria-label="Свернуть все проекты"
                      data-section-collapse-all=""
                      onClick={() => setFolded(new Set(groups.map((group) => group.projectUid)))}
                    >
                      −
                    </button>
                  </span>
                </span>
              </th>
              {FORM7_HEADINGS.slice(1).map((heading) => <th key={heading} className={styles.cell} scope="col">{heading}</th>)}
              {columns === 'priced' ? PRICED_HEADINGS.map((heading) => <th key={heading} className={styles.cell} scope="col">{heading}</th>) : null}
            </tr>
            {/* The form's own row of graph numbers; decoration, not a header. */}
            <tr className={styles.columnNumbers} aria-hidden="true">
              {FORM7_HEADINGS.map((heading, index) => <th key={heading} className={styles.cell}>{index + 1}</th>)}
              {columns === 'priced' ? <th className={styles.cell} colSpan={PRICED_HEADINGS.length} /> : null}
            </tr>
          </thead>
          {groups.map((group) => {
            const collapsed = folded.has(group.projectUid);
            return (
              <tbody key={group.projectUid} data-section-group={group.projectUid}>
                <GroupHeader group={group} span={span} collapsed={collapsed} onToggle={() => toggle(group.projectUid)} />
                {collapsed ? null : (
                  <GroupBody
                    group={group}
                    span={span}
                    addresses={addresses}
                    columns={columns}
                    searched={searched}
                    otherRows={groups.some((other) => other !== group && other.rows.length > 0)}
                  />
                )}
              </tbody>
            );
          })}
        </table>
      </div>
      <p className="am-note">
        В сохранённом тексте графы «Тип, марка», «Код» и «Завод-изготовитель» не отделены от
        наименования и показаны вместе с ним. Строки разных проектов не объединяются.
      </p>
      <Pager answer={answer} onPage={onPage} />
    </>
  );
}

export function SectionSpecificationAnswer({ answer, onPage, onSelectProject, columns = 'form7' }: SectionSpecificationAnswerProps) {
  const tooLarge = answer.state === 'section_too_large';
  return (
    <div data-section-state={answer.state} data-section-code={answer.section_code}>
      {tooLarge ? (
        <div role="status" data-section-limit={answer.limit_reason ?? 'unknown'}>
          <EmptyState
            title="Раздел слишком велик для одного чтения"
            detail={answer.limit_reason === null ? sectionLimitMessage('') : sectionLimitMessage(answer.limit_reason)}
          />
        </div>
      ) : null}
      {answer.projects.length === 0 && !tooLarge ? (
        <EmptyState
          title="В разделе нет подтверждённых комплектов"
          detail={
            answer.project_filter === null
              ? 'В сводку входят комплекты, текущую версию которых эксперт подтвердил для этого раздела на экране версии. Таких комплектов пока нет.'
              : 'У выбранного проекта нет комплектов, текущая версия которых подтверждена для этого раздела.'
          }
        />
      ) : (
        <>
          <p data-section-summary="">
            Проектов в разделе: {answer.projects.length}, комплектов: {answer.source_count}
            {tooLarge ? '.' : `, строк спецификации: ${answer.row_count}.`}
            {' '}Итоги считаются отдельно по каждому проекту и каждой валюте; итога по разделу нет.
          </p>
          {/* `UI-PARITY-DENSE`: the projects side by side, as the original lists its projects in one table (they were stacked, one panel of five paragraphs each). */}
          <div className={styles.projects}>
            {answer.projects.map((project) => (
              <ProjectPanel key={project.project_uid} project={project} onSelectProject={answer.project_filter === null ? onSelectProject : null} />
            ))}
          </div>
        </>
      )}
      <Excluded answer={answer} />
      <RowsTable key={answer.section_code} answer={answer} onPage={onPage} columns={columns} />
    </div>
  );
}
