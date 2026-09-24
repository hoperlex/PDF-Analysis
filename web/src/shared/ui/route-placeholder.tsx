/**
 * The shell's stand-in for a section that is not available yet.
 *
 * This is not a loading state and not an error state. Nothing was requested and nothing
 * failed: the section has not been built. Rendering `LoadingState` here would be a lie
 * that never resolves.
 *
 * **What it says, and to whom.** Before `R-18` this rendered the developer's own note —
 * which `_pages` module was awaited, which session owned it, and the one-line change to
 * land it — on a screen an expert opens. `R-18` makes the alpha's interface the thing a
 * reviewer is shown, and a reviewer has no use for a module path. The routing facts are
 * kept, because they are useful, but as `data-` attributes rather than as prose: they
 * reach a developer reading the DOM and never reach the page.
 */

import { PageShell } from './page-shell';

export interface RoutePlaceholderProps {
  /** The section's name, as the reviewer would call it. */
  readonly screen: string;
  /** The route URL this file serves. */
  readonly route: string;
  /** The `_pages` module that will replace this, e.g. `@/_pages/projects`. */
  readonly awaitingModule?: string | undefined;
  /** The session that owns that module. */
  readonly owner?: string | undefined;
  /** One sentence on what will be here, shown to the reviewer. */
  readonly promise?: string | undefined;
  /**
   * The two sentences that say WHY the section is not here, for a section whose default
   * reading would be false.
   *
   * Both default to today's wording and neither may be left out where the default is
   * wrong. `«Раздел пока недоступен»` and `«Этот раздел ещё не готов.»` both carry a
   * *yet*: they tell a reviewer the section is on its way. That is true of the thirteen
   * project sections and of three of `W43-PREP`'s four, and it is **false of workers** —
   * `PROTOTYPE_PROFILE.md` §7.2 defers remote/distributed executors and the whole
   * `Job/Attempt` framework, so nobody has decided to build them. `R-18` says a stub may
   * not claim something false about the system, and *"coming soon"* is a claim.
   *
   * They are optional and default to the existing strings, so every caller that predates
   * this prop renders exactly the bytes it rendered before.
   */
  readonly unavailability?: string | undefined;
  /** The headline above the promise. Defaults to the "not ready yet" wording. */
  readonly headline?: string | undefined;
}

export function RoutePlaceholder({
  screen,
  route,
  awaitingModule,
  owner,
  promise,
  unavailability,
  headline,
}: RoutePlaceholderProps) {
  return (
    <PageShell title={screen} subtitle={unavailability ?? 'Раздел пока недоступен'}>
      <div
        className="am-state am-state--neutral"
        role="status"
        data-route={route}
        {...(awaitingModule === undefined ? {} : { 'data-awaiting-module': awaitingModule })}
        {...(owner === undefined ? {} : { 'data-owner': owner })}
      >
        <p className="am-state__title">{headline ?? 'Этот раздел ещё не готов.'}</p>
        <div className="am-state__detail">
          <p>
            {promise ??
              'Раздел появится в одной из следующих версий. Ничего не сломалось и никакие данные не потеряны — этой части приложения пока просто нет.'}
          </p>
        </div>
      </div>
    </PageShell>
  );
}
