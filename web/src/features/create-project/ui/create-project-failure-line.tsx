/**
 * The refusal of a create, as one line (`UIP-S03-01`): what the window «Новый объект» says under its field.
 *
 * The page's form draws a refusal as a block (`ErrorState` / `UnsupportedState`, with a retry button), which a window cannot
 * spare room for. The window has one line: the title, then the detail, then the correlation id when the server gave one.
 * No retry button: «Создать» is the retry, and for the same name it carries the same idempotency key, so pressing it again is
 * the same command and never a second object (`useIntentKey`). Whether the refusal can be retried is in the detail's own words.
 *
 * Markup only: the classification (`classifyCreateProjectFailure`) is the entity's, and the form passes its result in.
 */

import type { CreateProjectFailure } from '@/entities/project';

export function CreateProjectFailureLine({ failure }: { readonly failure: CreateProjectFailure }) {
  return (
    <p className="am-form__problem" role="alert" data-create-failure={failure.kind}>
      {failure.title} {failure.detail}
      {failure.correlationId === null ? null : ` Код обращения: ${failure.correlationId}`}
    </p>
  );
}
