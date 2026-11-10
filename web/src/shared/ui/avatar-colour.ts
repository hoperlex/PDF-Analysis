/**
 * Which of the twelve avatar colours an account wears (`R-57`, `W50-PLAN.md` §3.5;
 * `AVATAR-PALETTE-01`).
 *
 * ## Keyed on the account's `user_uid`, never on the name or the e-mail
 *
 * The input is the account's `user_uid` — the identifier the API issues once, at creation,
 * and never changes: `Account.user_uid` in `GET /me` and in the user card, the session
 * subject's `userUid`. It is NOT the e-mail (`login`), which a profile change rewrites and
 * which an archived account hands back to whoever registers it next, and it is NOT the
 * display label or the initials. So a reviewer who corrects a misspelt surname, or changes
 * their address, keeps the colour their colleagues already know them by, and a new account
 * on a freed address starts with a colour of its own. The colour is computed whenever an
 * avatar is drawn and stored nowhere: no column, no migration, no contract field.
 *
 * ## No normalisation: the key is the uid exactly as the API wrote it
 *
 * Every caller reads the uid from an `Account` answer, so every caller holds the same
 * canonical string, and folding case or trimming would only hide a caller that did not. Two
 * strings that differ in any way are two keys. The one thing that is refused is a key with
 * nothing in it: an empty or blank uid is a broken promise upstream, and drawing a circle
 * from it would move the defect somewhere nobody looks (`AvatarColourKeyError`, the same
 * stance as `AvatarInitialsError` takes on empty initials, and `AGENTS.md` §4's ban on a
 * silent fallback).
 *
 * ## The hash
 *
 * 32-bit FNV-1a over the UTF-8 bytes of the key, unsigned, modulo the palette size. Stable
 * across sessions, browsers and the server render, needs no dependency, and spreads strings
 * that share a long prefix (every uid starts `usr_`) across the palette.
 * `web/tests/unit/ui/avatar.test.ts` holds every index reachable and the same key to the
 * same index; `web/tests/unit/styles/avatar-palette.test.ts` holds the palette size to the
 * number of colour pairs `globals.css` actually declares.
 */

/** The number of colour pairs in `globals.css`. The avatar palette test reads the stylesheet and holds this to it. */
export const AVATAR_PALETTE_SIZE = 12;

/** The colour key was empty or blank: the account's `user_uid` broke its promise upstream. */
export class AvatarColourKeyError extends Error {
  constructor() {
    super('Аватар: пустой ключ цвета. У учётной записи всегда есть идентификатор user_uid.');
    this.name = 'AvatarColourKeyError';
  }
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
 * @param colourKey the account's `user_uid`, verbatim — never its e-mail or its name.
 * @throws {AvatarColourKeyError} when the key is empty or only whitespace.
 */
export function avatarColourIndex(colourKey: string): number {
  if (colourKey.trim().length === 0) throw new AvatarColourKeyError();
  return fnv1a32(colourKey) % AVATAR_PALETTE_SIZE;
}

/** The two-digit pair number `globals.css` names a colour by: index 0 is pair `01`. */
export function avatarPairNumber(index: number): string {
  if (!Number.isInteger(index) || index < 0 || index >= AVATAR_PALETTE_SIZE) {
    throw new RangeError(`Аватар: номер цвета ${index} вне палитры из ${AVATAR_PALETTE_SIZE}.`);
  }
  return String(index + 1).padStart(2, '0');
}
