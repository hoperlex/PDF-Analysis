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
 * **What a section is here, and what it is emphatically not.** It is *navigation*, and
 * the structure `R-18`'s stub rule asks an alpha to carry. It is not a property of a
 * document and it is not a filter:
 *
 *   - the contract has no section field anywhere — `Project` is `project_uid`, `name`,
 *     `created_at`, `document_count`, and `UploadDocumentRequest` is `file` and
 *     `display_title` (`D-56` verified this against `contracts/api/v1/openapi.json`);
 *   - nothing in the pipeline checks a document's section. The `AR` restriction lives in
 *     the analysis prompt (`src/auditmanager/analysis/text/prompt.py`) and in fixture
 *     names, while the upload envelope checks the media type, the byte size, the page
 *     count and the text layer — and none of those is a section.
 *
 * So `analysed` below means **"this is the section the analysis is built for"**, which is
 * a rule about what is worth submitting. It never means "this document belongs to that
 * section": no code in this repository can establish that, and a screen that said so
 * would be asserting something the software cannot confirm. Every sentence rendered from
 * this module is written to that distinction.
 *
 * Counting anything per section — a verdict total, a document total — is the other half
 * of `D-56` and is deliberately absent: it needs a contract field, a reseal and a
 * migration, and none of them belongs to a frontend wave.
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
