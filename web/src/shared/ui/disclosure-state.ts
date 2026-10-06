/**
 * The open/close logic of `Disclosure`, as one pure function.
 *
 * The client island in `disclosure.tsx` owns no rule of its own: it turns a browser event
 * into a `DisclosureEvent`, asks `disclosureTransition` what follows, and applies the answer —
 * the new open state, where focus goes, and whether the event stops here. Keeping the rules
 * here is what lets the node test environment, which has no DOM, drive every one of them
 * (`web/tests/unit/ui/disclosure.test.ts`).
 *
 * ## The pattern, and why it is not a menu
 *
 * The WAI-ARIA Authoring Practices *disclosure* pattern: a `<button aria-expanded
 * aria-controls>` that shows and hides a region. The navigation groups hold LINKS, and a
 * link inside `role="menu"` stops being a link to assistive technology — it loses the
 * link list, the "visited" state and the expectation that Tab moves through it. So the
 * group is a disclosure, and the arrow keys are deliberately not taken over.
 *
 * ## What closes it
 *
 * - the button again (Enter and Space reach a `<button>` as a click, natively);
 * - Escape, from the button or from inside the panel, which also returns focus to the
 *   button — the keyboard user is put back where they opened it;
 * - a pointer pressed, or focus arriving, anywhere outside the disclosure;
 * - following a link inside it — the frame survives a client-side navigation, so a panel
 *   left open would sit over the next page.
 *
 * ## Nesting
 *
 * The stacked «Меню» holds disclosures inside a disclosure. Escape closes the innermost
 * OPEN one and is consumed there (`handled`), so one press closes one level; a press inside
 * a closed inner group is not consumed and reaches the enclosing one.
 */

import { assertNever } from '@/shared/lib';

export type DisclosureEvent =
  /** The button was activated: a click, or Enter/Space, which a `<button>` turns into one. */
  | { readonly type: 'toggle' }
  /** A key went down on the button or anywhere inside the panel. */
  | { readonly type: 'key'; readonly key: string }
  /** A pointer went down, or focus arrived, outside the disclosure. */
  | { readonly type: 'outside' }
  /** A link inside the panel was followed. */
  | { readonly type: 'navigate' };

/** Where focus goes after the event: back to the disclosure's button, or nowhere new. */
export type DisclosureFocus = 'button' | null;

export interface DisclosureTransition {
  readonly open: boolean;
  readonly focus: DisclosureFocus;
  /**
   * The event was consumed here. The island calls `preventDefault` and `stopPropagation`, so
   * an enclosing disclosure does not act on the same key press.
   */
  readonly handled: boolean;
}

export function disclosureTransition(open: boolean, event: DisclosureEvent): DisclosureTransition {
  switch (event.type) {
    case 'toggle':
      return { open: !open, focus: null, handled: false };
    case 'key':
      if (event.key === 'Escape' && open) return { open: false, focus: 'button', handled: true };
      return { open, focus: null, handled: false };
    case 'outside':
    case 'navigate':
      return { open: false, focus: null, handled: false };
    default:
      return assertNever(event, 'disclosureTransition');
  }
}
