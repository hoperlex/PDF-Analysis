/**
 * The 404 screen, and the reason there is one.
 *
 * `D-28`. Next.js matches a dynamic segment against *any* string, so `/projects/<anything>`
 * resolved to the project route and answered **200** while rendering an error state.
 * Only an unrouted *top-level* path 404'd, and that one was the framework's default page.
 *
 * **The consequence is not mainly for users.** The screen said the right thing — "that is
 * not a project address" — to anyone reading it. But a status code is what a journey, a
 * probe or an uptime monitor reads, and a 200 made *"this screen exists and works"*
 * indistinguishable from *"this screen exists and is reporting a failure"*. `W21-E2E`'s
 * committed journey reads the rendered body rather than the status precisely because of
 * this, and that is how the row was found.
 *
 * Each dynamic route now checks the shape of its own segments against the contract's
 * pattern and calls `notFound()`, which lands here with a real 404. The mechanism was
 * already proven in this tree: `app/page.tsx` calls `redirect()` from a server component
 * and that produces a genuine **307** on the wire — measured, not assumed. `notFound()` is
 * the same mechanism at the same seam.
 *
 * The message is written for whoever reached it, and it says what was *not* done — no
 * request was made — because "nothing was requested" and "the server said no" are
 * different answers and a reader should not have to guess which one they got.
 */

import Link from 'next/link';

import { PageShell, UnsupportedState } from '@/shared/ui';
import { routes } from '@/shared/lib';

export default function NotFound() {
  return (
    <PageShell
      title="Страница не найдена"
      actions={<Link href={routes.projects()}>Все проекты</Link>}
    >
      <UnsupportedState
        title="Такого адреса в приложении нет."
        detail="Проект, документ, версия и прогон адресуются непрозрачным идентификатором. В этом пути его нет, поэтому запрос не отправлялся — это не сообщение о том, что сервер чего-то не нашёл."
      />
    </PageShell>
  );
}
