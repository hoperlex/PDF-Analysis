'use client';

/**
 * `Disclosure` — a navigation group: a real `<button>` that shows and hides a list of links
 * (the WAI-ARIA disclosure pattern; `disclosure-state.ts` says why it is not a menu).
 *
 * Two layers, so both can be tested without a DOM:
 *
 * - `DisclosureView` is pure markup from props and an `open` flag. The contrast census
 *   renders it closed and open (`web/tests/unit/styles/screens.ts`), and the unit tests read
 *   the attributes the pattern requires off it.
 * - `Disclosure` is the client island the frame uses: it holds `open`, turns browser events
 *   into `disclosureTransition` calls and applies the answer. It renders exactly the view,
 *   and its server render is the view's closed state — a unit test holds the two equal.
 *
 * The panel is always in the markup and `hidden` while closed, so `aria-controls` always
 * names an element that exists. Closed is the default.
 *
 * It takes labels and links, never a session or a registry row: which groups a role sees,
 * which item is current, and the addresses themselves are `W50-SHELL-FRAME`'s to decide.
 */

import Link from 'next/link';
import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent, MouseEvent, ReactNode, Ref } from 'react';

import type { DisclosureTransition } from './disclosure-state';
import { disclosureTransition } from './disclosure-state';

export interface DisclosureLink {
  readonly href: string;
  readonly label: string;
  /** The link to the page being shown: it carries `aria-current="page"`. */
  readonly current?: boolean | undefined;
}

interface DisclosureCommonProps {
  /** The button's text: the group's name. */
  readonly label: string;
  /** The group holds the current page: the button carries `aria-current="true"`. */
  readonly current?: boolean | undefined;
  /**
   * `popover` (the default) floats the panel over the page under the button — a group in the
   * bar. `inline` opens it in the flow — a group inside the stacked menu.
   */
  readonly layout?: 'popover' | 'inline' | undefined;
  /** `end` anchors a popover to the button's right edge, for a group at the right of the bar. */
  readonly align?: 'start' | 'end' | undefined;
}

/**
 * Either a list of links — a navigation group — or arbitrary content, which is how the stacked
 * menu holds the groups themselves as inline disclosures. Never both.
 */
export type DisclosureProps = DisclosureCommonProps &
  (
    | { readonly links: readonly DisclosureLink[]; readonly children?: undefined }
    | { readonly children: ReactNode; readonly links?: undefined }
  );

/** What the island attaches to the view. A static render passes none. */
export interface DisclosureBindings {
  readonly rootRef?: Ref<HTMLDivElement> | undefined;
  readonly buttonRef?: Ref<HTMLButtonElement> | undefined;
  readonly onToggle?: (() => void) | undefined;
  readonly onKeyDown?: ((event: KeyboardEvent<HTMLDivElement>) => void) | undefined;
  readonly onPanelClick?: ((event: MouseEvent<HTMLDivElement>) => void) | undefined;
}

export type DisclosureViewProps = DisclosureProps & {
  readonly open: boolean;
  /** The panel's `id`, which the button's `aria-controls` names. */
  readonly panelId: string;
  readonly bindings?: DisclosureBindings | undefined;
};

export function DisclosureView(props: DisclosureViewProps) {
  const { label, current, layout, align, open, panelId, bindings } = props;
  const rootClass = [
    'am-disclosure',
    layout === 'inline' ? 'am-disclosure--inline' : null,
    align === 'end' ? 'am-disclosure--end' : null,
  ]
    .filter((name) => name !== null)
    .join(' ');

  return (
    <div className={rootClass} ref={bindings?.rootRef} onKeyDown={bindings?.onKeyDown}>
      <button
        type="button"
        className="am-disclosure__button"
        ref={bindings?.buttonRef}
        aria-expanded={open}
        aria-controls={panelId}
        aria-current={current === true ? 'true' : undefined}
        onClick={bindings?.onToggle}
      >
        {label}
      </button>
      <div
        className="am-disclosure__panel"
        id={panelId}
        hidden={!open}
        onClick={bindings?.onPanelClick}
      >
        {props.links !== undefined ? (
          <ul className="am-disclosure__list">
            {props.links.map((link) => (
              <li className="am-disclosure__item" key={link.href}>
                <Link
                  className="am-disclosure__link"
                  href={link.href}
                  aria-current={link.current === true ? 'page' : undefined}
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          props.children
        )}
      </div>
    </div>
  );
}

export function Disclosure(props: DisclosureProps) {
  const panelId = `${useId()}panel`;
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const apply = (
    transition: DisclosureTransition,
    native?: { preventDefault(): void; stopPropagation(): void },
  ): void => {
    if (transition.handled && native !== undefined) {
      native.preventDefault();
      native.stopPropagation();
    }
    setOpen(transition.open);
    if (transition.focus === 'button') buttonRef.current?.focus();
  };

  // While open, a pointer pressed or focus arriving anywhere outside closes it.
  useEffect(() => {
    if (!open) return undefined;
    const onOutside = (event: Event): void => {
      const root = rootRef.current;
      if (root !== null && event.target instanceof Node && !root.contains(event.target)) {
        setOpen(disclosureTransition(true, { type: 'outside' }).open);
      }
    };
    document.addEventListener('pointerdown', onOutside);
    document.addEventListener('focusin', onOutside);
    return () => {
      document.removeEventListener('pointerdown', onOutside);
      document.removeEventListener('focusin', onOutside);
    };
  }, [open]);

  return (
    <DisclosureView
      {...props}
      open={open}
      panelId={panelId}
      bindings={{
        rootRef,
        buttonRef,
        onToggle: () => apply(disclosureTransition(open, { type: 'toggle' })),
        onKeyDown: (event) => apply(disclosureTransition(open, { type: 'key', key: event.key }), event),
        onPanelClick: (event) => {
          if (event.target instanceof Element && event.target.closest('a') !== null) {
            apply(disclosureTransition(open, { type: 'navigate' }));
          }
        },
      }}
    />
  );
}
