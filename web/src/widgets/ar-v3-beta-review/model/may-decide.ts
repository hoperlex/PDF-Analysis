/**
 * Who is offered the verdict controls on an AR v3 finding (`R-146as`).
 *
 * `appendDecision` is an expert's operation: an administrator alone is refused by the server
 * (`permission_denied`, `required_capability: role:expert`). The panel offers the controls to an
 * expert only, so a person who may not decide sees the findings and no button that would be refused.
 * This is the browser's courtesy and not the control: the server decides again on every write.
 */
export function mayRecordVerdict(roles: readonly string[]): boolean {
  return roles.includes('expert');
}
