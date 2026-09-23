/** Public API of the `append-comment` feature: append a comment without touching a verdict. */

export type { CommentCheck, CommentRefusal } from './model/comment-text';
export { COMMENT_REFUSALS, checkComment, commentRefusalMessage } from './model/comment-text';

export type { AppendCommentApi, AppendCommentArgs } from './model/use-append-comment';
export { useAppendComment } from './model/use-append-comment';
