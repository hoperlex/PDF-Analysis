/**
 * Exhaustiveness helper.
 *
 * Every closed union in this app comes from the contract. When a `switch` over one is
 * missing an arm, this turns a silent fallthrough into a compile error at the default
 * branch and, if it is ever reached at runtime, into a loud throw rather than a blank
 * screen.
 */
export function assertNever(value: never, context: string): never {
  throw new Error(`${context}: unhandled contract value ${JSON.stringify(value)}`);
}
