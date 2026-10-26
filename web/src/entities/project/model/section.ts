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
 * **History: `W46-WIRE` (`F-3`).** A reseal landed after this
 * module was first written and made two of its claims false: `document.section` is now a
 * real, stored, checked field (a document's version carries an optional `section`, and the
 * upload refuses a malformed one with a `422`), and the dashboard now counts published
 * documents per section, server-side (`getDashboardSummary`'s `section_breakdown`,
 * `widgets/dashboard`). Neither earlier claim survives as it was written:
 *
 *   - it is **not true** any more that "the contract has no section field anywhere" —
 *     it does, and it round-trips;
 *   - it is **not true** any more that "nothing checks a document's section" — the
 *     `422 validation_failed` on an unrecognised or blank value is exactly a check.
 *
 * **What a section is here now (`WEB-SECTION-COPY-01`).** A section is the value an expert
 * confirmed for a document's current version, on the version screen (`W59-SECTION-UI-01`,
 * `classifyDocumentVersion`). The product's upload form still names no section and needs none,
 * so a freshly uploaded document is unclassified only until an expert confirms it. The
 * dashboard counts documents by that confirmation, and a document whose current version is not
 * confirmed stands in its row «Без раздела». The earlier statements that a section "reads as
 * navigation" and that every document the product accepts is unclassified do not survive
 * `W59-SECTION-UI-01`.
 *
 * **`W59-SECTION-SEAL-01`: fifteen, not fourteen.** The contract's `ProjectSection` gained
 * `PS` (the explanatory note, «Пояснительная записка»), distinct from `PB` (fire safety).
 * Legacy's fourteen keep their order and `PS` follows them, exactly as the backend's
 * `dashboard.repository.PROJECT_SECTIONS` does. A version also carries an expert-confirmed
 * `classification` (stage and section) that run start routes on.
 *
 * **How a section is analysed ({@link SectionAnalysis}).** Every one of the fifteen sections
 * has an analysis, by one of two routes. Fourteen are analysed by the text profile the server
 * registers for the section (`W59-SECTION-SEAL-01`: one package per code under
 * `src/auditmanager/analysis/text/profiles/`, every code but АР). АР has no text profile and is
 * analysed by the group of six AR v3 checks (`PROD-11-AR-V1-V2-REMOVAL-01`, `ADR-0024`); the
 * server refuses an ordinary run for it. `analysedBy` records the route and nothing more:
 * whether a particular version can start a run now is the API's answer
 * (`SectionReviewOption.executable`, and for АР the status of the checked pack), not this
 * registry's. A unit test holds the fourteen to the packages on disk.
 *
 * **`W59-SECTION-UI-01`: names and order are the owner's, not this module's.** The names are
 * the legacy ones the owner chose in poll answer `S-3` and that the backend's suggestion
 * catalogue carries (`src/auditmanager/sections/suggestion_patterns.json`); a unit test reads
 * that file and holds every name here to it. {@link PROJECT_SECTIONS} keeps legacy's order,
 * because the dashboard's breakdown is keyed on it. The project structure — a project's
 * documents grouped by the section an expert confirmed for their current version — follows
 * the order of poll answer `S-5` instead: АР, then the cheap profiles first
 * ({@link PROJECT_STRUCTURE_ORDER}).
 */

import type { ProjectSection as ContractProjectSection } from '@/shared/api';

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
  | 'POS'
  | 'PS';

/**
 * The route that analyses a section: the section's own text profile (fourteen sections), or the
 * group of six AR v3 checks (АР only). See this module's header. A machine value, never shown.
 */
export type SectionAnalysis = 'text_profile' | 'six_run_group';

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
   * The route that analyses this section (see this module's header): its own text profile, or,
   * for АР only, the group of six AR v3 checks. A statement about the analysis, not about any
   * file or any version. It is never shown as a code; the dashboard carries it in
   * `data-analysed-by` so an instrument can address it.
   */
  readonly analysedBy: SectionAnalysis;
}

/**
 * The section a section picker starts on: the first of the catalogue, АР. It is a default
 * choice and not a statement that only this section is analysed (every section is, see
 * {@link ProjectSection.analysedBy}). The name is kept because `widgets/section-specification`
 * imports it.
 */
export const ANALYSED_SECTION_CODE: ProjectSectionCode = 'AR';

export const PROJECT_SECTIONS: readonly ProjectSection[] = [
  { code: 'AR', abbr: 'АР', name: 'Архитектурные решения', analysedBy: 'six_run_group' },
  { code: 'AI', abbr: 'АИ', name: 'Архитектурные решения (интерьер)', analysedBy: 'text_profile' },
  { code: 'KM', abbr: 'КМ', name: 'Конструкции металлические', analysedBy: 'text_profile' },
  { code: 'KJ', abbr: 'КЖ', name: 'Конструкции железобетонные', analysedBy: 'text_profile' },
  { code: 'OV', abbr: 'ОВ', name: 'Отопление, вентиляция и кондиционирование', analysedBy: 'text_profile' },
  { code: 'EOM', abbr: 'ЭОМ', name: 'Электроснабжение и электрооборудование', analysedBy: 'text_profile' },
  { code: 'VK', abbr: 'ВК', name: 'Водоснабжение и канализация', analysedBy: 'text_profile' },
  { code: 'PT', abbr: 'ПТ', name: 'Противопожарный водопровод', analysedBy: 'text_profile' },
  { code: 'PB', abbr: 'ПБ', name: 'Пожарная безопасность', analysedBy: 'text_profile' },
  { code: 'SS', abbr: 'СС', name: 'Слаботочные системы', analysedBy: 'text_profile' },
  { code: 'ITP', abbr: 'ИТП', name: 'Индивидуальный тепловой пункт', analysedBy: 'text_profile' },
  { code: 'GP', abbr: 'ГП', name: 'Генеральный план', analysedBy: 'text_profile' },
  { code: 'TX', abbr: 'ТХ', name: 'Технологические решения', analysedBy: 'text_profile' },
  { code: 'POS', abbr: 'ПОС', name: 'Проект организации строительства', analysedBy: 'text_profile' },
  { code: 'PS', abbr: 'ПЗ', name: 'Пояснительная записка', analysedBy: 'text_profile' },
];

/**
 * Compile-time proof that this module's codes are exactly the contract's fifteen: a code the
 * contract gains or drops stops this line type-checking in either direction.
 */
type SameSet<A, B> = [A] extends [B] ? ([B] extends [A] ? true : false) : false;
const _sectionCodesAreTheContracts: SameSet<ProjectSectionCode, ContractProjectSection> = true;
void _sectionCodesAreTheContracts;

/**
 * The order of the project structure: poll answer `S-5`, «cheap first» after АР —
 * АИ → ПЗ, ПОС, ТХ → КЖ, КМ → ОВ, ВК, ПТ → ЭОМ, СС, ИТП → ГП → ПБ.
 */
export const PROJECT_STRUCTURE_ORDER: readonly ProjectSectionCode[] = [
  'AR',
  'AI',
  'PS',
  'POS',
  'TX',
  'KJ',
  'KM',
  'OV',
  'VK',
  'PT',
  'EOM',
  'SS',
  'ITP',
  'GP',
  'PB',
];

/** The section carrying `code`, or `null` when nothing does. Never a silent default. */
export function findProjectSection(code: string): ProjectSection | null {
  return PROJECT_SECTIONS.find((section) => section.code === code) ?? null;
}

/** A code outside this module's fifteen. A defect in this build, never a label to guess. */
export class UnknownProjectSectionError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(`Раздел проекта: код ${code} вне каталога этой версии приложения.`);
    this.name = 'UnknownProjectSectionError';
    this.code = code;
  }
}

/**
 * The section carrying a contract code. Total over the type, and a unit test proves every
 * one of the fifteen resolves; a code outside them throws rather than rendering a guess.
 */
export function projectSectionOf(code: ProjectSectionCode): ProjectSection {
  const section = findProjectSection(code);
  if (section === null) throw new UnknownProjectSectionError(code);
  return section;
}

/** The fifteen sections in the project structure's order (`S-5`). */
export function sectionsInStructureOrder(): readonly ProjectSection[] {
  return PROJECT_STRUCTURE_ORDER.map(projectSectionOf);
}

/** A code's position in the project structure's order (`S-5`), for sorting. */
export function structureRank(code: ProjectSectionCode): number {
  return PROJECT_STRUCTURE_ORDER.indexOf(code);
}

/**
 * How a section is titled on screen: the name, with the mark a designer would recognise.
 *
 * The legacy code is not part of it. A reviewer reads `АР`, not `AR`.
 */
export function projectSectionTitle(section: ProjectSection): string {
  return `${section.name} (${section.abbr})`;
}
