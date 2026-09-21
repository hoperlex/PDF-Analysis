/**
 * 401 and 403 as states the UI can show, on every screen that can receive one.
 *
 * Before `W15-AUTH` this file could not have been written: no classifier had a branch for
 * either code, so all five fell through to `default` and reported a refused credential as
 * "the request failed on the server". After wave 13 put the seam in front of all twelve
 * operations and wave 14 deployed it, that default was reachable from every screen.
 *
 * The end of this file is the part that matters: a real 401 response, decoded by the real
 * transport, classified by each real classifier. Everything above it is one classifier at
 * a time; that section is the path an operator's browser actually takes.
 *
 * Titles and details are pinned as literals. §12 of `OPERATING_CONSTRAINTS.md`: asserting
 * `failure.detail === AUTHENTICATION_REQUIRED_DETAIL` would share the constant with the
 * subject and would pass over an empty string.
 */

import { describe, expect, it } from 'vitest';

import { classifyRunFailure } from '@/entities/audit-run';
import { classifyUploadFailure } from '@/entities/document-version';
import { classifyCreateProjectFailure, classifyProjectListFailure } from '@/entities/project';
import { presentFailure } from '@/_pages/review';
import type { ErrorEnvelope } from '@/shared/api';
import {
  AUTHENTICATION_REQUIRED_DETAIL,
  ApiError,
  OPERATIONS,
  PERMISSION_DENIED_DETAIL,
  isAuthorizationErrorCode,
  isAuthorizationFailure,
  request,
} from '@/shared/api';

const UNAUTHENTICATED_MESSAGE =
  'No valid authenticated subject was presented. The response carries no hint about the ' +
  'addressed resource.';

function envelope(
  code: ErrorEnvelope['error_code'],
  message: string,
  details?: ErrorEnvelope['details'],
): ErrorEnvelope {
  return {
    contract_version: '1.0.0-draft.1',
    correlation_id: 'cid-7f1c',
    error_code: code,
    message,
    retryable: false,
    ...(details === undefined ? {} : { details }),
  };
}

const unauthenticated = () =>
  new ApiError(401, envelope('authentication_required', UNAUTHENTICATED_MESSAGE), 'cid-7f1c');

const forbidden = (details?: ErrorEnvelope['details']) =>
  new ApiError(
    403,
    envelope(
      'permission_denied',
      'The authenticated subject is not permitted to perform this operation on this resource.',
      details,
    ),
    'cid-7f1c',
  );

// ----------------------------------------------------------------------------------------
// The two codes, named once

describe('the authorization codes are the catalog’s, and are recognised as a pair', () => {
  it('is exactly authentication_required and permission_denied', () => {
    expect(isAuthorizationErrorCode('authentication_required')).toBe(true);
    expect(isAuthorizationErrorCode('permission_denied')).toBe(true);
    expect(isAuthorizationErrorCode('not_found')).toBe(false);
    expect(isAuthorizationErrorCode('dependency_unavailable')).toBe(false);
  });

  it('recognises a thrown ApiError carrying either, and nothing else', () => {
    expect(isAuthorizationFailure(unauthenticated())).toBe(true);
    expect(isAuthorizationFailure(forbidden())).toBe(true);
    expect(isAuthorizationFailure(new ApiError(404, envelope('not_found', 'no'), null))).toBe(false);
    expect(isAuthorizationFailure(new Error('something'))).toBe(false);
  });

  it('says what the operator can act on, and says retrying will not help', () => {
    expect(AUTHENTICATION_REQUIRED_DETAIL).toContain('не принял учётные данные');
    expect(AUTHENTICATION_REQUIRED_DETAIL).toContain('не настроены');
    expect(AUTHENTICATION_REQUIRED_DETAIL).toContain('повтор отправит те же учётные данные');
    expect(PERMISSION_DENIED_DETAIL).toContain('Учётные данные приняты');
    expect(PERMISSION_DENIED_DETAIL).toContain('эта операция над этим ресурсом им не разрешена');
  });
});

// ----------------------------------------------------------------------------------------
// One screen at a time

describe('starting or watching a run', () => {
  it('reports a 401 as not authenticated, not as a server error', () => {
    const failure = classifyRunFailure(unauthenticated());
    expect(failure.kind).toBe('not_authenticated');
    expect(failure.title).toBe('Этот прогон не авторизован.');
    expect(failure.detail).toBe(
      'API не принял учётные данные для этого запроса. Либо в этом развёртывании они не ' +
        'настроены, либо предъявляемые API не принимает. Ничего не применено, и повтор ' +
        'отправит те же учётные данные к тому же отказу.',
    );
    expect(failure.retryable).toBe(false);
    expect(failure.errorCode).toBe('authentication_required');
    expect(failure.correlationId).toBe('cid-7f1c');
  });

  it('reports a 403 as not permitted, with the safe classifiers the catalog allows', () => {
    const failure = classifyRunFailure(
      forbidden({ aggregate_type: 'AuditRun', required_capability: 'run:start' }),
    );
    expect(failure.kind).toBe('not_permitted');
    expect(failure.title).toBe('Вам не разрешено действовать с этим прогоном.');
    expect(failure.detail).toContain('(aggregate_type: AuditRun, required_capability: run:start)');
  });
});

describe('creating a project', () => {
  it('reports a 401 as not authenticated', () => {
    const failure = classifyCreateProjectFailure(unauthenticated());
    expect(failure.kind).toBe('not_authenticated');
    expect(failure.title).toBe('Создание проекта не авторизовано.');
    expect(failure.retryable).toBe(false);
  });

  it('reports a 403 as not permitted', () => {
    const failure = classifyCreateProjectFailure(forbidden());
    expect(failure.kind).toBe('not_permitted');
    expect(failure.title).toBe('Вам не разрешено создавать проект.');
  });
});

describe('reading the project list', () => {
  it('reports a 401 as not authenticated', () => {
    const failure = classifyProjectListFailure(unauthenticated());
    expect(failure.kind).toBe('not_authenticated');
    expect(failure.title).toBe('Чтение списка проектов не авторизовано.');
    expect(failure.retryable).toBe(false);
  });

  it('reports a 403 as not permitted', () => {
    expect(classifyProjectListFailure(forbidden()).kind).toBe('not_permitted');
  });
});

describe('uploading a document', () => {
  it('reports a 401 as not authenticated', () => {
    const failure = classifyUploadFailure(unauthenticated());
    expect(failure.kind).toBe('not_authenticated');
    expect(failure.title).toBe('Загрузка не авторизована.');
    expect(failure.presentation).toBe('error');
  });

  it('reports a 403 as not permitted', () => {
    const failure = classifyUploadFailure(forbidden());
    expect(failure.kind).toBe('not_permitted');
    expect(failure.title).toBe('Вам не разрешено загружать в этот проект.');
  });
});

describe('the review screen', () => {
  it('shows the authorization sentence and never the envelope message with the code', () => {
    const props = presentFailure(unauthenticated(), { title: 'Findings could not be read.' });
    expect(props.title).toBe('Findings could not be read.');
    expect(props.detail).toBe(
      'API не принял учётные данные для этого запроса. Либо в этом развёртывании они не ' +
        'настроены, либо предъявляемые API не принимает. Ничего не применено, и повтор ' +
        'отправит те же учётные данные к тому же отказу.',
    );
    // Not the generic `${code}: ${message}` shape the default branch produces.
    expect(props.detail).not.toContain('authentication_required:');
    expect(props.correlationId).toBe('cid-7f1c');
  });

  it('offers no retry button even when the caller passed one', () => {
    let retried = 0;
    const props = presentFailure(unauthenticated(), {
      title: 'Findings could not be read.',
      onRetry: () => {
        retried += 1;
      },
      retryLabel: 'Повторить',
    });
    expect(props.onRetry).toBeUndefined();
    expect(retried).toBe(0);
    expect(presentFailure(forbidden(), { title: 'x', onRetry: () => {} }).onRetry).toBeUndefined();
  });
});

// ----------------------------------------------------------------------------------------
// The whole path: a real 401 response, the real transport, the real classifiers

describe('a 401 from the wire reaches the screen as a 401', () => {
  const body = JSON.stringify(envelope('authentication_required', UNAUTHENTICATED_MESSAGE));

  const refusing = () =>
    Promise.resolve(
      new Response(body, {
        status: 401,
        headers: { 'content-type': 'application/json', 'x-correlation-id': 'cid-7f1c' },
      }),
    );

  it('decodes to an ApiError the classifiers name, on a read and on a write', async () => {
    const read = await request(OPERATIONS.listProjects, {}, { baseUrl: '/bff/v1', fetch: refusing })
      .then(() => null)
      .catch((error: unknown) => error);
    expect(read).toBeInstanceOf(ApiError);
    expect((read as ApiError).status).toBe(401);
    expect(classifyProjectListFailure(read).kind).toBe('not_authenticated');

    const write = await request(
      OPERATIONS.createProject,
      { body: { name: 'x' }, idempotencyKey: 'idem-1' },
      { baseUrl: '/bff/v1', fetch: refusing },
    )
      .then(() => null)
      .catch((error: unknown) => error);
    expect(write).toBeInstanceOf(ApiError);
    expect(classifyCreateProjectFailure(write).kind).toBe('not_authenticated');
  });

  it('is a state on every one of the fifteen operations, because the seam is on all fifteen', () => {
    const ids = Object.keys(OPERATIONS);
    expect(ids).toHaveLength(15);
    for (const id of ids) {
      const descriptor = OPERATIONS[id as keyof typeof OPERATIONS];
      expect([...descriptor.errorStatuses], `${id} cannot return 401`).toContain(401);
      expect([...descriptor.errorStatuses], `${id} cannot return 403`).toContain(403);
    }
  });
});
