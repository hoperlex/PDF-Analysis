/**
 * What counts as a comment worth appending.
 *
 * `AppendDecisionRequest.comment` is "required for `comment`", so an empty one is a
 * `validation_failed` waiting to happen. Refusing it in the browser is not a second
 * validation of the contract — the server stays the authority — it is refusing to append
 * an event to a ledger that cannot delete one.
 *
 * The text is otherwise passed through untouched apart from trimming the surrounding
 * whitespace a textarea collects. Nothing collapses interior whitespace, truncates, or
 * rewrites quote characters: the comment is the reviewer's words and it becomes an
 * immutable row.
 */

/**
 * Every reason this tier refuses to send, as a value.
 *
 * DECLARED AS AN ARRAY so the set is enumerable at run time as well as at compile time,
 * which is `SIGN_IN_REFUSALS`'s shape eight files away and is what lets a test render the
 * screen for EVERY member rather than for the one whoever wrote the test remembered.
 * `D-84` is the row that asks for this: the decision panel matched the literal `'empty'`
 * and a second member would have been refused in silence.
 */
export const COMMENT_REFUSALS = ['empty'] as const;

export type CommentRefusal = (typeof COMMENT_REFUSALS)[number];

/**
 * The sentence a reviewer reads. The machine value stays on the `data-` attribute.
 *
 * THE SWITCH HAS NO `default` ON PURPOSE. A `default` would make this function total over
 * a union it has not been told about, which is the same silence one layer down: adding a
 * member would compile and the new refusal would read as the old sentence. Without one,
 * `tsc` refuses the file — *"Function lacks ending return statement and return type does
 * not include 'undefined'"* — until the member has words. That refusal is `D-84`'s repair;
 * the widget rendering on PRESENCE is what makes it reach the screen.
 */
export function commentRefusalMessage(refusal: CommentRefusal): string {
  switch (refusal) {
    case 'empty':
      return 'Событию комментария нужен текст. Ничего не отправлено.';
  }
}

export type CommentCheck =
  | { readonly kind: 'ok'; readonly comment: string }
  | { readonly kind: 'refused'; readonly refusal: CommentRefusal };

export function checkComment(raw: string): CommentCheck {
  const comment = raw.trim();
  if (comment.length === 0) return { kind: 'refused', refusal: 'empty' };
  return { kind: 'ok', comment };
}
