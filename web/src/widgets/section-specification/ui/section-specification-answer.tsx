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
 * **What stands where** (`UIP-S11-03`). The table comes first. The summary by object — the documents with their state, the price list, the
 * totals per currency — lies under the disclosure «Источники и итоги» (open only where a bound stopped the read, because the way out,
 * «Показать только этот объект», is in it), and «Неполные источники: N» is one disclosure at the bottom: the documents the server could
 * not read yet and the current versions nobody classified. Nothing is counted here: the totals are the server's, shown.
 *
 * **The table is grouped by document** (`UIP-S11-02`, the original's «⌄ АР-1 · v2 · 10 строк»): one row-group for each document
 * whose current version is confirmed in the section, keyed by `document_uid` and never by a name or a number. A document with
 * no table says «Спецификация отсутствует» in red; with every object chosen the group names its object too; a group the page
 * boundary tears says how many of its rows are on this page. «+» and «−» in the first graph open and fold every group.
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
const PRICED_HEADINGS = ['Сопоставление', 'Позиция прайс-листа объекта', 'Цена', 'Сумма'] as const;

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
                (не прочитано строк таблиц: {skipped}; причины — в «Спецификации и ценах» комплекта, на вкладке «Оптимизация» объекта)
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
        Итогов по объекту нет: {project.price_state === 'price_list_missing' ? 'у объекта нет прайс-листа.' : 'прайс-лист не читался.'}
      </p>
    );
  }
  const excluded = Object.entries(matching.excluded).filter(([, count]) => count > 0);
  const excludedTotal = excluded.reduce((sum, [, count]) => sum + count, 0);
  return (
    <div data-section-totals={project.project_uid}>
      <h4 className={styles.subheading}>Итого по объекту — по однозначно сопоставленным строкам</h4>
      {matching.totals.length === 0 ? (
        <p data-section-total="none">
          Итога нет: ни одна строка объекта не сопоставлена с одной позицией его прайс-листа в той же единице
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
          ? 'В итог вошли все строки объекта.'
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
          (<Link href={routes.projectOptimisation(project.project_uid)}>вкладка «Оптимизация» объекта</Link>)
        </span>
      </h3>
      <p data-section-price-list={list?.price_list_id ?? 'none'}>
        {list === null
          ? sectionPriceStateMessage(project.price_state)
          : `Прайс-лист «${list.source_filename}», редакция ${list.revision_number}, позиций: ${list.position_count}: ${sectionPriceStateMessage(project.price_state)}.`}
      </p>
      <Sources project={project} />
      <p data-section-project-rows={project.row_count}>Строк спецификации объекта: {project.row_count}.</p>
      <Totals project={project} />
      {onSelectProject === null ? null : (
        <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => onSelectProject(project.project_uid)}>
          Показать только этот объект
        </button>
      )}
    </article>
  );
}

/**
 * «Неполные источники: N» (`UIP-S11-03`, the original's one disclosure at the foot of its frame): the documents of the section the
 * server could not read rows of yet — each with what is missing — and the current versions nobody classified, which the summary does
 * not hold. One list of warnings instead of two blocks; the figure is the count of both, drawn only where there is something to say.
 */
function IncompleteSources({ answer }: { readonly answer: SectionSpecification }) {
  const unread = answer.projects.flatMap((project) =>
    project.sources.filter((source) => source.state !== 'ready').map((source) => ({ project, source })),
  );
  const total = unread.length + answer.excluded_count;
  if (total === 0) return null;
  return (
    <details className={styles.details} data-section-incomplete={total}>
      <summary>Неполные источники: {total}</summary>
      {unread.length === 0 ? null : (
        <ul className={styles.list} data-section-unread-sources={unread.length}>
          {unread.map(({ project, source }) => (
            <li key={source.version_uid} data-section-incomplete-state={source.state}>
              <Link href={routes.project(project.project_uid)}>{project.name}</Link>
              {' / '}
              <Link href={routes.document(project.project_uid, source.document_uid)}>{source.display_title}</Link>
              {' '}— версия {source.version_ordinal}: {sectionSourceStateMessage(source.state)}
            </li>
          ))}
        </ul>
      )}
      {answer.excluded_count === 0 ? null : (
        <>
          <p className={styles.hint} data-section-excluded-versions={answer.excluded_count}>
            Текущие версии без подтверждённого раздела: {answer.excluded_count}. В сводку они не входят.
          </p>
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
        </>
      )}
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

/** One document's rows of this page, in the order the server sent them; a document of the answer with none still has its group. */
interface RowGroup {
  readonly documentUid: string;
  /** The document as the answer lists it; `undefined` for rows of a document the answer does not list. */
  readonly source: SectionSpecificationSource | undefined;
  /** The project the document belongs to, named by the answer; `undefined` when the answer does not list it. */
  readonly project: SectionSpecificationProject | undefined;
  readonly projectUid: string | undefined;
  readonly rows: readonly SectionSpecificationRow[];
}

/**
 * The rows of the page grouped under their document, the documents in the answer's order: project by project, each project's
 * sets as it lists them (`UIP-S11-02`). The identity of a group is the row's `document_uid`. A row whose document the answer does
 * not list is kept under a group of its own and never dropped.
 */
export function groupRowsByDocument(answer: SectionSpecification): readonly RowGroup[] {
  const byDocument = new Map<string, SectionSpecificationRow[]>();
  for (const row of answer.rows?.items ?? []) {
    const held = byDocument.get(row.document_uid);
    if (held === undefined) byDocument.set(row.document_uid, [row]);
    else held.push(row);
  }
  const groups: RowGroup[] = [];
  const listed = new Set<string>();
  for (const project of answer.projects) {
    for (const source of project.sources) {
      listed.add(source.document_uid);
      groups.push({
        documentUid: source.document_uid,
        source,
        project,
        projectUid: project.project_uid,
        rows: byDocument.get(source.document_uid) ?? [],
      });
    }
  }
  const projects = new Map(answer.projects.map((project) => [project.project_uid as string, project] as const));
  for (const [documentUid, rows] of byDocument) {
    if (listed.has(documentUid)) continue;
    const projectUid = rows[0]?.project_uid;
    groups.push({ documentUid, source: undefined, project: projects.get(projectUid ?? ''), projectUid, rows });
  }
  return groups;
}

/** A document has a specification when the server read rows of it; `null` (not read) and `0` are none. */
function hasSpecification(group: RowGroup): boolean {
  return group.source === undefined ? group.rows.length > 0 : (group.source.row_count ?? 0) > 0;
}

function GroupHeader({
  group, span, collapsed, onToggle, withObject, searched,
}: {
  readonly group: RowGroup;
  readonly span: number;
  readonly collapsed: boolean;
  readonly onToggle: () => void;
  /** Every object is in view, so the group says which object its document belongs to. */
  readonly withObject: boolean;
  readonly searched: boolean;
}) {
  const source = group.source;
  const missing = !hasSpecification(group);
  const total = source?.row_count ?? null;
  // The page boundary tore the group: some of its rows are here and the rest are on another page. A search narrows the rows, not
  // the count, so a searched list is not torn, it is filtered.
  const torn = !searched && !missing && total !== null && group.rows.length > 0 && group.rows.length < total;
  return (
    <tr className={styles.groupRow} data-section-group-row={group.documentUid} data-section-group-collapsed={collapsed ? 'yes' : 'no'}>
      <td colSpan={span} className={styles.groupCell}>
        <button type="button" className={styles.groupToggle} aria-expanded={!collapsed} onClick={onToggle}>
          <span className={styles.caret} aria-hidden="true">{collapsed ? '›' : '⌄'}</span>
          <span className={missing ? styles.missing : styles.groupName}>{source?.display_title ?? 'Документ'}</span>
          <span className={styles.hint}>
            {source === undefined ? null : ` · v${source.version_ordinal}`}
            {missing || total === null ? '' : ` · ${total} ${pluralRu(total, ROW_WORD)}`}
            {torn ? `, на этой странице: ${group.rows.length}` : ''}
          </span>
        </button>
        {withObject && group.project !== undefined ? (
          <span className={styles.hint} data-section-group-object="">
            {' · '}
            <Link href={routes.project(group.project.project_uid)}>{group.project.name}</Link>
          </span>
        ) : null}
        {group.projectUid === undefined ? null : (
          <>
            {' '}
            <span className={styles.hint}>
              (<Link href={routes.document(group.projectUid, group.documentUid)}>документ</Link>,{' '}
              <Link href={routes.documentOptimisation(group.projectUid, group.documentUid)}>оптимизация документа</Link>)
            </span>
          </>
        )}
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
  /** True when the page holds rows of another document: this one's rows may be on a page before or after it. */
  readonly otherRows: boolean;
}) {
  if (group.rows.length === 0) {
    const none = !hasSpecification(group);
    const state = group.source?.state;
    return (
      <tr className={styles.noteRow} data-section-group-empty={none ? 'missing' : 'page'}>
        <td />
        <td colSpan={span - 1}>
          {none ? (
            <>
              Спецификация отсутствует
              {state === undefined || state === 'ready' ? null : (
                <span className={styles.hint}> — {sectionSourceStateMessage(state)}</span>
              )}
            </>
          ) : searched ? (
            'По текущему поиску строки спецификации этого документа на этой странице не найдены.'
          ) : otherRows ? (
            'Строки этого документа — на другой странице списка.'
          ) : (
            'Строк спецификации этого документа нет.'
          )}
        </td>
      </tr>
    );
  }
  return (
    <>
      {group.rows.map((row, index) => (
        <Fragment key={row.row_id}>
          {/* The original's category row: where the form's heading changes inside a document. */}
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
  // The documents the reader folded; held by identity so a fold survives another page, and forgotten with the section (the
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
            ? 'Поиск идёт по позиции, наименованию, названию группы, единице измерения и примечанию строк. Итоги объектов от поиска не зависят.'
            : answer.row_count > 0
              ? 'Строки есть, но не на этой странице.'
              : 'Таблиц спецификации с графами «Наименование» и «Кол.» в сохранённом тексте текущих версий раздела не найдено или текст ещё не прочитан — состояние каждого комплекта указано выше.'
        }
      />
    );
  }
  const addresses = addressesOf(answer);
  const groups = groupRowsByDocument(answer);
  // With every object in view a group names its object too; narrowed to one, the object is the screen's.
  const withObject = answer.project_filter === null;
  const span = FORM7_HEADINGS.length + (columns === 'priced' ? PRICED_HEADINGS.length : 0);
  const toggle = (documentUid: string) =>
    setFolded((held) => {
      const next = new Set(held);
      if (next.has(documentUid)) next.delete(documentUid);
      else next.add(documentUid);
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
                  <span className={styles.allToggle} role="group" aria-label="Управление всеми документами">
                    <button type="button" title="Развернуть все документы" aria-label="Развернуть все документы" data-section-expand-all="" onClick={() => setFolded(new Set())}>+</button>
                    <button
                      type="button"
                      title="Свернуть все документы"
                      aria-label="Свернуть все документы"
                      data-section-collapse-all=""
                      onClick={() => setFolded(new Set(groups.map((group) => group.documentUid)))}
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
            const collapsed = folded.has(group.documentUid);
            return (
              <tbody key={group.documentUid} data-section-group={group.documentUid}>
                <GroupHeader
                  group={group}
                  span={span}
                  collapsed={collapsed}
                  onToggle={() => toggle(group.documentUid)}
                  withObject={withObject}
                  searched={searched}
                />
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
        наименования и показаны вместе с ним. Строки разных документов и объектов не объединяются.
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
              : 'У выбранного объекта нет комплектов, текущая версия которых подтверждена для этого раздела.'
          }
        />
      ) : null}
      <RowsTable key={answer.section_code} answer={answer} onPage={onPage} columns={columns} />
      {answer.projects.length === 0 ? null : (
        // `UIP-S11-03`: the summary by object under one disclosure. A read a bound stopped has no table, and what it offers instead —
        // narrowing to one object — is in the summary, so that one stands open.
        <details className={styles.details} open={tooLarge} data-section-summary-panel="">
          <summary>Источники и итоги</summary>
          <p data-section-summary="">
            Объектов в разделе: {answer.projects.length}, комплектов: {answer.source_count}
            {tooLarge ? '.' : `, строк спецификации: ${answer.row_count}.`}
            {' '}Итоги считаются отдельно по каждому объекту и каждой валюте; итога по разделу нет.
          </p>
          {/* `UI-PARITY-DENSE`: the projects side by side, as the original lists its projects in one table (they were stacked, one panel of five paragraphs each). */}
          <div className={styles.projects}>
            {answer.projects.map((project) => (
              <ProjectPanel key={project.project_uid} project={project} onSelectProject={answer.project_filter === null ? onSelectProject : null} />
            ))}
          </div>
        </details>
      )}
      <IncompleteSources answer={answer} />
    </div>
  );
}
