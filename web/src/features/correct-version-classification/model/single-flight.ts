/**
 * One request per correction, however many times the button is pressed.
 *
 * The same gate `classify-version` presses through, restated here rather than imported: a
 * feature does not reach into another feature's internals. See that file for why
 * `disabled={pending}` alone is not enough.
 */

export interface SingleFlight {
  /** Whether a call is in flight now. */
  readonly busy: boolean;
  /** Start `task` unless one is already in flight. Returns whether it was started. */
  run(task: () => Promise<unknown>): boolean;
}

export function createSingleFlight(): SingleFlight {
  let busy = false;
  return {
    get busy() {
      return busy;
    },
    run(task) {
      if (busy) return false;
      busy = true;
      let work: Promise<unknown>;
      try {
        work = task();
      } catch (error) {
        busy = false;
        throw error;
      }
      void work.then(
        () => {
          busy = false;
        },
        () => {
          busy = false;
        },
      );
      return true;
    },
  };
}
