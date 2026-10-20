/**
 * `/` — the application's front door (`W50-PLAN.md` §3.6, `W50-HOME-01`).
 *
 * It greets the account by name, says which roles it holds, and shows three tiles: the five
 * most recent projects, the summary the dashboard reads, and — for a session holding `admin`
 * only — how many registration requests wait for a decision. A session holding `expert` also
 * gets «Мои задачи» (`W61-DISPATCHER-01`): its open assignments, with their moves and links.
 *
 * ## Which tiles: the registry decides, as it does for the screens they summarise
 *
 * Each tile summarises one registered screen — `/projects`, `/dashboard`,
 * `/admin/registrations` — and is mounted only when the screen registry's
 * `screenRolesAdmit` opens that screen to this role set. So a tile cannot offer what the menu
 * and the guard refuse. `R-80`: an account with no role is suspended and the API refuses it
 * every product read, so its home page says «Роли не назначены.», mounts no tile and asks
 * the API nothing.
 *
 * **The props are `W50-REGISTRY-01`'s contract** and this task keeps them: the `/` route and
 * its seed in `web/tests/unit/screens/route-screens.ts` hand down the name and the roles of
 * the subject the route's guard returns. **That subject is the one source of both**: the page
 * does not read `getMe` again, so the name it greets and the roles it decides by are the ones
 * the guard admitted. Everything else on the page is read by the tiles, through the generated
 * client.
 *
 * ## An unknown role is a typed fault, and the page acts on nothing else
 *
 * The role labels are `entities/account`'s, which throws `UnknownRoleError` for a value
 * outside the contract's set. Here that is the page's fault state: the greeting stays, no role
 * is named — not the unknown one and not a generic word for it — and no tile is mounted,
 * because the role set decides what the page asks the API, and a set this build cannot read is
 * not one it may decide by. The BFF already refuses such a `getMe` answer at sign-in, so this
 * is the second line, not the first.
 *
 * ## A long name wraps
 *
 * `displayLabel` is `Фамилия И. О.` with a last name of up to sixty letters, which in one word
 * is wider than the 780 px floor at the title's size. The heading's own rule breaks it
 * anywhere (`home-page.module.css`), so it wraps instead of widening the page.
 */

import type { Role } from '@/shared/api';
import type { ScreenAddress } from '@/shared/config';
import { screenAt } from '@/shared/config';
import { routes } from '@/shared/lib';
import { screenRolesAdmit } from '@/shared/config/screen-registry';
import { ErrorState } from '@/shared/ui';
import { UnknownRoleError, roleLabels } from '@/entities/account';
import { MyTasks } from '@/widgets/my-tasks';
import {
  PendingRegistrationsTile,
  RecentProjectsTile,
  SummaryTile,
  registrationsScreenLink,
} from '@/widgets/home-tiles';

import styles from './home-page.module.css';

export interface HomePageProps {
  /** The account's name as the server resolves it (`Фамилия И. О.`), never empty. */
  readonly displayLabel: string;
  /** The account's role set, exactly as `getMe` listed it. Empty is a valid set. */
  readonly roles: readonly Role[];
}

const UNKNOWN_ROLE_TITLE = 'Учётная запись содержит неизвестную роль.';
const UNKNOWN_ROLE_DETAIL =
  'Сервер назвал роль, которой этот клиент не знает, поэтому решить, что показать на этой странице, достоверно нельзя — плитки скрыты.';

/** The role labels, or `null` when the set holds a value outside the contract's. */
function labelsOf(roles: readonly Role[]): readonly string[] | null {
  try {
    return roleLabels(roles);
  } catch (error) {
    if (error instanceof UnknownRoleError) return null;
    throw error;
  }
}

function rolesSentence(labels: readonly string[]): string {
  return labels.length === 0 ? 'Роли не назначены.' : `Роли: ${labels.join(', ')}.`;
}

/** Whether the registry opens `address` to this role set — the one rule the menu uses too. */
function opens(address: ScreenAddress, roles: readonly Role[]): boolean {
  const screen = screenAt(address);
  return screen !== undefined && screenRolesAdmit(screen.roles, roles);
}

export function HomePage({ displayLabel, roles }: HomePageProps) {
  const labels = labelsOf(roles);
  const projects = opens('/projects', roles);
  const summary = opens('/dashboard', roles);
  const registrations = opens('/admin/registrations', roles);
  // «Мои задачи» summarises the expert's own part of «Диспетчер»: mounted when the registry
  // opens that screen and the session holds `expert`, the role work is assigned to.
  const tasks = opens('/dispatcher', roles) && roles.includes('expert');

  return (
    <section className="am-page" data-screen="home">
      <header className="am-page__header">
        <div className={styles.heading}>
          {/*
            One text node, and an exclamation rather than a period: the name form ends in one
            (`Петрова А. С.`), and a period after it reads `С..`.
          */}
          <h1 className={`am-page__title ${styles.greeting}`}>{`Здравствуйте, ${displayLabel}!`}</h1>
          {labels === null ? null : (
            <p className="am-page__subtitle" data-roles={roles.join(' ')}>
              {rolesSentence(labels)}
            </p>
          )}
        </div>
      </header>
      <div className="am-page__body">
        {labels === null ? (
          <div data-home-fault="closed-vocabulary">
            <ErrorState title={UNKNOWN_ROLE_TITLE} detail={UNKNOWN_ROLE_DETAIL} />
          </div>
        ) : projects || summary || registrations || tasks ? (
          <>
            {tasks ? <MyTasks roles={roles} listHref={routes.dispatcher()} /> : null}
            {projects || summary || registrations ? (
              <div className={styles.tiles}>
                {projects ? <RecentProjectsTile /> : null}
                {summary ? <SummaryTile /> : null}
                {registrations ? <PendingRegistrationsTile href={registrationsScreenLink()} /> : null}
              </div>
            ) : null}
          </>
        ) : (
          <p className="am-note" data-home-tiles="none">
            Разделы с данными откроются, когда администратор назначит учётной записи роль.
          </p>
        )}
      </div>
    </section>
  );
}
