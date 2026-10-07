/**
 * The set of screens this application has, **derived from the route tree**, and the seeds
 * that make each one renderable.
 *
 * ## Why this file exists — `D-88`, measured twice and negative both times
 *
 * `D-69`'s repair made `rendered-language.guard.test.ts` derive **which contract members**
 * must be rendered from the contract, and left **which screens are rendered** a
 * hand-written `const SCREENS = [...]`. `tests/unit/styles/screens.ts` was a hand-written
 * import list for the same reason. So a screen that exists was invisible to both
 * instruments until somebody remembered to add it.
 *
 * `W43-PREP` measured the cost and `W43-JUDGE-A` measured it again, harder: English prose
 * on four new screens, four different sentences, and **the whole frontend suite stayed
 * green — 73 files, 1047 tests, 0 failed.** It was reproduced once more at `386130e`,
 * this wave, before this file was written: the same probe left the language guard green
 * over four English sentences and left `R-33`'s 3:1 floor green over a border measured at
 * **1.08:1** on an element a screen really rendered. The only red was the contrast
 * census's *unreached rule* case, and what it said was **false**:
 *
 * > these rules declare a colour and NO screen in `screens.ts` renders an element they
 * > match … expected [ '._frame_d22d03' ] to deeply equal []
 *
 * `BlocksPage` rendered that element. `screens.ts` did not render `BlocksPage`. A reader
 * sent to look for a rule nobody uses would have found a rule the product uses on a page
 * the census could not open — and the message named a bundler hash rather than the screen.
 *
 * ## What is derived and what is not
 *
 * Wave 41's rule, which this file is the second application of: **coverage is derived from
 * the contract; the seeds are not. The question is derived; a human answers it.**
 *
 *   DERIVED, from `web/src/app`      which addresses exist, and which dynamic segments each
 *                                    one takes. `routeAddresses()` walks the tree for
 *                                    `page.tsx` the way
 *                                    `tests/e2e/test_pc01_journey_conformance.py` already
 *                                    does with `rglob("page.tsx")`.
 *   HAND-WRITTEN, in `SEEDS`         what it takes to RENDER one: the component behind the
 *                                    address, the props it needs, and what the screen is
 *                                    expected to do with a malformed segment.
 *
 * A new `page.tsx` with no seed makes `screen-set.guard.test.ts` red **naming the
 * address**. Deriving the seed instead would let a new screen seed itself and both
 * instruments would go green over a screen nobody had looked at — the same silence, one
 * level up.
 *
 * ## The hard part: what a derived screen needs in order to be RENDERED
 *
 * The glob is the easy half. Three things stood between an address and a render, and each
 * is answered here rather than caught:
 *
 *   1. **A route file is not a component this harness can render.** Every `page.tsx` under
 *      a dynamic segment is an `async` server component whose `params` arrive as a
 *      promise, and `renderToStaticMarkup` cannot render one. So a seed names the
 *      `_pages` slice the route delegates to — which is also the thing a reviewer reads —
 *      and `routes.test.ts` is what holds the delegation itself.
 *   2. **Identifiers.** A dynamic segment's value is a prop, and the shape of it decides
 *      which branch renders. `make` therefore receives the segment values BY SEGMENT NAME
 *      — `project_uid`, `run_id` — which are the names the directory layout already
 *      carries, so a seed cannot silently pass a run id where a version uid belongs.
 *   3. **Cache state.** A screen with a query renders a spinner until its cache is seeded,
 *      and every seed here is deliberately state-free: the state matrix belongs to the
 *      instrument (`CACHE_STATES` in the language guard, the populated clients in the
 *      contrast census) and this file must not duplicate it. `make` returns the ELEMENT
 *      and the caller decides the client it renders under.
 *
 * ## How a screen opts out, and why an opt-out is not a `catch`
 *
 * None does today. The one there was — `/`, while it was a bare `redirect("/projects")` —
 * became an ordinary seed when `W50-REGISTRY-01` gave the address a screen of its own. An
 * opt-out is **an entry in `SEEDS` like any other**, carrying `optOut` instead of `make`,
 * and it has to satisfy three things or the guard is red:
 *
 *   - a `why` a reader can act on, at least 80 characters;
 *   - a `proof` — a zero-argument behavioural probe which the guard RUNS against what the
 *     route file does, so changing what the route does is red even if its source still
 *     contains the old words;
 *   - it is still counted. `routeAddresses().length` and the opt-out list are both
 *     asserted, so an address cannot leave the census by being excused.
 *
 * **A `try/catch` around a render is not an opt-out and must never become one.** It cannot
 * state a reason, nothing checks it, and it turns a screen that throws — which is a defect
 * — into a screen that is merely absent, which is what `D-88` is. That is this defect
 * returning in a new costume, and it is written here so the next reader has to argue
 * against a sentence rather than merely notice an absence.
 */

import { createElement } from 'react';
import type { ReactElement } from 'react';

import { AccountPage } from '@/_pages/account';
import { AdminRegistrationsPage } from '@/_pages/admin-registrations';
import { AdminUserPage } from '@/_pages/admin-user';
import { AdminUsersPage } from '@/_pages/admin-users';
import { AnalysisSettingsPage } from '@/_pages/analysis-settings';
import { BlocksPage } from '@/_pages/blocks';
import { ChangePasswordPage } from '@/_pages/change-password';
import { DashboardPage } from '@/_pages/dashboard';
import { DocumentDetailPage } from '@/_pages/document-detail';
import { ForbiddenPage } from '@/_pages/forbidden';
import { HomePage } from '@/_pages/home';
import { KnowledgeBasePage } from '@/_pages/knowledge-base';
import { LogsPage } from '@/_pages/logs';
import { NormsPage } from '@/_pages/norms';
import { OptimisationPage } from '@/_pages/optimisation';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { ProjectsPage } from '@/_pages/projects';
import { QueuePage } from '@/_pages/queue';
import { RegisterPage } from '@/_pages/register';
import { RegisterSubmittedPage } from '@/_pages/register-submitted';
import { ReviewPage } from '@/_pages/review';
import { RunPage } from '@/_pages/run';
import { SectionOptimisationPage } from '@/_pages/section-optimisation';
import { SignInPage } from '@/_pages/sign-in';
import { StageComparisonPage } from '@/_pages/stage-comparison';
import { VersionDetailPage } from '@/_pages/version-detail';
import { WorkersPage } from '@/_pages/workers';

import { REPO_ROOT, repoRelative, walkFiles } from '../../guards/lib/repo';
import { join } from 'node:path';

// ==================================================================== the derived question

/** `<repo>/web/src/app` — the route tree, which is the subject of the derivation. */
export const APP_ROOT = join(REPO_ROOT, 'web', 'src', 'app');

export interface RouteAddress {
  /** The address Next serves, with dynamic segments left as `[name]`. */
  readonly address: string;
  /** The `page.tsx` that serves it, repo-relative. */
  readonly file: string;
  /** The dynamic segment names, outermost first, as the directory layout spells them. */
  readonly segments: readonly string[];
}

/**
 * Every address `web/src/app` offers, read off the filesystem.
 *
 * Route groups (`(name)`) and parallel/intercepting routes (`@slot`, `(.)`) are not used
 * in this tree today. They are not silently stripped here: an address containing one
 * would come through with the bracket in it, fail to match any seed, and be NAMED by the
 * guard — which is the outcome this file wants for anything it has not been taught.
 */
export function routeAddresses(): readonly RouteAddress[] {
  const PREFIX = 'web/src/app/';
  const SUFFIX = '/page.tsx';
  return walkFiles(APP_ROOT, (path) => path.endsWith('/page.tsx'))
    .map((file) => {
      const relative = repoRelative(file);
      // `web/src/app/page.tsx` slices to the empty string and is therefore `/`, which is
      // the one address whose directory is the app root itself.
      const address = `/${relative.slice(PREFIX.length, relative.length - SUFFIX.length)}`;
      return {
        address,
        file: relative,
        segments: [...address.matchAll(/\[([^\]]+)\]/g)].map((m) => m[1] as string),
      };
    })
    .sort((a, b) => a.address.localeCompare(b.address));
}

// ===================================================================== the human's answers

/** The values a segment takes in a seed, keyed by the name the directory layout gives it. */
export type SegmentValues = Readonly<Record<string, string>>;

/**
 * What a screen does when one of its own segments is malformed.
 *
 * This is the half of `D-90` that no derivation can supply, and it is the reason the
 * answer is written here rather than read out of the component. `StageComparisonPage`
 * re-checks `looksLikeProjectUid` itself; delete the call and the whole frontend suite
 * stayed green, 75 files and 1085 tests. A guard that recovered the expectation by
 * scanning the component for `looksLike…(` would have gone green on that same mutation,
 * because the mutation deletes the scan's evidence along with the behaviour —
 * `OPERATING_CONSTRAINTS.md` §12, a query sharing an assumption with its subject.
 *
 *   `refuses`           the SCREEN itself refuses a malformed value for this segment and
 *                       renders `UnsupportedState`. Asserted by rendering it.
 *   `defers-to-route`   only the route file refuses it; the screen renders normally.
 *                       Asserted the same way, in the other direction, so a screen that
 *                       silently gained a check is red too.
 */
export type SegmentDiscipline = 'refuses' | 'defers-to-route';

export interface RenderedSeed {
  readonly address: string;
  /** A stable name used in every failure message both instruments print. */
  readonly name: string;
  readonly make: (segments: SegmentValues) => ReactElement;
  /** One entry per dynamic segment of the address. Asserted against the derived set. */
  readonly discipline: Readonly<Record<string, SegmentDiscipline>>;
  readonly optOut?: undefined;
}

export interface OptedOutSeed {
  readonly address: string;
  readonly name: string;
  readonly make?: undefined;
  readonly optOut: {
    readonly why: string;
    /**
     * **Run against what the route file DOES, not against what it says.**
     *
     * `W44-JUDGE-A` defeated the first version of this, which was a predicate over the
     * file's source: `/\bredirect\(/.test(source) && !/\breturn\s*\(/.test(source)`.
     * A page that renders a whole screen of English prose satisfies both halves, so the
     * proof did not check the claim it exists for — *"it renders nothing"* — and the
     * guard that runs every opt-out claim stayed green while `/` rendered.
     *
     * A text predicate over a file is a claim about a file. **The claim here is about
     * behaviour**, so `invoke` calls the route module's own default export and the proof
     * answers from what happened. A screen that returns anything at all fails it,
     * whatever its source looks like.
     */
    readonly proof: () => boolean;
  };
}

export type Seed = RenderedSeed | OptedOutSeed;

export const SEEDS: readonly Seed[] = [
  {
    /*
     * `W50-REGISTRY-01`: an ordinary seed since `/` stopped redirecting. Was the
     * `root-redirect` opt-out. `W50-HOME-01` changes what `HomePage` renders and keeps these
     * props, so this seed renders the home page it builds without being touched. The label
     * is Cyrillic like every value this file seeds, and the longest a name form reaches in
     * practice is HOME's own case, not this one's.
     */
    address: '/',
    name: 'home',
    make: () => createElement(HomePage, { displayLabel: 'Петрова А. С.', roles: ['expert'] }),
    discipline: {},
  },
  {
    /*
     * `W50-SHELL-FRAME`, granted at the Stage-B merges and widened by the integrator's ruling
     * of 2026-10-07 (Q3): the same address for a session holding `admin`. The expert's seed
     * above cannot mount the administrator tile, so without this one the language guard and
     * the census never read it. A second seed for one address is why `derivedScreens()`
     * yields every seed of an address, in this order.
     */
    address: '/',
    name: 'home-admin',
    make: () => createElement(HomePage, { displayLabel: 'Проверкина А. С.', roles: ['admin', 'expert'] }),
    discipline: {},
  },
  {
    // `R-60` gives no W50 screen a role, so the live `/403` names none; a seed that names one
    // is the screen a role-gated row will send a session to, and it is the one the
    // instruments should read.
    address: '/403',
    name: 'forbidden',
    make: () => createElement(ForbiddenPage, { requiredRoles: ['admin'] }),
    discipline: {},
  },
  {
    // The placeholder the guard sends an incomplete profile to: the state it exists for.
    address: '/account',
    name: 'account-incomplete',
    make: () => createElement(AccountPage, { profileComplete: false }),
    discipline: {},
  },
  {
    address: '/account/password',
    name: 'change-password-signed-out',
    make: () => createElement(ChangePasswordPage, {}),
    discipline: {},
  },
  {
    address: '/register',
    name: 'register',
    make: () => createElement(RegisterPage, {}),
    discipline: {},
  },
  {
    address: '/register/submitted',
    name: 'register-submitted',
    make: () => createElement(RegisterSubmittedPage, {}),
    discipline: {},
  },
  {
    address: '/admin/users',
    name: 'admin-users',
    make: () => createElement(AdminUsersPage, {}),
    discipline: {},
  },
  {
    address: '/admin/users/[user_uid]',
    name: 'admin-user',
    make: (s) => createElement(AdminUserPage, { userUid: s['user_uid'] as string }),
    discipline: { user_uid: 'defers-to-route' },
  },
  {
    address: '/admin/registrations',
    name: 'admin-registrations',
    make: () => createElement(AdminRegistrationsPage, {}),
    discipline: {},
  },
  {
    address: '/blocks',
    name: 'blocks',
    make: () => createElement(BlocksPage, {}),
    discipline: {},
  },
  {
    address: '/dashboard',
    name: 'dashboard',
    make: () => createElement(DashboardPage, {}),
    discipline: {},
  },
  {
    address: '/analysis-settings',
    name: 'analysis-settings',
    make: () => createElement(AnalysisSettingsPage, {}),
    discipline: {},
  },
  {
    address: '/knowledge-base',
    name: 'knowledge-base',
    make: () => createElement(KnowledgeBasePage, {}),
    discipline: {},
  },
  {
    address: '/login',
    name: 'sign-in',
    make: () => createElement(SignInPage, {}),
    discipline: {},
  },
  { address: '/logs', name: 'logs', make: () => createElement(LogsPage, {}), discipline: {} },
  { address: '/norms', name: 'norms', make: () => createElement(NormsPage, {}), discipline: {} },
  {
    address: '/optimisation',
    name: 'optimisation',
    make: () => createElement(OptimisationPage, {}),
    discipline: {},
  },
  {
    address: '/projects',
    name: 'projects',
    make: () => createElement(ProjectsPage, {}),
    discipline: {},
  },
  {
    address: '/projects/[project_uid]',
    name: 'project-detail',
    make: (s) => createElement(ProjectDetailPage, { projectUid: s['project_uid'] as string }),
    discipline: { project_uid: 'refuses' },
  },
  {
    address: '/projects/[project_uid]/documents/[document_uid]',
    name: 'document-detail',
    make: (s) =>
      createElement(DocumentDetailPage, {
        projectUid: s['project_uid'] as string,
        documentUid: s['document_uid'] as string,
      }),
    discipline: { project_uid: 'refuses', document_uid: 'refuses' },
  },
  {
    address: '/projects/[project_uid]/runs/[run_id]',
    name: 'run',
    make: (s) =>
      createElement(RunPage, {
        projectUid: s['project_uid'] as string,
        runId: s['run_id'] as string,
      }),
    /*
     * The run screen and the review screen check NOTHING of their own, and that is a
     * property of the product rather than a gap in this file. `app/.../runs/[run_id]/
     * page.tsx` calls `notFound()` for a malformed segment, so the component is never
     * reached with one in the deployed application. Declaring it here is what makes the
     * difference between these two screens and the other four an assertion instead of an
     * accident: a check added to either of them without a decision is red.
     */
    discipline: { project_uid: 'defers-to-route', run_id: 'defers-to-route' },
  },
  {
    address: '/projects/[project_uid]/runs/[run_id]/review',
    name: 'review',
    make: (s) =>
      createElement(ReviewPage, {
        projectUid: s['project_uid'] as string,
        runId: s['run_id'] as string,
      }),
    discipline: { project_uid: 'defers-to-route', run_id: 'defers-to-route' },
  },
  {
    address: '/projects/[project_uid]/versions/[version_uid]',
    name: 'version-detail',
    make: (s) =>
      createElement(VersionDetailPage, {
        projectUid: s['project_uid'] as string,
        versionUid: s['version_uid'] as string,
      }),
    discipline: { project_uid: 'refuses', version_uid: 'refuses' },
  },
  {
    address: '/projects/[project_uid]/versions/[version_uid]/comparison',
    name: 'stage-comparison',
    make: (s) =>
      createElement(StageComparisonPage, {
        projectUid: s['project_uid'] as string,
        versionUid: s['version_uid'] as string,
      }),
    /*
     * `D-90`. Both of these are live conditions inside the component, and before wave 44
     * neither was asserted by anything: removing the `looksLikeProjectUid` call left 75
     * files and 1085 tests green. The naive mutation — deleting the call — dies at `tsc`
     * for an unused import, which is a red about the import and says nothing about the
     * condition; keeping the import used and dropping only the branch was green.
     */
    discipline: { project_uid: 'refuses', version_uid: 'refuses' },
  },
  { address: '/queue', name: 'queue', make: () => createElement(QueuePage, {}), discipline: {} },
  {
    address: '/section-optimisation',
    name: 'section-optimisation',
    make: () => createElement(SectionOptimisationPage, {}),
    discipline: {},
  },
  {
    address: '/workers',
    name: 'workers',
    make: () => createElement(WorkersPage, {}),
    discipline: {},
  },
];

// ================================================================== joining the two halves

/** A value of the right shape for each segment name this tree uses. */
export function wellFormed(identities: {
  readonly projectUid: string;
  readonly documentUid: string;
  readonly versionUid: string;
  readonly runId: string;
}): SegmentValues {
  return {
    project_uid: identities.projectUid,
    document_uid: identities.documentUid,
    version_uid: identities.versionUid,
    run_id: identities.runId,
    user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
  };
}

/**
 * The one value used for "this segment is not an identifier", in every instrument.
 *
 * **Cyrillic, and that is not decoration.** `rendered-language.guard.test.ts` renders
 * these variants and judges every Latin word left on the markup as chrome the application
 * authored — its whole allowlist design rests on *"every value this file seeds is
 * Cyrillic, or an identifier, or a contract enum"*. The hand-written bad-address entries
 * this replaces seeded the Latin string `not-an-identifier`, which was invisible only
 * because the three screens that used it all refuse and never echo the value. The run and
 * review screens do echo it — they defer the check to their route file — so the first run
 * of the derived variants reported `not-an-identifier` as English on a rendered screen.
 * The guard was right and the seed was wrong.
 */
export const MALFORMED_SEGMENT = 'это-не-идентификатор';

export interface DerivedScreen {
  readonly address: string;
  readonly name: string;
  readonly file: string;
  readonly segments: readonly string[];
  readonly discipline: Readonly<Record<string, SegmentDiscipline>>;
  readonly make: (segments: SegmentValues) => ReactElement;
}

function seedFor(address: string): Seed | undefined {
  return SEEDS.find((seed) => seed.address === address);
}

/**
 * Every rendering seed of every derived address, joined to what the tree says about it — one
 * entry per seed, so an address seeded twice (`/`, for an expert and for an administrator) is
 * rendered twice.
 *
 * An address with no seed is NOT silently dropped: it is reported by `unseededAddresses()`
 * and the guard names it. This function is what the two instruments consume, so a screen
 * that reaches this list reaches both of them in the same commit.
 */
export function derivedScreens(): readonly DerivedScreen[] {
  const out: DerivedScreen[] = [];
  for (const route of routeAddresses()) {
    // Every seed of the address, in `SEEDS` order: `/` has two (`W50-SHELL-FRAME`).
    for (const seed of SEEDS.filter((entry) => entry.address === route.address)) {
      if (seed.make === undefined) continue;
      out.push({
        address: route.address,
        name: seed.name,
        file: route.file,
        segments: route.segments,
        discipline: seed.discipline,
        make: seed.make,
      });
    }
  }
  return out;
}

/** Addresses the tree offers and no seed renders or excuses. The guard names these. */
export function unseededAddresses(): readonly string[] {
  return routeAddresses()
    .filter((route) => seedFor(route.address) === undefined)
    .map((route) => route.address);
}

/** Seeds for addresses the tree no longer offers, so a deleted screen is red too. */
export function staleSeeds(): readonly string[] {
  const addresses = new Set(routeAddresses().map((route) => route.address));
  return SEEDS.filter((seed) => !addresses.has(seed.address)).map((seed) => seed.address);
}

/** The opt-outs, each proof RUN — see `OptedOutSeed.proof` for why not read. */
export function optOuts(): readonly {
  readonly address: string;
  readonly why: string;
  readonly holds: boolean;
}[] {
  const files = new Map(routeAddresses().map((route) => [route.address, route.file]));
  return SEEDS.filter((seed): seed is OptedOutSeed => seed.optOut !== undefined).map((seed) => {
    // The file is still resolved, because an opt-out for an address the tree no longer
    // serves must not quietly pass; `staleSeeds()` is the case that reports it.
    const file = files.get(seed.address);
    return {
      address: seed.address,
      why: seed.optOut.why,
      holds: file !== undefined && seed.optOut.proof(),
    };
  });
}

/**
 * Every (screen, segment) pair, with the value that makes that one segment malformed.
 *
 * The pairs are derived — a new dynamic segment brings its own pair — and the expected
 * discipline is the human's answer, which is what survives the mutation that deletes the
 * condition.
 */
export function malformedVariants(identities: Parameters<typeof wellFormed>[0]): readonly {
  readonly name: string;
  readonly address: string;
  readonly segment: string;
  readonly expected: SegmentDiscipline;
  readonly make: () => ReactElement;
}[] {
  const base = wellFormed(identities);
  const out: {
    name: string;
    address: string;
    segment: string;
    expected: SegmentDiscipline;
    make: () => ReactElement;
  }[] = [];
  for (const screen of derivedScreens()) {
    for (const segment of screen.segments) {
      const expected = screen.discipline[segment];
      if (expected === undefined) continue; // reported by `undisciplinedSegments()`
      out.push({
        name: `${screen.name} (${segment} malformed)`,
        address: screen.address,
        segment,
        expected,
        make: () => screen.make({ ...base, [segment]: MALFORMED_SEGMENT }),
      });
    }
  }
  return out;
}

/** Segments the tree has and no seed answered for, and answers for segments that are gone. */
export function undisciplinedSegments(): readonly string[] {
  const out: string[] = [];
  for (const screen of derivedScreens()) {
    for (const segment of screen.segments) {
      if (screen.discipline[segment] === undefined) {
        out.push(`${screen.address} has a segment [${segment}] and its seed answers for none`);
      }
    }
    for (const declared of Object.keys(screen.discipline)) {
      if (!screen.segments.includes(declared)) {
        out.push(`${screen.address} answers for [${declared}], which its address does not have`);
      }
    }
  }
  return out;
}
