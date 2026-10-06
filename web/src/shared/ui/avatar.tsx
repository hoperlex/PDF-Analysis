/**
 * The generated avatar (`R-57`): the account's initials on a circle whose colour is hashed
 * from its e-mail. There is no upload in this programme.
 *
 * A server component with no state. It takes exactly two facts — the initials and the
 * colour key — and no session, no account and no query: `shared/ui` may not import
 * `entities/account`, and a primitive that read the session would be one only the frame
 * could use.
 *
 * ## What the caller passes
 *
 * - `initials`: the session subject's `initials`, which `W49` derives from the display label
 *   and which is never empty. An empty one is refused loudly (`AvatarInitialsError`) rather
 *   than drawn as a blank circle: a blank avatar is a broken promise upstream, and hiding it
 *   here would move the defect somewhere nobody looks.
 * - `colourKey`: the account's e-mail, the subject's `login`. See `avatar-colour.ts` for why
 *   it is the e-mail and never the name.
 * - `label`, optional: the accessible name. Leave it out where a visible name sits beside the
 *   circle — the account menu's header, a trigger with its own label — and the circle is
 *   `aria-hidden`, so a screen reader does not read the letters as a word. Pass it where the
 *   circle stands alone, and it is an image with that name.
 *
 * The colour is a modifier class and never an inline style: the stylesheet rule for each pair
 * reads that pair's two tokens, so the contrast census and the dedicated palette test both
 * see what a browser paints.
 */

import { avatarColourIndex, avatarPairNumber } from './avatar-colour';

/** The initials were empty: the account's display label broke its promise upstream. */
export class AvatarInitialsError extends Error {
  constructor() {
    super('Аватар: пустые инициалы. Подпись учётной записи не может быть пустой.');
    this.name = 'AvatarInitialsError';
  }
}

export interface AvatarProps {
  /** The subject's `initials`, derived from its display label. Never empty. */
  readonly initials: string;
  /** The account's e-mail (the subject's `login`). Never its name: a corrected name keeps its colour. */
  readonly colourKey: string;
  /** The accessible name, where no visible name sits beside the circle. Omitted: `aria-hidden`. */
  readonly label?: string | undefined;
}

export function Avatar({ initials, colourKey, label }: AvatarProps) {
  const letters = initials.trim();
  if (letters.length === 0) throw new AvatarInitialsError();
  const pair = avatarPairNumber(avatarColourIndex(colourKey));
  const className = `am-avatar am-avatar--${pair}`;
  if (label === undefined) {
    return (
      <span className={className} data-avatar-pair={pair} aria-hidden="true">
        {letters}
      </span>
    );
  }
  return (
    <span className={className} data-avatar-pair={pair} role="img" aria-label={label}>
      {letters}
    </span>
  );
}
