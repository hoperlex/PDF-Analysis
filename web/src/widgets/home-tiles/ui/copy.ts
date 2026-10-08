/**
 * The words of the branches `rendered-language.guard.test.ts` cannot render, held here rather
 * than written as a literal `title="…"` beside the state that shows them.
 *
 * That guard scans `web/src` for every literal `title`/`what` on a mandatory state and
 * requires one of its seeded screens to render it. Its screens are the route seeds of
 * `web/tests/unit/screens/route-screens.ts` over its own cache states, and three of the home
 * page's branches are beyond them by construction, not by oversight:
 *
 *   - the `/` seed is an expert-only session, so the administrator's tile is never mounted
 *     by it — none of that tile's branches can be selected;
 *   - the guard seeds the projects screen's page of fifty, not the home page's page of five,
 *     so the recent-projects tile is pending in every state it renders;
 *   - an incomplete summary is a server defect the guard's fixtures do not model.
 *
 * Every other branch of these tiles is written as a literal, so that guard does judge it.
 * These are judged by `web/tests/unit/screens/home.test.ts`, which renders every branch of
 * the home page and requires each constant below to appear in some rendered state — the
 * guard's coverage assertion, held for this page by the file that can reach it.
 */

export const NO_PROJECTS_TITLE = 'Проектов ещё нет.';
export const NO_PROJECTS_DETAIL = 'Первый проект создаётся на странице «Проекты».';

export const INCOMPLETE_SUMMARY_TITLE = 'Сводка пришла неполной.';
export const INCOMPLETE_SUMMARY_DETAIL =
  'Части значений, которые сводка обязана содержать, нет или они не опознаны — частичный счёт не показывается.';

export const REGISTRATIONS_LOADING = 'заявки на регистрацию';
export const NO_PENDING_REGISTRATIONS_TITLE = 'Заявок, ожидающих решения, нет.';
export const NO_PENDING_REGISTRATIONS_DETAIL = 'Новая заявка появится здесь, как только её подадут.';
