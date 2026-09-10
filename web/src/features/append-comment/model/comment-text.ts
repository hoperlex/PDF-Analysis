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

export type CommentRefusal = 'empty';

export type CommentCheck =
  | { readonly kind: 'ok'; readonly comment: string }
  | { readonly kind: 'refused'; readonly refusal: CommentRefusal };

export function checkComment(raw: string): CommentCheck {
  const comment = raw.trim();
  if (comment.length === 0) return { kind: 'refused', refusal: 'empty' };
  return { kind: 'ok', comment };
}
