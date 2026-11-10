/**
 * One request per press of «Отозвать» / «Вернуть», however many times the button is pressed.
 *
 * The same gate `classify-version` and `correct-version-classification` press through, restated here rather than imported: a
 * feature does not reach into another feature's internals. `disabled={isPending}` alone does not give it: React re-renders after
 * the first press, and a double click delivers its second press before the button is disabled. Found by the browser journey
 * (`D-503`, lane MEM-JOURNEY): two presses sent two `POST`s under one Idempotency-Key. The server answered both with the same
 * status event and wrote one, so nothing was lost, but the screen sent a request it had no reason to send.
 *
 * Plain state, no React: the control keeps one gate for its lifetime, and a unit test drives it directly, which the static render
 * harness cannot do with a click. The gate closes synchronously on the first call and opens again when that call's work settles.
 */

export interface SingleFlight {
  /** Whether a call is in flight now. */
  readonly busy: boolean;
  /** Start `task` unless one is already in flight. Returns whether it was started. The task's failure is the caller's to observe. */
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
