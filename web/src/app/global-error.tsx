'use client';

/**
 * The last error boundary: a failure in the root layout itself (`C-24`).
 *
 * `app/error.tsx` catches a screen that throws, but it renders *inside* the root layout, so a
 * throw in the layout — the frame, the session read, the providers — fell through to the
 * framework's own page, which is English and, in development, prints the error. Next renders
 * this file in place of the whole layout, which is why it writes its own `<html>` and
 * `<body>`, and why it uses no shared component that assumes the frame's providers.
 *
 * Like `app/error.tsx` it prints nothing of the error — no message, no stack, no name — and
 * shows only the opaque `digest` an operator can trace.
 */

const PAGE_TITLE = 'Приложение не открылось';
const FAILURE_DETAIL =
  'При построении страницы произошла ошибка. Ничего не изменено. Страницу можно запросить ещё раз; если ошибка повторится, сообщите о ней, указав идентификатор ниже.';
const RETRY_LABEL = 'Открыть ещё раз';
const DIGEST_LABEL = 'Идентификатор:';

export interface GlobalErrorProps {
  readonly error: Error & { readonly digest?: string };
  readonly reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  const digest = error.digest ?? null;
  return (
    <html lang="ru">
      <body>
        <main data-global-error="">
          <h1>{PAGE_TITLE}</h1>
          <p role="alert">{FAILURE_DETAIL}</p>
          {digest === null ? null : (
            <p>
              {DIGEST_LABEL} <code>{digest}</code>
            </p>
          )}
          <button type="button" onClick={reset}>
            {RETRY_LABEL}
          </button>
        </main>
      </body>
    </html>
  );
}
