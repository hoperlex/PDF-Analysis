/**
 * Which rows of the pairs catalog are on the screen (`UI-B-85`, the N+1 fix of the stage pair catalog).
 *
 * A row says what the pair's latest run is, and each row's run list is a read of its own. The catalog lists up to a hundred pairs,
 * so reading every row on open was a hundred walks of the run list and, once a batch ran, a hundred polls. A row now reads, and
 * polls, only while it is in view; this module is the watcher that says which rows those are. It is written over a factory of
 * the browser's `IntersectionObserver` so a test drives it with a scripted one, and nothing here touches `window` until the first
 * row is watched.
 */

/** What of an `IntersectionObserverEntry` the watcher reads. */
export interface ViewportEntry {
  readonly target: Element;
  readonly isIntersecting: boolean;
}

/** What of an `IntersectionObserver` the watcher calls. */
export interface ViewportObserver {
  observe(target: Element): void;
  unobserve(target: Element): void;
}

/**
 * Makes the observer, handing it the function that receives its entries; `null` when the client has no
 * `IntersectionObserver`. With none, every watched row is reported in view at once, which is the catalog's behaviour before this
 * fix (every row read): an old client reads more, it never shows a row unread as read.
 */
export type ViewportObserverFactory = (onEntries: (entries: readonly ViewportEntry[]) => void) => ViewportObserver | null;

/** Watches one element; reports every change of whether it is in view; returns the function that stops watching it. */
export type WatchViewport = (element: Element, onChange: (visible: boolean) => void) => () => void;

export function createViewportWatcher(make: ViewportObserverFactory): WatchViewport {
  const listeners = new Map<Element, (visible: boolean) => void>();
  let observer: ViewportObserver | null | undefined;
  return (element, onChange) => {
    if (observer === undefined) {
      observer = make((entries) => {
        for (const entry of entries) listeners.get(entry.target)?.(entry.isIntersecting);
      });
    }
    if (observer === null) {
      onChange(true);
      return () => undefined;
    }
    listeners.set(element, onChange);
    observer.observe(element);
    return () => {
      listeners.delete(element);
      observer?.unobserve(element);
    };
  };
}

/** A row is read a little before it scrolls in, so its figures are there when it arrives. */
const ROW_MARGIN = '200px 0px';

/** The watcher the catalog uses: the browser's own observer, made on the first row. */
export const watchViewport: WatchViewport = createViewportWatcher((onEntries) =>
  typeof IntersectionObserver === 'undefined'
    ? null
    : new IntersectionObserver((entries) => onEntries(entries), { rootMargin: ROW_MARGIN }));

/** The set of rows in view after one row's change; the same set when nothing changed, so a repeat report renders nothing. */
export function withRowVisibility(prior: ReadonlySet<string>, pairId: string, visible: boolean): ReadonlySet<string> {
  if (prior.has(pairId) === visible) return prior;
  const next = new Set(prior);
  if (visible) next.add(pairId); else next.delete(pairId);
  return next;
}
