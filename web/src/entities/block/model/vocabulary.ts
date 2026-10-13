/**
 * What each value a portal block carries means, in Russian (`W55B-WEB-BLOCKS`).
 *
 * `R-18`: everything a reviewer reads is Russian, and the machine value keeps its home in a
 * `data-` attribute. Two of the vocabularies here are CLOSED (`PortalBlockType`,
 * `PortalGeometryState`: the contract enumerates them, so the tables are `Record`s and a
 * reseal that adds a member stops this file type-checking). Two are OPEN strings on the
 * wire: the portal's own `status` token and the quality `flags` of the recognised text. An
 * open vocabulary gets a neutral Russian sentence for a value this screen does not know,
 * never the raw token: an unknown token printed as a sentence is English on a Russian
 * screen, and a silently dropped one is a flag nobody sees. The raw value stays in the
 * `data-` attribute beside the sentence, where an operator can still read it.
 *
 * Every sentence restates what the producing module says the value means
 * (`src/auditmanager/analysis/recognised/flags.py` for the flags; the contract's
 * `PortalBlock` and `PortalGeometryState` descriptions for the rest) and adds no cause.
 */

import type { PortalBlockType, PortalGeometryState } from '@/shared/api';

/** The portal's three block types, as a heading on each block. */
export const PORTAL_BLOCK_TYPE_LABELS: Readonly<Record<PortalBlockType, string>> = {
  text: 'Текст',
  image: 'Изображение',
  stamp: 'Штамп',
};

/** A type the contract does not declare (a server that broke the contract), named neutrally. */
export const UNKNOWN_BLOCK_TYPE_LABEL = 'Блок неизвестного типа';

export function portalBlockTypeLabel(type: string): string {
  return (PORTAL_BLOCK_TYPE_LABELS as Readonly<Record<string, string>>)[type] ?? UNKNOWN_BLOCK_TYPE_LABEL;
}

/** How a block's portal `status` reads, and which badge tone carries it. */
export interface PortalStatusPresentation {
  readonly label: string;
  readonly tone: 'ok' | 'failed' | 'inert';
}

/**
 * The portal's own recognition status of a block. An OPEN lowercase token on the wire: the
 * two the portal is known to send are named; anything else is said to be unknown.
 */
const PORTAL_STATUS: Readonly<Record<string, PortalStatusPresentation>> = {
  recognized: { label: 'распознан порталом', tone: 'ok' },
  failed: { label: 'сбой распознавания портала', tone: 'failed' },
};

export const UNKNOWN_PORTAL_STATUS: PortalStatusPresentation = {
  label: 'состояние у портала неизвестно этому экрану',
  tone: 'inert',
};

export function portalStatusPresentation(status: string): PortalStatusPresentation {
  return Object.hasOwn(PORTAL_STATUS, status) ? (PORTAL_STATUS[status] as PortalStatusPresentation) : UNKNOWN_PORTAL_STATUS;
}

/**
 * The page-box check, said only when it failed. `ok` carries no sentence: the crop (or, for
 * a text block, nothing at all) is what an agreeing page looks like, and a badge on every
 * block saying so would bury the one that matters.
 */
export const GEOMETRY_MISMATCH_LABEL = 'страница не совпала с PDF — фрагмент не вырезан';

export function geometryLabel(geometry: PortalGeometryState): string | null {
  return geometry === 'geometry_mismatch' ? GEOMETRY_MISMATCH_LABEL : null;
}

/** One quality flag of a recognised text: a short name and a plain sentence. */
export interface FlagPresentation {
  readonly label: string;
  readonly explanation: string;
}

/**
 * The flag vocabulary `analysis/recognised/flags.py` emits today, in its own order. Open:
 * a flag the backend adds later gets {@link UNKNOWN_FLAG} until somebody words it here.
 */
export const RECOGNISED_FLAGS: Readonly<Record<string, FlagPresentation>> = {
  mixed_script: {
    label: 'смешение кириллицы и латиницы',
    explanation: 'В одном слове стоят и кириллические, и латинские буквы.',
  },
  homoglyph: {
    label: 'латинская буква вместо кириллической',
    explanation:
      'Буква, похожая на букву другого алфавита, стоит там, где по соседним словам ждали бы кириллицу (или наоборот).',
  },
  cjk: {
    label: 'иероглифы',
    explanation: 'В тексте встретились иероглифы, кана или хангыль.',
  },
  doubled_list_marker: {
    label: 'повторяющийся маркер списка',
    explanation: 'Строка начинается двумя одинаковыми маркерами списка подряд, например «- -» или «1. 1.».',
  },
  degenerate_instruction_echo: {
    label: 'модель повторила свою инструкцию',
    explanation: 'Вместо текста страницы в блоке слова из инструкции модели распознавания.',
  },
  degenerate_first_person_plan: {
    label: 'модель рассуждает вместо распознавания',
    explanation: 'Вместо текста страницы модель от первого лица описала, что собирается сделать.',
  },
  degenerate_page_narration: {
    label: 'модель пересказывает страницу',
    explanation: 'Вместо распознанного текста модель рассказала, что видно на странице.',
  },
  degenerate_serialised_payload: {
    label: 'служебные данные вместо текста',
    explanation: 'Вместо текста страницы в блоке оказалась служебная структура данных.',
  },
  empty_text: {
    label: 'пустой текст',
    explanation: 'Портал не распознал в этом блоке ни одного знака.',
  },
};

export const UNKNOWN_FLAG: FlagPresentation = {
  label: 'другой признак качества',
  explanation: 'Этот признак экрану не знаком. Сверьте распознанный текст с PDF.',
};

export function flagPresentation(flag: string): FlagPresentation {
  return Object.hasOwn(RECOGNISED_FLAGS, flag) ? (RECOGNISED_FLAGS[flag] as FlagPresentation) : UNKNOWN_FLAG;
}

/** The marker every recognised text carries (`R-116`: OCR is always marked). */
export const RECOGNISED_MARKER = 'распознано';

/** The marker every portal description carries; the plan fixes the wording (`R-117`). */
export const DESCRIPTION_MARKER = 'описание портала — в анализе не используется';
