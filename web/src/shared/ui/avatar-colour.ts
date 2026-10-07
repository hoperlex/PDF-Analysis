/**
 * Which of the fourteen avatar colours an account wears (`R-57`, `W50-PLAN.md` §3.5).
 *
 * ## Keyed on the e-mail, never on the name
 *
 * The input is the account's e-mail — the session subject's `login`, which every account
 * carries from its first sign-in after the identity upgrade (`R-59`). It is NOT the display
 * label and NOT the initials: a reviewer who corrects a misspelt surname keeps the colour
 * their colleagues already know them by. A legacy login that is not an address yet (the
 * seeded `admin` before its first sign-in) is hashed the same way, and so is an empty
 * string; both give a valid index, because a hash input is never a reason to render
 * nothing.
 *
 * ## Normalised the way the access boundary normalises it
 *
 * The boundary folds a login to lower case and stores the folded value, so `Petrova@…` and
 * `petrova@…` are one account and must be one colour. Surrounding whitespace is not part of
 * an address either. Nothing else is folded: two addresses that differ in any other way are
 * two accounts.
 *
 * ## The hash
 *
 * 32-bit FNV-1a over the UTF-8 bytes of the normalised key, unsigned, modulo the palette
 * size. Stable across sessions, browsers and the server render, needs no dependency, and
 * spreads short similar strings (`expert-1@…`, `expert-2@…`) across the palette.
 * `web/tests/unit/ui/avatar.test.ts` holds every index reachable and the same key to the
 * same index; `web/tests/unit/styles/avatar-palette.test.ts` holds the palette size to the
 * number of colour pairs `globals.css` actually declares.
 */

/** The number of colour pairs in `globals.css`. The avatar palette test reads the stylesheet and holds this to it. */
export const AVATAR_PALETTE_SIZE = 14;

/** The key the hash reads: trimmed and lower-cased, as the access boundary stores a login. */
export function normaliseColourKey(colourKey: string): string {
  return colourKey.trim().toLowerCase();
}

const FNV_OFFSET_BASIS = 0x811c9dc5;
const FNV_PRIME = 0x01000193;

/** 32-bit FNV-1a of the UTF-8 bytes of `text`, as an unsigned integer. */
function fnv1a32(text: string): number {
  let hash = FNV_OFFSET_BASIS;
  for (const byte of new TextEncoder().encode(text)) {
    hash ^= byte;
    hash = Math.imul(hash, FNV_PRIME);
  }
  return hash >>> 0;
}

/**
 * The zero-based colour index for an account, in `[0, AVATAR_PALETTE_SIZE)`.
 *
 * @param colourKey the account's e-mail (the session subject's `login`) — never its name.
 */
export function avatarColourIndex(colourKey: string): number {
  return fnv1a32(normaliseColourKey(colourKey)) % AVATAR_PALETTE_SIZE;
}

/** The two-digit pair number `globals.css` names a colour by: index 0 is pair `01`. */
export function avatarPairNumber(index: number): string {
  if (!Number.isInteger(index) || index < 0 || index >= AVATAR_PALETTE_SIZE) {
    throw new RangeError(`Аватар: номер цвета ${index} вне палитры из ${AVATAR_PALETTE_SIZE}.`);
  }
  return String(index + 1).padStart(2, '0');
}
