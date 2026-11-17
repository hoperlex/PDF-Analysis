/**
 * The colour of a section: the one list that says which palette token a section wears
 * (`UIP-G-17`, `Г1-C`).
 *
 * **Where it lives.** The section catalogue (`./section`) is this slice's, so the answer to
 * "which colour is the vent section" is too. It is the lowest layer that both the application
 * frame's menu (`_app`) and the screens (`_pages`, `widgets`) may import, which is why it is
 * not in `shared` (a section is domain knowledge) and not in any one screen (the menu, the
 * section's heading, the sections table and the work schedule must agree on one colour per
 * section, and agreement is only checkable when the answer is stored once).
 *
 * **What it names.** The tokens `--am-section-01` ... `--am-section-15` of `globals.css`,
 * which hold the colours in both themes. Nothing here knows a hex value, so a theme or a
 * retuned palette costs no change in this file. `tests/unit/projects/section-colour.test.ts`
 * holds the list whole (every section has a token, every token exists in the stylesheet,
 * none is shared, none is left over) and `tests/unit/styles/section-palette.test.ts` holds
 * the colours themselves (contrast against the surfaces, distance between colours).
 *
 * **Why the numbers are not in catalogue order.** The tokens are numbered in hue order, and
 * the entries below are written in the order of the menu (`PROJECT_STRUCTURE_ORDER`): the
 * section at menu position `i`, counted from 0, wears token `(4 i mod 15) + 1`. A step of four
 * hues is about 80 degrees, so two sections next to each other in the menu never look alike,
 * and neither do two a place or two further apart.
 *
 * **«Без раздела».** A document with no confirmed section gets no section colour: it wears
 * the neutral token the stylesheet already has for inert things, and there is no sixteenth
 * colour. That case is stated by passing `null`, never by leaving a section out: a code this
 * catalogue does not know is a defect and throws, as `projectSectionOf` does.
 */

import type { CSSProperties } from 'react';

import type { ProjectSectionCode } from './section';
import { projectSectionOf } from './section';

type TokenNumber =
  | '01'
  | '02'
  | '03'
  | '04'
  | '05'
  | '06'
  | '07'
  | '08'
  | '09'
  | '10'
  | '11'
  | '12'
  | '13'
  | '14'
  | '15';

/** A custom property of the section palette, spelled as the stylesheet declares it. */
export type SectionColourToken = `--am-section-${TokenNumber}`;

/**
 * Section code to palette token. Total over the codes (a missing or an extra key stops this
 * object type-checking) and written in menu order, so the step reads straight off the page.
 */
export const SECTION_COLOUR_TOKENS: Readonly<Record<ProjectSectionCode, SectionColourToken>> = {
  AR: '--am-section-01',
  AI: '--am-section-05',
  PS: '--am-section-09',
  POS: '--am-section-13',
  TX: '--am-section-02',
  KJ: '--am-section-06',
  KM: '--am-section-10',
  OV: '--am-section-14',
  VK: '--am-section-03',
  PT: '--am-section-07',
  EOM: '--am-section-11',
  SS: '--am-section-15',
  ITP: '--am-section-04',
  GP: '--am-section-08',
  PB: '--am-section-12',
};

/** What a row without a section wears: an existing neutral token, not a sixteenth colour. */
const NO_SECTION_COLOUR = 'var(--am-inert)';

/** The custom property a dot reads, and a row that holds a dot may set for it. */
export const SECTION_COLOUR_PROPERTY = '--am-section-colour';

/** A style object that sets {@link SECTION_COLOUR_PROPERTY}; it can be passed as a `style`. */
export type SectionColourStyle = CSSProperties & { readonly '--am-section-colour': string };

/**
 * The colour of a section as a CSS value: the `var()` reference to its palette token, or the
 * neutral one for `null` («Без раздела»). A code outside the catalogue throws.
 */
export function sectionColourVar(code: ProjectSectionCode | null): string {
  if (code === null) return NO_SECTION_COLOUR;
  const section = projectSectionOf(code);
  return `var(${SECTION_COLOUR_TOKENS[section.code]})`;
}

/**
 * The style that gives an element (a dot, or a row whose dot reads it) its section's colour:
 * the custom property a CSS module reads, set to the section's token.
 */
export function sectionColourStyle(code: ProjectSectionCode | null): SectionColourStyle {
  return { [SECTION_COLOUR_PROPERTY]: sectionColourVar(code) } as SectionColourStyle;
}
