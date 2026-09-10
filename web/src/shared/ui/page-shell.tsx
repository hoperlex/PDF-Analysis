/**
 * The frame every PC-01 screen sits in: a title, an optional subtitle, an optional
 * action area and the body. Slices supply the body; they do not re-invent the frame.
 */

import type { ReactNode } from 'react';

export interface PageShellProps {
  readonly title: string;
  readonly subtitle?: ReactNode | undefined;
  /** Primary actions for this screen, rendered opposite the title. */
  readonly actions?: ReactNode | undefined;
  readonly children: ReactNode;
}

export function PageShell({ title, subtitle, actions, children }: PageShellProps) {
  return (
    <section className="am-page">
      <header className="am-page__header">
        <div>
          <h1 className="am-page__title">{title}</h1>
          {subtitle !== undefined ? <p className="am-page__subtitle">{subtitle}</p> : null}
        </div>
        {actions !== undefined ? <div className="am-page__actions">{actions}</div> : null}
      </header>
      <div className="am-page__body">{children}</div>
    </section>
  );
}
