/**
 * The server-only configuration, and the `/bff/v1` route handler's fail-closed answer.
 *
 * The property this file exists for is the one that cannot be seen by reading the route
 * handler: a deployment with no credential answers the same `401 authentication_required`
 * the API answers when handed none, so the operator lands on the state the UI now has
 * rather than on a Next error page.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { MissingConfigurationError } from '@/shared/config';
import {
  API_TOKEN_VARIABLE,
  API_UPSTREAM_VARIABLE,
  SERVER_ONLY_VARIABLES,
  getApiToken,
  getApiUpstreamUrl,
  hasServerCredential,
} from '@/shared/config/server-env';

const SAVED = { ...process.env };

beforeEach(() => {
  delete process.env.AUDITMANAGER_API_TOKEN;
  delete process.env.AUDITMANAGER_API_UPSTREAM;
});

afterEach(() => {
  process.env = { ...SAVED };
});

describe('the credential is read from names Next never inlines', () => {
  it('names exactly the two server-side variables, neither of them NEXT_PUBLIC_', () => {
    expect([...SERVER_ONLY_VARIABLES]).toEqual([
      'AUDITMANAGER_API_UPSTREAM',
      'AUDITMANAGER_API_TOKEN',
    ]);
    expect(API_TOKEN_VARIABLE).toBe('AUDITMANAGER_API_TOKEN');
    expect(API_UPSTREAM_VARIABLE).toBe('AUDITMANAGER_API_UPSTREAM');
    for (const name of SERVER_ONLY_VARIABLES) {
      expect(name.startsWith('NEXT_PUBLIC_')).toBe(false);
    }
  });

  it('refuses to default the token, and names the variable when it does', () => {
    expect(() => getApiToken()).toThrow(MissingConfigurationError);
    try {
      getApiToken();
    } catch (error) {
      expect((error as MissingConfigurationError).variable).toBe('AUDITMANAGER_API_TOKEN');
    }
  });

  it('refuses a blank token, which is how an unset compose variable arrives', () => {
    process.env.AUDITMANAGER_API_TOKEN = '   ';
    expect(() => getApiToken()).toThrow(MissingConfigurationError);
  });

  it('returns the token with surrounding whitespace removed', () => {
    process.env.AUDITMANAGER_API_TOKEN = '  s3cret-value  ';
    expect(getApiToken()).toBe('s3cret-value');
  });

  it('refuses to default the upstream', () => {
    expect(() => getApiUpstreamUrl()).toThrow(MissingConfigurationError);
  });

  it('refuses a relative upstream, which would make the server forward to itself', () => {
    process.env.AUDITMANAGER_API_UPSTREAM = '/api/v1';
    expect(() => getApiUpstreamUrl()).toThrow(MissingConfigurationError);
  });

  it('refuses a scheme this forwarder does not speak', () => {
    process.env.AUDITMANAGER_API_UPSTREAM = 'file:///etc/passwd';
    expect(() => getApiUpstreamUrl()).toThrow(MissingConfigurationError);
  });

  it('accepts an absolute origin and strips a trailing slash', () => {
    process.env.AUDITMANAGER_API_UPSTREAM = 'http://api:8000/';
    expect(getApiUpstreamUrl()).toBe('http://api:8000');
    process.env.AUDITMANAGER_API_UPSTREAM = 'https://api.example.test/api/v1';
    expect(getApiUpstreamUrl()).toBe('https://api.example.test/api/v1');
  });

  it('reports both present or not, without deciding anything', () => {
    expect(hasServerCredential()).toBe(false);
    process.env.AUDITMANAGER_API_TOKEN = 'x';
    expect(hasServerCredential()).toBe(false);
    process.env.AUDITMANAGER_API_UPSTREAM = 'http://api:8000';
    expect(hasServerCredential()).toBe(true);
  });
});

describe('an unconfigured deployment answers the contract, not a stack trace', () => {
  it('serves 401 authentication_required with no credential configured', async () => {
    const { GET } = await import('@/app/bff/v1/[...path]/route');
    const response = await GET(new Request('http://localhost/bff/v1/projects'), {
      params: Promise.resolve({ path: ['projects'] }),
    });
    expect(response.status).toBe(401);
    const body = (await response.json()) as {
      error_code: string;
      retryable: boolean;
      contract_version: string;
      message: string;
      correlation_id: string;
    };
    expect(body.error_code).toBe('authentication_required');
    expect(body.retryable).toBe(false);
    expect(body.contract_version).toBe('1.0.0-draft.1');
    // The refusal must not name the environment variable: a variable name on a public
    // response is a hint about the deployment that nothing outside needs.
    expect(body.message).not.toContain('AUDITMANAGER_API_TOKEN');
    expect(body.message).not.toContain('AUDITMANAGER_API_UPSTREAM');
    expect(body.correlation_id).toMatch(/^web-[0-9a-f]{32}$/);
  });

  it('echoes a correlation id the browser supplied, so one request has one id', async () => {
    const { POST } = await import('@/app/bff/v1/[...path]/route');
    const response = await POST(
      new Request('http://localhost/bff/v1/projects', {
        method: 'POST',
        headers: { 'x-correlation-id': 'cid-browser-supplied' },
      }),
      { params: Promise.resolve({ path: ['projects'] }) },
    );
    expect(response.status).toBe(401);
    expect(response.headers.get('x-correlation-id')).toBe('cid-browser-supplied');
  });

  it('answers every method the twelve operations use', async () => {
    const route = await import('@/app/bff/v1/[...path]/route');
    expect(typeof route.GET).toBe('function');
    expect(typeof route.POST).toBe('function');
    expect(typeof route.PUT).toBe('function');
    expect(typeof route.PATCH).toBe('function');
    expect(typeof route.DELETE).toBe('function');
    expect(route.runtime).toBe('nodejs');
    expect(route.dynamic).toBe('force-dynamic');
  });
});
