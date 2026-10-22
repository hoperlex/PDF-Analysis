/**
 * `useMutation` as the browser has it, without a browser (`WEB-HOOKS-PER-FINDING-01`).
 *
 * The verdict and comment hooks are bound to ONE finding but live at page level, so what they
 * report about a press has to survive a change of selection and must not be told to the wrong
 * finding. Whether it is told to the wrong finding depends on what React Query does with a
 * mutation across renders, and the older hook tests replace `useMutation` by a record of
 * whatever the test sets -- which cannot show a defect that lives in the way the real observer
 * behaves. This model does not invent that behaviour. It builds the REAL `MutationObserver`
 * over a REAL `QueryClient` and does the two things `useMutation` does around it:
 *
 *   - one observer per call site, kept across renders (`useState(() => new MutationObserver)`);
 *   - `observer.setOptions(options)` on every render (`useEffect` in the real hook). That call
 *     also rewrites the options of a mutation that is still PENDING, so the callbacks a request
 *     finishes with are the ones of the LATEST render, not of the render that sent it.
 *
 * What it leaves out is the subscription: there is no screen to re-render, so a test re-renders
 * by calling the hooks again, and reads `observer.getCurrentResult()`, which the observer keeps
 * up to date without a listener.
 *
 * `mutate` swallows the rejection the real hook's `mutate` swallows (an error is state, not a
 * thrown value).
 */

import type { MutationObserver, QueryClient } from '@tanstack/react-query';

type Query = typeof import('@tanstack/react-query');

export interface MutationModel {
  readonly client: QueryClient;
  /** Start a render: the next `useMutation` call is the first call site again. */
  readonly rewind: () => void;
  readonly useMutation: (options: never) => unknown;
}

export function createMutationModel(
  actual: Pick<Query, 'MutationObserver' | 'QueryClient'>,
): MutationModel {
  const client = new actual.QueryClient();
  const observers: MutationObserver<unknown, unknown, unknown, unknown>[] = [];
  let next = 0;

  return {
    client,
    rewind: () => {
      next = 0;
    },
    useMutation: (options) => {
      const at = next;
      next += 1;
      let observer = observers[at];
      if (observer === undefined) {
        observer = new actual.MutationObserver(client, options as never);
        observers[at] = observer;
      } else {
        observer.setOptions(options as never);
      }
      const result = observer.getCurrentResult();
      const held = observer;
      return {
        ...result,
        mutate: (variables: unknown) => {
          held.mutate(variables).catch(() => {});
        },
        reset: () => {
          held.reset();
        },
      };
    },
  };
}
