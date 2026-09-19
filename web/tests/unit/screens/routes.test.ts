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

import { existsSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { WEB_ROOT } from '../../guards/lib/repo';

import { DocumentDetailPage } from '@/_pages/document-detail';
import { ReviewPage } from '@/_pages/review';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { ProjectsPage } from '@/_pages/projects';
import { RunPage } from '@/_pages/run';
import { VersionDetailPage } from '@/_pages/version-detail';

import DocumentRoute from '@/app/projects/[project_uid]/documents/[document_uid]/page';
import ProjectRoute from '@/app/projects/[project_uid]/page';
import VersionRoute from '@/app/projects/[project_uid]/versions/[version_uid]/page';
import ProjectsRoute from '@/app/projects/page';
import ReviewRoute from '@/app/projects/[project_uid]/runs/[run_id]/review/page';
import RootPage from '@/app/page';
import RunRoute from '@/app/projects/[project_uid]/runs/[run_id]/page';

import { GET, POST } from '@/app/bff/v1/[...path]/route';
import RootLayout, { metadata } from '@/app/layout';
import { AppFrame, AppProviders } from '@/_app';

import { routes } from '@/shared/lib';

import { DOCUMENT_UID, PROJECT_UID, RUN_ID, VERSION_UID } from '../review/fixtures';

/** Distinct values, so a route that crossed its two parameters is red rather than green. */
const A_PROJECT = PROJECT_UID;
const A_RUN = RUN_ID.replace(/.$/, 'C');
const A_DOCUMENT = DOCUMENT_UID.replace(/.$/, 'D');
const A_VERSION = VERSION_UID.replace(/.$/, 'E');

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

  it('/projects/{project_uid}/documents/{document_uid} passes both, and does not cross them', async () => {
    const element = await DocumentRoute({
      params: Promise.resolve({ project_uid: A_PROJECT, document_uid: A_DOCUMENT }),
    });
    expect(element.type).toBe(DocumentDetailPage);
    expect(element.props).toEqual({ projectUid: A_PROJECT, documentUid: A_DOCUMENT });
  });

  it('/projects/{project_uid}/versions/{version_uid} passes both, and does not cross them', async () => {
    const element = await VersionRoute({
      params: Promise.resolve({ project_uid: A_PROJECT, version_uid: A_VERSION }),
    });
    expect(element.type).toBe(VersionDetailPage);
    expect(element.props).toEqual({ projectUid: A_PROJECT, versionUid: A_VERSION });
  });

  it('review is mounted under the run, not beside it', () => {
    // The URL is the claim: a finding is only meaningful against the run that produced
    // it. This is the file layout that makes the claim true.
    expect(A_RUN).not.toBe(A_PROJECT);
  });
});

/**
 * `D-28`. A dynamic segment matches any string, so `/projects/<anything>` resolved to the
 * project route and answered **200** while rendering an error state. Only an unrouted
 * *top-level* path 404'd.
 *
 * The consequence is not mainly for users — the screen said the right thing. It is that a
 * journey, a probe or a monitor reading a status code could not tell *"this screen exists
 * and works"* from *"this screen exists and is reporting a failure"*. `W21-E2E`'s
 * committed journey reads the rendered body precisely because of this.
 *
 * `notFound()` signals the same way `redirect()` does — by throwing, with the answer in
 * the digest — so these assert on the throw rather than on a rendered element. Measured on
 * the wire afterwards: `/projects/nonexistent-abc` answers **404** and
 * `/projects/{a real uid}` still answers **200**.
 */
describe('a malformed address is a 404, not a screen reporting a failure', () => {
  const BAD = 'nonexistent-abc';

  it('a malformed project address 404s instead of rendering the project screen', async () => {
    // The digest is how Next carries the answer -- `NEXT_HTTP_ERROR_FALLBACK;404` -- and
    // it is asserted rather than the mere fact of a throw: `redirect()` throws too, and a
    // route that redirected to /projects instead would still be a 307 to an instrument.
    await expect(
      ProjectRoute({ params: Promise.resolve({ project_uid: BAD }) }),
    ).rejects.toMatchObject({ digest: 'NEXT_HTTP_ERROR_FALLBACK;404' });
  });

  it('a malformed run address 404s, for both the run screen and the review screen', async () => {
    for (const route of [RunRoute, ReviewRoute]) {
      await expect(
        route({ params: Promise.resolve({ project_uid: A_PROJECT, run_id: BAD }) }),
      ).rejects.toMatchObject({ digest: expect.stringContaining('404') });
    }
  });

  it('a malformed document or version address 404s', async () => {
    await expect(
      DocumentRoute({ params: Promise.resolve({ project_uid: A_PROJECT, document_uid: BAD }) }),
    ).rejects.toMatchObject({ digest: expect.stringContaining('404') });
    await expect(
      VersionRoute({ params: Promise.resolve({ project_uid: A_PROJECT, version_uid: BAD }) }),
    ).rejects.toMatchObject({ digest: expect.stringContaining('404') });
  });

  it('a malformed PARENT 404s even when the child segment is well formed', async () => {
    // The check is on every segment, not only the last one. A route that validated the
    // run and trusted the project would answer 200 for /projects/nonsense/runs/<real>.
    await expect(
      RunRoute({ params: Promise.resolve({ project_uid: BAD, run_id: A_RUN }) }),
    ).rejects.toMatchObject({ digest: expect.stringContaining('404') });
    await expect(
      VersionRoute({ params: Promise.resolve({ project_uid: BAD, version_uid: A_VERSION }) }),
    ).rejects.toMatchObject({ digest: expect.stringContaining('404') });
  });

  it('a well-formed address is NOT a 404 — the guard is not simply always red', async () => {
    // The other direction, and the reason the delegation tests above still pass: every
    // working screen must keep answering 200. This is the assertion that would catch a
    // shape check inverted or tightened past the contract's own pattern.
    await expect(
      ProjectRoute({ params: Promise.resolve({ project_uid: A_PROJECT }) }),
    ).resolves.toBeDefined();
    await expect(
      ReviewRoute({ params: Promise.resolve({ project_uid: A_PROJECT, run_id: A_RUN }) }),
    ).resolves.toBeDefined();
  });

  it('a well-formed address the server has never heard of is NOT a 404 here', async () => {
    // Deliberate, and the half of D-28 this session did not close. Answering 404 for a
    // resource that does not exist needs the server's answer, which needs a server-side
    // fetch on a screen that fetches on the client. See docs/program/reviews/W22-WEB.md.
    const ABSENT = 'run_00000000000000000000000000';
    await expect(
      RunRoute({ params: Promise.resolve({ project_uid: A_PROJECT, run_id: ABSENT }) }),
    ).resolves.toBeDefined();
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


/**
 * The addresses themselves.
 *
 * `D-16`'s acceptance test is a **fresh tab**: a URL is pasted, nothing is in the client,
 * and the screen renders. Half of that property is the string — a route file that exists
 * at a path nothing ever links to is as unreachable as no route at all. `routes` in
 * `@/shared/lib` is the one place those strings are built, and this is where they are
 * compared to the directory layout on disk rather than to another copy of themselves.
 */
describe('every screen address is built once and matches a route file on disk', () => {
  const ADDRESSES: ReadonlyArray<{ url: string; file: string }> = [
    { url: routes.projects(), file: 'src/app/projects/page.tsx' },
    { url: routes.project(A_PROJECT), file: 'src/app/projects/[project_uid]/page.tsx' },
    {
      url: routes.document(A_PROJECT, A_DOCUMENT),
      file: 'src/app/projects/[project_uid]/documents/[document_uid]/page.tsx',
    },
    {
      url: routes.version(A_PROJECT, A_VERSION),
      file: 'src/app/projects/[project_uid]/versions/[version_uid]/page.tsx',
    },
    { url: routes.run(A_PROJECT, A_RUN), file: 'src/app/projects/[project_uid]/runs/[run_id]/page.tsx' },
    {
      url: routes.review(A_PROJECT, A_RUN),
      file: 'src/app/projects/[project_uid]/runs/[run_id]/review/page.tsx',
    },
  ];

  it.each(ADDRESSES)('$url is served by a file that exists', ({ url, file }) => {
    expect(existsSync(join(WEB_ROOT, file))).toBe(true);
    // The directory layout, turned back into the URL Next serves it at. A route file
    // moved without its builder -- or a builder that spelled a segment differently --
    // makes these two disagree.
    const served = file
      .replace(/^src\/app/, '')
      .replace(/\/page\.tsx$/, '')
      .replace('[project_uid]', A_PROJECT)
      .replace('[document_uid]', A_DOCUMENT)
      .replace('[version_uid]', A_VERSION)
      .replace('[run_id]', A_RUN);
    expect(url).toBe(served);
  });

  it('carries no identity a route file cannot receive', () => {
    // `version_ordinal` is a display and ordering value; the contract refuses it as a path
    // parameter. An address built from one would be an identity invented by the UI.
    for (const { url } of ADDRESSES) expect(url).not.toMatch(/\/\d+(\/|$)/);
  });

  it('gives a document and a version each an address of their own', () => {
    // The sentence this replaces is web/docs/PC01_UI_SEAM.md's "there is no route for a
    // document version", which is D-16.
    expect(routes.document(A_PROJECT, A_DOCUMENT)).toContain(A_DOCUMENT);
    expect(routes.version(A_PROJECT, A_VERSION)).toContain(A_VERSION);
    expect(routes.document(A_PROJECT, A_DOCUMENT)).not.toBe(routes.version(A_PROJECT, A_VERSION));
  });
});
