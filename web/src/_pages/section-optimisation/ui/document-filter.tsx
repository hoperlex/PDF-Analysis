'use client';

/**
 * The filter «Документ» in the row of the tabs of «Оптимизация раздела» (`UIP-S11-06`): the original's «Все проекты раздела»,
 * where its «проект» is a document set — what ours calls a document — and not a construction site, which is the top strip's
 * object (`UIC-G-11`). One list for both tabs, made once.
 *
 * The documents offered are the ones the unnarrowed read of the scope lists: the sources of the section's answer, «АР-1 · v2» each
 * (the title and the version of the current one). The filter narrows both tabs to that document; it never merges rows of two
 * documents, every row stays the row of its own document and version. It is drawn only when there is something to choose, so an
 * empty scope shows no list; a document the address names is offered even before the list is in hand — named from the narrowed
 * answer once that lists it, by its identity until then — and is never silently dropped.
 */

import type { DocumentUid, SectionSpecification } from '@/shared/api';

import styles from './section-optimisation-page.module.css';

/** A document of the scope as the list shows it. `objectName` is the object it belongs to (`''` while nothing names it). */
export interface DocumentFilterOption {
  readonly documentUid: DocumentUid;
  readonly label: string;
  readonly objectName: string;
}

/** «АР-1 · v2»: the document's title and the version of its current one. */
export function documentOptionLabel(title: string, versionOrdinal: number): string {
  return `${title} · v${versionOrdinal}`;
}

/**
 * The documents an answer of the section lists, project by project in its order. An answer of another section than
 * `sectionCode` is none of this scope's (a late one, or a placeholder), and lists nothing.
 */
export function documentFilterOptions(answer: SectionSpecification | undefined, sectionCode: string): readonly DocumentFilterOption[] {
  if (answer === undefined || answer.section_code !== sectionCode) return [];
  return answer.projects.flatMap((project) =>
    project.sources.map((source) => ({
      documentUid: source.document_uid,
      label: documentOptionLabel(source.display_title, source.version_ordinal),
      objectName: project.name,
    })),
  );
}

/**
 * The options with the selected document in them: the list as read, and, when it lacks the selected document, that document named by
 * `narrowed` (the answer asked for it) or, failing that, by its identity — the only label true before anything is read.
 */
export function withSelectedDocument(
  options: readonly DocumentFilterOption[],
  selected: DocumentUid | null,
  narrowed: readonly DocumentFilterOption[],
): readonly DocumentFilterOption[] {
  if (selected === null || options.some((option) => option.documentUid === selected)) return options;
  const named = narrowed.find((option) => option.documentUid === selected);
  return [...options, named ?? { documentUid: selected, label: selected, objectName: '' }];
}

export interface DocumentFilterProps {
  readonly options: readonly DocumentFilterOption[];
  /** The document chosen; `null` is «Все документы раздела». */
  readonly value: DocumentUid | null;
  readonly onChange: (documentUid: DocumentUid | null) => void;
}

export function DocumentFilter({ options, value, onChange }: DocumentFilterProps) {
  if (options.length === 0 && value === null) return null;
  // With documents of more than one object in the list, each object's own are grouped under its name: the same title in two
  // objects is two documents, and the list says which is which.
  const objects = [...new Set(options.map((option) => option.objectName))];
  const grouped = objects.length > 1;
  const option = (item: DocumentFilterOption) => (
    <option key={item.documentUid} value={item.documentUid}>
      {item.label}
    </option>
  );
  return (
    <form className={styles.filterBar} aria-label="Документ раздела" onSubmit={(event) => event.preventDefault()} data-section-document-filter={options.length}>
      <div className={styles.filterField}>
        <label htmlFor="section-specification-document">Документ</label>
        <select
          id="section-specification-document"
          value={value ?? ''}
          onChange={(event) => onChange(event.target.value === '' ? null : (event.target.value as DocumentUid))}
        >
          <option value="">Все документы раздела</option>
          {grouped
            ? objects.map((object) => (
                <optgroup key={object} label={object === '' ? 'Без объекта' : object}>
                  {options.filter((item) => item.objectName === object).map(option)}
                </optgroup>
              ))
            : options.map(option)}
        </select>
      </div>
    </form>
  );
}
