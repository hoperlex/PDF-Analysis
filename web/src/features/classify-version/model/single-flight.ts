/**
 * One request per confirmation, however many times the button is pressed.
 *
 * `disabled={pending}` alone does not give that: React re-renders after the first press, and
 * a double click delivers its second press before the button is disabled. This gate closes
 * synchronously on the first call and opens again only when that call's work settles, so a
 * second press in the same tick is refused here rather than sent.
 *
 * Plain state, no React: the form keeps one gate for its lifetime, and a unit test drives it
 * directly, which the static render harness cannot do with a click.
 */

export interface SingleFlight {
  /** Whether a call is in flight now. */
  readonly busy: boolean;
  /**
   * Start `task` unless one is already in flight. Returns whether it was started. The task's
   * own failure is the caller's to observe; the gate only reopens.
   */
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
