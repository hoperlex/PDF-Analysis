/**
 * The icon set.
 *
 * ## Where the geometry comes from, and why that is the whole design
 *
 * `D-52` settled the provenance question before this file existed: the legacy reference
 * interface carries 43 inline `<svg>`, 28 of them at `viewBox="0 0 24 24"` with
 * `stroke-width="2"`, round caps and `currentColor`, and the `dollar-sign` path there is
 * **byte-identical** to Feather's. So a 24x24 icon in this programme is a **copy** of an
 * MIT-licensed work, not a drawing, and the obligation that follows is a notice, not a
 * design budget. Every path below was fetched from `feathericons/feather` and pasted; not
 * one was recalled, approximated or redrawn. `FEATHER_SOURCE` records which Feather file
 * each name came from, `web/NOTICE` carries the licence and the same table, and
 * `tests/unit/icon-convention.test.ts` fails if the two disagree.
 *
 * If a later session needs an icon Feather does not have, it draws it, changes
 * `FEATHER_SOURCE`'s type to admit an icon of our own, and says so in `NOTICE`. Claiming
 * a drawn icon is Feather's, or guessing at a path from memory, is the one thing this
 * file is arranged to make hard.
 *
 * ## The convention
 *
 * `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `stroke-width="2"`,
 * round caps and joins -- Feather's own attribute set, applied once on the `<svg>` so no
 * child element carries presentation of its own.
 *
 * **Colour is never written here.** It is inherited through `currentColor`, which is what
 * lets one icon read correctly on a button, in a badge and inside an error panel without
 * a variant per tone, and what keeps the set working when a theme changes `color`. A
 * hex literal anywhere in this file is a defect, and the convention test is what says so.
 *
 * **Size comes from outside.** The default is `1em`, so an icon placed in a line of text
 * takes the size of that text; a caller that wants a fixed size passes one.
 *
 * ## Accessibility
 *
 * An icon is decorative by default and renders `aria-hidden="true"`: beside a label it
 * has nothing of its own to say, and a screen reader announcing it twice is worse than
 * silence. An icon that stands alone -- an icon-only button -- takes `label`, and that
 * label is the user's text, so it is Russian like every other string a user reads.
 *
 * This file wires no icon to any screen. It is a set and its public API; the screens are
 * other owners' and they choose where an icon belongs.
 */

import type { ReactNode } from 'react';

/** Every icon this application has. Names are machine values and stay Latin. */
export type IconName =
  | 'project'
  | 'document'
  | 'version'
  | 'run'
  | 'finding'
  | 'review'
  | 'export'
  | 'upload'
  | 'accept'
  | 'reject'
  | 'comment'
  | 'back'
  | 'arrow'
  | 'warning'
  | 'error'
  | 'success';

/**
 * The Feather file each name was copied from.
 *
 * A `Record<IconName, string>` rather than an optional field, because today **every**
 * icon in the set is Feather's and the type should say so. An icon of our own is a type
 * change here plus a `NOTICE` entry, and that is deliberately visible.
 */
export const FEATHER_SOURCE: Readonly<Record<IconName, string>> = {
  project: 'folder',
  document: 'file-text',
  version: 'layers',
  run: 'play-circle',
  finding: 'flag',
  review: 'search',
  export: 'download',
  upload: 'upload',
  accept: 'check',
  reject: 'x',
  comment: 'message-square',
  back: 'arrow-left',
  arrow: 'arrow-right',
  warning: 'alert-triangle',
  error: 'alert-circle',
  success: 'check-circle',
};

/** The set, in a fixed order, for tests and for anything that enumerates it. */
export const ICON_NAMES: readonly IconName[] = Object.keys(FEATHER_SOURCE) as IconName[];

/**
 * The geometry, pasted from Feather.
 *
 * No element here carries `fill`, `stroke` or a width: the `<svg>` sets all three once.
 * Feather's own files put those attributes on the root for the same reason.
 */
const GEOMETRY: Readonly<Record<IconName, ReactNode>> = {
  project: <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />,
  document: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </>
  ),
  version: (
    <>
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </>
  ),
  run: (
    <>
      <circle cx="12" cy="12" r="10" />
      <polygon points="10 8 16 12 10 16 10 8" />
    </>
  ),
  finding: (
    <>
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <line x1="4" y1="22" x2="4" y2="15" />
    </>
  ),
  review: (
    <>
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </>
  ),
  export: (
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </>
  ),
  upload: (
    <>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </>
  ),
  accept: <polyline points="20 6 9 17 4 12" />,
  reject: (
    <>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </>
  ),
  comment: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
  back: (
    <>
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </>
  ),
  arrow: (
    <>
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </>
  ),
  warning: (
    <>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </>
  ),
  error: (
    <>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </>
  ),
  success: (
    <>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </>
  ),
};

export interface IconProps {
  readonly name: IconName;
  /**
   * Edge length, as any CSS length or a number of pixels. Defaults to `1em`, so an icon
   * next to text is the size of that text and a caller that sets nothing still gets a
   * sensible icon.
   */
  readonly size?: number | string | undefined;
  /**
   * The accessible name, in Russian, for an icon that stands alone. Omit it wherever a
   * visible label already says the same thing: the icon then renders `aria-hidden`.
   */
  readonly label?: string | undefined;
  readonly className?: string | undefined;
}

export function Icon({ name, size = '1em', label, className }: IconProps) {
  const decorative = label === undefined;
  return (
    <svg
      // The machine value stays an attribute. A label is the caller's Russian text; this
      // is what a test or a browser scenario selects on, and it is never translated.
      data-icon={name}
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      // Decorative or not, an icon is never a tab stop.
      focusable="false"
      aria-hidden={decorative ? true : undefined}
      role={decorative ? undefined : 'img'}
      aria-label={label}
    >
      {GEOMETRY[name]}
    </svg>
  );
}
