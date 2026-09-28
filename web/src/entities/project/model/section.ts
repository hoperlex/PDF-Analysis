/**
 * The sections a project's working documentation is organised into.
 *
 * **Where the set comes from.** The legacy application organises work by project section
 * and carries fourteen of them. `docs/program/DEBT_REGISTER.md` `D-56` records that set
 * and its order, read out of `backend/app/pipeline/stages/prepare/task_builder.py:1362`
 * — a file that is not in this repository, which is why the register is cited here rather
 * than a path nobody can open. The codes below are that list, unchanged and in that
 * order. The Russian names are this application's own, because legacy carries the codes
 * and not their expansions.
 *
 * **What a section is here, updated at `W46-WIRE` (`F-3`).** A reseal landed after this
 * module was first written and made two of its claims false: `document.section` is now a
 * real, stored, checked field (a document's version carries an optional `section`, and the
 * upload refuses a malformed one with a `422`), and the dashboard now counts published
 * documents per section, server-side (`getDashboardSummary`'s `section_breakdown`,
 * `widgets/dashboard`). Neither claim below survives as it was written:
 *
 *   - it is **not true** any more that "the contract has no section field anywhere" —
 *     it does, and it round-trips;
 *   - it is **not true** any more that "nothing checks a document's section" — the
 *     `422 validation_failed` on an unrecognised or blank value is exactly a check.
 *
 * **What is still true, and is the reason a section still reads as navigation here.** This
 * product's own upload form (`widgets/upload-panel`, `features/upload-document`) offers a
 * file and a display title and nothing else — no screen in this product lets a reviewer
 * name a section for a document, so every document this product has ever accepted is
 * unclassified at the storage layer that now exists to record one. `analysed` below still
 * means **"this is the section the analysis is built for"**, a rule about intake and not a
 * claim about membership: the `AR` restriction lives in the analysis prompt
 * (`src/auditmanager/analysis/text/prompt.py`) and in fixture names, not in what a document
 * is uploaded carrying. A screen built from this module still never claims a document
 * belongs to a section — that claim would now be checkable in principle, and is simply not
 * one this product's own flow ever makes true.
 *
 * Counting per section is no longer absent: `getDashboardSummary` counts published
 * documents, per section, including the unclassified bucket every product upload falls
 * into today. A section *picker* on the upload form — the only way a reviewer could change
 * that bucket — is a feature and remains out of scope (`D-107`).
 */

/** A section code, exactly as the legacy application spells it. Never shown to a user. */
export type ProjectSectionCode =
  | 'AR'
  | 'AI'
  | 'KM'
  | 'KJ'
  | 'OV'
  | 'EOM'
  | 'VK'
  | 'PT'
  | 'PB'
  | 'SS'
  | 'ITP'
  | 'GP'
  | 'TX'
  | 'POS';

export interface ProjectSection {
  /**
   * The machine value: the legacy code. It is carried in `data-section` so an instrument
   * can address a section without reading a label, and it never reaches the screen as
   * text — the reader gets the Cyrillic abbreviation and the name.
   */
  readonly code: ProjectSectionCode;
  /** The Cyrillic mark a designer writes on a title block: `АР`, `КЖ`, `ЭОМ`. */
  readonly abbr: string;
  /** The section's name in the words a reviewer uses. */
  readonly name: string;
  /**
   * Whether this programme's analysis is built for this section's text.
   *
   * True for exactly one section today. It is a statement about the analysis, not about
   * any file: see this module's header.
   */
  readonly analysed: boolean;
}

/** The section the analysis is written for, and the one the upload rule names. */
export const ANALYSED_SECTION_CODE: ProjectSectionCode = 'AR';

export const PROJECT_SECTIONS: readonly ProjectSection[] = [
  { code: 'AR', abbr: 'АР', name: 'Архитектурные решения', analysed: true },
  { code: 'AI', abbr: 'АИ', name: 'Интерьеры', analysed: false },
  { code: 'KM', abbr: 'КМ', name: 'Конструкции металлические', analysed: false },
  { code: 'KJ', abbr: 'КЖ', name: 'Конструкции железобетонные', analysed: false },
  { code: 'OV', abbr: 'ОВ', name: 'Отопление и вентиляция', analysed: false },
  { code: 'EOM', abbr: 'ЭОМ', name: 'Электрооборудование и электроосвещение', analysed: false },
  { code: 'VK', abbr: 'ВК', name: 'Водоснабжение и канализация', analysed: false },
  { code: 'PT', abbr: 'ПТ', name: 'Пожаротушение', analysed: false },
  { code: 'PB', abbr: 'ПБ', name: 'Пожарная безопасность', analysed: false },
  { code: 'SS', abbr: 'СС', name: 'Слаботочные системы', analysed: false },
  { code: 'ITP', abbr: 'ИТП', name: 'Индивидуальный тепловой пункт', analysed: false },
  { code: 'GP', abbr: 'ГП', name: 'Генеральный план', analysed: false },
  { code: 'TX', abbr: 'ТХ', name: 'Технологические решения', analysed: false },
  { code: 'POS', abbr: 'ПОС', name: 'Организация строительства', analysed: false },
];

/** The section carrying `code`, or `null` when nothing does. Never a silent default. */
export function findProjectSection(code: string): ProjectSection | null {
  return PROJECT_SECTIONS.find((section) => section.code === code) ?? null;
}

/**
 * How a section is titled on screen: the name, with the mark a designer would recognise.
 *
 * The legacy code is not part of it. A reviewer reads `АР`, not `AR`.
 */
export function projectSectionTitle(section: ProjectSection): string {
  return `${section.name} (${section.abbr})`;
}
