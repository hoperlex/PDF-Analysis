/**
 * The three write forms and the four PC-01 route screens.
 *
 * These are the rest of the region `web/tests` reached by no import. What one static
 * render pass can see here is the *resting* state of each screen, and the resting state
 * carries real claims: the run control must offer no provider-mode selector, the upload
 * form must refuse to submit before a file is chosen, and a malformed project address
 * must be refused without a request.
 *
 * What it cannot see is any branch behind `useMutation`. A mutation's error lives on a
 * `MutationObserver` created fresh by `useMutation` on each render, with nothing in the
 * `QueryClient` to seed — unlike a query, whose cache entry `./harness.ts` can seed or
 * fault. So the failure branches of these three forms are not reached from here; their
 * classifiers (`classifyUploadFailure`, `classifyCreateProjectFailure`,
 * `classifyRunFailure`) are guarded as functions in `tests/unit/projects` and
 * `tests/unit/run`, and the session report says which of the two that leaves unguarded.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

// `ProjectDetailPage` calls `useRouter()` before it does anything else, and Next's hook
// throws "invariant expected app router to be mounted" with no provider above it. This is
// the context Next's own `<AppRouterProvider>` publishes; supplying it is what lets the
// screen be rendered at all. It is a deep import into `next/dist`, which is why it is
// here in one place and not spread across the suite, and it adds no dependency.
import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

import { queryKeys } from '@/shared/api';
import { AppFrame } from '@/_app';
import { CreateProjectForm } from '@/features/create-project';
import { StartRunControl } from '@/features/start-run';
import { UploadDocumentForm } from '@/features/upload-document';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { ProjectsPage } from '@/_pages/projects';
import { RunPage } from '@/_pages/run';

import { PROJECT_UID, RUN_ID, VERSION_UID, render, runStatus } from '../review/fixtures';
import { newClient, renderWith } from './harness';

// ------------------------------------------------------------------- the forms

describe('the create-project form', () => {
  const form = () => renderWith(newClient(), createElement(CreateProjectForm, {}));

  it('renders a named input and a submit control', () => {
    const markup = form();
    expect(markup).toContain('id="new-project-name"');
    expect(markup).toContain('name="name"');
    expect(markup).toContain('>Create</button>');
  });

  it('claims nothing was created before anything was created', () => {
    const markup = form();
    expect(markup).not.toContain('data-created-project');
    expect(markup).not.toContain('data-create-problem');
  });
});

describe('the upload form', () => {
  const form = () =>
    renderWith(newClient(), createElement(UploadDocumentForm, { projectUid: PROJECT_UID }));

  it('accepts one PDF and says so to the file picker itself', () => {
    const markup = form();
    expect(markup).toContain('type="file"');
    expect(markup).toContain('accept="application/pdf"');
  });

  it('cannot be submitted before a file is chosen', () => {
    // The disabled attribute is the browser-side half of "no request without a file";
    // the `send` guard is the other half and is covered by the wiring guard.
    const markup = form();
    expect(markup).toMatch(/<button[^>]*type="submit"[^>]*disabled/);
  });

  it('says the display title is optional and is never an identity', () => {
    const markup = form();
    expect(markup).toContain('optional; never an identity');
  });

  it('states no refusal before a file has been chosen', () => {
    const markup = form();
    expect(markup).not.toContain('data-precheck-problem');
    expect(markup).not.toContain('data-upload-failure');
  });
});

describe('the start-run control', () => {
  const control = () =>
    renderWith(newClient(), createElement(StartRunControl, { versionUid: VERSION_UID }));

  it('offers one button and no provider-mode selector', () => {
    const markup = control();
    expect(markup).toContain('>Start run</button>');
    expect(markup).not.toContain('<select');
    expect(markup).not.toContain('type="radio"');
    expect(markup).not.toContain('recorded mode instead');
  });

  it('says the provider mode is the deployment’s and is never chosen here', () => {
    expect(control()).toContain('never chosen here');
  });

  it('offers no cancel and no re-run carryover, which PC-01 rules out', () => {
    const markup = control().toLowerCase();
    expect(markup).not.toContain('>cancel<');
    expect(markup).not.toContain('re-run');
  });
});

// ------------------------------------------------------------- the route screens

describe('/projects', () => {
  it('composes the create form and the list under one frame', () => {
    const markup = renderWith(newClient(), createElement(ProjectsPage, {}));
    expect(markup).toContain('>Projects</h1>');
    expect(markup).toContain('id="new-project-name"');
    expect(markup).toContain('All projects');
  });
});

/** A router that records instead of navigating. Nothing in one render pass calls it. */
function stubRouter(pushed: string[]): AppRouterInstance {
  return {
    push: (href: string) => pushed.push(href),
    replace: (href: string) => pushed.push(href),
    back: () => {},
    forward: () => {},
    refresh: () => {},
    prefetch: () => {},
  } as unknown as AppRouterInstance;
}

describe('/projects/{project_uid}', () => {
  const detail = (projectUid: string) =>
    renderWith(
      newClient(),
      createElement(
        AppRouterContext.Provider,
        { value: stubRouter([]) },
        createElement(ProjectDetailPage, { projectUid }),
      ),
    );

  it('refuses a malformed address without asking the server about it', () => {
    const markup = detail('not-a-project-address');
    expect(markup).toContain('That is not a project address.');
    expect(markup).toContain('Nothing was requested.');
    // A malformed address must not reach the upload screen.
    expect(markup).not.toContain('What this accepts');
  });

  it.each(['proj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', 'prj_lowercase', 'prj_', ''])(
    'refuses %s',
    (bad) => {
      expect(detail(bad)).toContain('That is not a project address.');
    },
  );

  it('shows the upload screen for a well-shaped address', () => {
    const markup = detail(PROJECT_UID);
    expect(markup).toContain('What this accepts');
    expect(markup).toContain(PROJECT_UID);
    expect(markup).not.toContain('That is not a project address.');
  });
});

describe('/projects/{project_uid}/runs/{run_id}', () => {
  it('renders run progress under the frame, with a way back to the project', () => {
    const status = runStatus({ state: 'published' });
    const client = newClient();
    client.setQueryData(queryKeys.runs.detail(status.run_id), status);
    const markup = renderWith(
      client,
      createElement(RunPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
    );
    expect(markup).toContain('>Run</h1>');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}"`);
    expect(markup).toContain(`data-run-id="${RUN_ID}"`);
  });
});

describe('the application frame', () => {
  it('carries the product name, the prototype label and the one navigation target', () => {
    const markup = render(createElement(AppFrame, { children: 'the screen' }));
    expect(markup).toContain('AuditManager');
    expect(markup).toContain('PC-01');
    expect(markup).toContain('href="/projects"');
    expect(markup).toContain('the screen');
  });

  it('states what this prototype is not, rather than implying it is more', () => {
    const markup = render(createElement(AppFrame, { children: null }));
    expect(markup).toContain('no authentication');
    expect(markup).toContain('no tenancy');
  });
});
