/**
 * The shell's stand-in for a screen whose slice has not landed.
 *
 * `web/src/app/**` has exactly one writer — the toolchain owner — so the four PC-01
 * routes exist from Gate A, before the `_pages` slices `B7` and `B8` own exist. A route
 * cannot import a module that is not there yet, so until the slice lands it renders this,
 * which says out loud which module the route is waiting for and what the one-line change
 * is.
 *
 * This is not a loading state and not an error state. Nothing was requested and nothing
 * failed: the screen has not been written. Rendering `LoadingState` here would be a lie
 * that never resolves.
 */

import { PageShell } from './page-shell';

export interface RoutePlaceholderProps {
  /** The screen's name, as the seam document calls it. */
  readonly screen: string;
  /** The route URL this file serves. */
  readonly route: string;
  /** The `_pages` module that will replace this, e.g. `@/_pages/projects`. */
  readonly awaitingModule: string;
  /** The Gate B session that owns that module. */
  readonly owner: string;
}

export function RoutePlaceholder({ screen, route, awaitingModule, owner }: RoutePlaceholderProps) {
  return (
    <PageShell
      title={screen}
      subtitle={
        <>
          Route <code>{route}</code> — shell only.
        </>
      }
    >
      <div className="am-state am-state--neutral" role="status">
        <p className="am-state__title">This screen has not been written yet.</p>
        <div className="am-state__detail">
          <p>
            The route file exists so that <code>web/src/app/**</code> keeps one writer. The
            screen itself is owned by <strong>{owner}</strong>.
          </p>
          <p>
            To land it: create <code>{awaitingModule}</code> exporting a page component, then
            replace the body of this route with a delegation to it. Do not add logic here —
            an <code>app/</code> route is an adapter and nothing else.
          </p>
        </div>
      </div>
    </PageShell>
  );
}
