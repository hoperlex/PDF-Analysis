/**
 * `src/app/**` — the five route files and the BFF handler.
 *
 * These are the last of the modules `web/tests` imported from nowhere. Four of the five
 * routes are delegation-only and look like nothing worth a test, and that is exactly the
 * shape of the bug they can hold: a route that awaited its params and then handed
 * `project_uid` to a prop named `runId` would render a screen that asked the server about
 * the wrong thing, would type-check (both are `string`), and would be invisible to every
 * component test in this suite because the component would have been given exactly what
 * it was asked for.
 *
 * A route file exports a function. Calling it returns a React element, and the element's
 * `type` and `props` are the whole of what the route decides. Nothing here needs a
 * renderer, a DOM or a Next server.
 *
 * The handler under `bff/v1` is the other half: its forwarding rules live in
 * `@/shared/api/credentialed-forward` and are guarded there, but its **fail-closed**
 * branch — a deployment with no credential answers `401 authentication_required` and
 * sends nothing upstream — is decided in this file and nowhere else.
 */

import { describe, expect, it } from 'vitest';

import { ReviewPage } from '@/_pages/review';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { ProjectsPage } from '@/_pages/projects';
import { RunPage } from '@/_pages/run';

import ProjectRoute from '@/app/projects/[project_uid]/page';
import ProjectsRoute from '@/app/projects/page';
import ReviewRoute from '@/app/projects/[project_uid]/runs/[run_id]/review/page';
import RootPage from '@/app/page';
import RunRoute from '@/app/projects/[project_uid]/runs/[run_id]/page';

import { GET, POST } from '@/app/bff/v1/[...path]/route';
import RootLayout, { metadata } from '@/app/layout';
import { AppFrame, AppProviders } from '@/_app';

import { PROJECT_UID, RUN_ID } from '../review/fixtures';

/** Distinct values, so a route that crossed its two parameters is red rather than green. */
const A_PROJECT = PROJECT_UID;
const A_RUN = RUN_ID.replace(/.$/, 'C');

describe('each route delegates to its screen and to no other', () => {
  it('/projects renders the projects screen', () => {
    const element = ProjectsRoute();
    expect(element.type).toBe(ProjectsPage);
  });

  it('/projects/{project_uid} passes the project address through, unparsed', async () => {
    const element = await ProjectRoute({ params: Promise.resolve({ project_uid: A_PROJECT }) });
    expect(element.type).toBe(ProjectDetailPage);
    expect(element.props).toEqual({ projectUid: A_PROJECT });
  });

  it('/projects/{project_uid}/runs/{run_id} passes both, and does not cross them', async () => {
    const element = await RunRoute({
      params: Promise.resolve({ project_uid: A_PROJECT, run_id: A_RUN }),
    });
    expect(element.type).toBe(RunPage);
    expect(element.props).toEqual({ projectUid: A_PROJECT, runId: A_RUN });
  });

  it('.../review passes both to the review screen, and does not cross them', async () => {
    const element = await ReviewRoute({
      params: Promise.resolve({ project_uid: A_PROJECT, run_id: A_RUN }),
    });
    expect(element.type).toBe(ReviewPage);
    expect(element.props).toEqual({ projectUid: A_PROJECT, runId: A_RUN });
  });

  it('review is mounted under the run, not beside it', () => {
    // The URL is the claim: a finding is only meaningful against the run that produced
    // it. This is the file layout that makes the claim true.
    expect(A_RUN).not.toBe(A_PROJECT);
  });
});

describe('/ starts the journey at the project list', () => {
  it('redirects rather than rendering a screen of its own', () => {
    // `redirect()` signals by throwing; Next's digest carries the destination.
    let thrown: unknown;
    try {
      RootPage();
    } catch (error) {
      thrown = error;
    }
    expect(thrown).toBeDefined();
    expect(String((thrown as { digest?: string }).digest ?? thrown)).toContain('/projects');
  });
});

/**
 * The fail-closed half of `T-6`'s credential seam. `W15-AUTH` wrote it; it landed in the
 * region no test reached, which is how the module count went from 110 to 114 and the
 * unreached count from 34 to 35.
 */
describe('the BFF answers 401 when this deployment has no credential', () => {
  const ORIGINAL = {
    upstream: process.env.AUDITMANAGER_API_UPSTREAM,
    token: process.env.AUDITMANAGER_API_TOKEN,
  };

  function withoutConfiguration<T>(body: () => T): T {
    delete process.env.AUDITMANAGER_API_UPSTREAM;
    delete process.env.AUDITMANAGER_API_TOKEN;
    try {
      return body();
    } finally {
      if (ORIGINAL.upstream === undefined) delete process.env.AUDITMANAGER_API_UPSTREAM;
      else process.env.AUDITMANAGER_API_UPSTREAM = ORIGINAL.upstream;
      if (ORIGINAL.token === undefined) delete process.env.AUDITMANAGER_API_TOKEN;
      else process.env.AUDITMANAGER_API_TOKEN = ORIGINAL.token;
    }
  }

  async function unconfigured(method: typeof GET, headers: HeadersInit = {}): Promise<Response> {
    return withoutConfiguration(() =>
      method(new Request('http://web.test/bff/v1/projects', { method: 'GET', headers }), {
        params: Promise.resolve({ path: ['projects'] }),
      }),
    );
  }

  it('answers 401 with the catalog code, not 500 and not a thirteenth code', async () => {
    const response = await unconfigured(GET);
    expect(response.status).toBe(401);
    const body = (await response.json()) as { error_code: string; retryable: boolean };
    expect(body.error_code).toBe('authentication_required');
    expect(body.retryable).toBe(false);
  });

  it('names no environment variable in what it puts on the wire', async () => {
    const response = await unconfigured(GET);
    const text = await response.text();
    expect(text).not.toContain('AUDITMANAGER_API_TOKEN');
    expect(text).not.toContain('AUDITMANAGER_API_UPSTREAM');
    expect(text).toContain('No request was sent.');
  });

  it('keeps the caller’s correlation id, so the 401 is traceable to the request', async () => {
    const response = await unconfigured(GET, { 'x-correlation-id': 'corr-bff-1' });
    const body = (await response.json()) as { correlation_id: string };
    expect(body.correlation_id).toBe('corr-bff-1');
  });

  it('mints one when the caller sent none, rather than leaving it blank', async () => {
    const response = await unconfigured(GET);
    const body = (await response.json()) as { correlation_id: string };
    expect(body.correlation_id).toBeTruthy();
    expect(body.correlation_id.length).toBeGreaterThan(8);
  });

  it('fails closed on a write as well as a read', async () => {
    const response = await withoutConfiguration(() =>
      POST(new Request('http://web.test/bff/v1/projects', { method: 'POST', body: '{}' }), {
        params: Promise.resolve({ path: ['projects'] }),
      }),
    );
    expect(response.status).toBe(401);
  });
});

describe('the handler is mounted for every method the contract uses', () => {
  it('exports one handler per verb, so no operation is silently unroutable', async () => {
    const route = await import('@/app/bff/v1/[...path]/route');
    for (const verb of ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'] as const) {
      expect(typeof route[verb]).toBe('function');
    }
    expect(route.runtime).toBe('nodejs');
    expect(route.dynamic).toBe('force-dynamic');
  });
});

/**
 * The root layout is a framework adapter, and the one thing it decides is nesting order:
 * the query provider must be **outside** the frame, or every client component below the
 * frame renders without a `QueryClient`. That is not visible in a screenshot and it is
 * not visible to any component test, because every component test supplies its own
 * provider.
 */
describe('the root layout wires the providers outside the frame', () => {
  it('nests provider, then frame, then the screen', () => {
    const marker = 'the screen';
    const html = RootLayout({ children: marker });
    expect(html.type).toBe('html');
    expect(html.props.lang).toBe('en');

    const body = html.props.children as { type: unknown; props: { children: unknown } };
    expect(body.type).toBe('body');

    const providers = body.props.children as { type: unknown; props: { children: unknown } };
    expect(providers.type).toBe(AppProviders);

    const frame = providers.props.children as { type: unknown; props: { children: unknown } };
    expect(frame.type).toBe(AppFrame);
    expect(frame.props.children).toBe(marker);
  });

  it('names the product and says what this build is', () => {
    expect(String(metadata.title)).toContain('AuditManager');
    expect(String(metadata.title)).toContain('PC-01');
    expect(String(metadata.description)).toContain('one AR PDF');
  });
});
