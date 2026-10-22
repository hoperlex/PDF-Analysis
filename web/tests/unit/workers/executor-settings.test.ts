/**
 * `EXEC-HTTP-01` — the settings of a revision: what a form may send, and whether saving it
 * moves the key.
 *
 * Pure functions over `FormData`, which Node has. The server checks every rule again; what is
 * pinned here is what a person can fix before pressing the button, the shape of the request
 * (the full settings, never a patch, and no field the kind does not take), and the one warning
 * that matters: the key opens only for the destination it was entered for.
 */

import { describe, expect, it } from 'vitest';

import type { ExecutorKind, ExecutorRevision } from '@/shared/api';
import { destinationChanged, destinationOf, normalisedOrigin, sshEndpointOf } from '@/entities/executor-connection';
import { draftMovesTheKey, initialSettings, readRevision, requestFromRevision } from '@/features/manage-executor-connection';

import { PINNED, READY, revision } from './executor-fixtures';

function form(fields: Record<string, string | boolean>): FormData {
  const data = new FormData();
  for (const [name, value] of Object.entries(fields)) {
    if (value === true) data.set(name, 'on');
    else if (value !== false) data.set(name, value);
  }
  return data;
}

const COMMON = {
  pin_id: 'модель-основная', gateway_model: 'шлюзовая-основная', billing: 'metered', timeout_seconds: '120',
};
const HTTP = {
  ...COMMON, api_flavour: 'openai_chat', base_url: 'https://шлюз.example/api/v1', transport: 'direct', max_parallel_calls: '2',
};
const SSH = {
  ...COMMON, ssh_profile: 'claude_code_headless', ssh_host: 'node.example', ssh_port: '22', ssh_user: 'runner',
};
const PULL = { ...COMMON, pull_client: 'agent', answer_deadline_seconds: '600', max_claimed_tasks: '2' };

function read(kind: ExecutorKind, fields: Record<string, string | boolean>) {
  return readRevision(kind, form(fields), PINNED);
}

describe('reading a revision out of a form', () => {
  it('builds the full http_api request, with the checkbox read as a boolean', () => {
    const reading = read('http_api', { ...HTTP, allow_client_documents: true });
    expect(reading).toEqual({
      ok: true,
      body: {
        pin_id: 'модель-основная', gateway_model: 'шлюзовая-основная', billing: 'metered',
        allow_client_documents: true, timeout_seconds: 120,
        api_flavour: 'openai_chat', base_url: 'https://шлюз.example/api/v1', transport: 'direct', max_parallel_calls: 2,
      },
    });
    const unticked = read('http_api', HTTP);
    expect(unticked.ok && unticked.body.allow_client_documents).toBe(false);
  });

  it('takes the SSH endpoint for a tunnel and leaves it out for a direct connection', () => {
    const tunnel = read('http_api', { ...HTTP, transport: 'ssh_tunnel', ssh_host: 'node.example', ssh_port: '2222', ssh_user: 'tunnel' });
    expect(tunnel.ok && tunnel.body).toMatchObject({ transport: 'ssh_tunnel', ssh_host: 'node.example', ssh_port: 2222 });
    const direct = read('http_api', { ...HTTP, ssh_host: 'node.example', ssh_port: '22', ssh_user: 'x' });
    expect(direct.ok && 'ssh_host' in direct.body).toBe(false);
  });

  it('builds the ssh_command request, with the host key only when one is given', () => {
    const bare = read('ssh_command', SSH);
    expect(bare.ok && bare.body).toMatchObject({ ssh_profile: 'claude_code_headless', ssh_port: 22 });
    expect(bare.ok && 'host_key' in bare.body).toBe(false);
    expect(bare.ok && 'api_flavour' in bare.body).toBe(false);
    const pinned = read('ssh_command', { ...SSH, host_key: 'отпечаток' });
    expect(pinned.ok && pinned.body.host_key).toBe('отпечаток');
  });

  it('builds the pull request with no field of another kind', () => {
    const reading = read('pull', PULL);
    expect(reading.ok && reading.body).toEqual({
      pin_id: 'модель-основная', gateway_model: 'шлюзовая-основная', billing: 'metered',
      allow_client_documents: false, timeout_seconds: 120,
      pull_client: 'agent', answer_deadline_seconds: 600, max_claimed_tasks: 2,
    });
  });

  const problems: ReadonlyArray<readonly [string, ExecutorKind, Record<string, string | boolean>, string]> = [
    ['an unpinned model', 'http_api', { ...HTTP, pin_id: 'чужая-модель' }, 'Выберите модель из списка закреплённых.'],
    ['no gateway name', 'http_api', { ...HTTP, gateway_model: '  ' }, 'Укажите имя модели на шлюзе: до 200 символов.'],
    ['a timeout of zero', 'http_api', { ...HTTP, timeout_seconds: '0' }, 'Время ожидания: целое число секунд от 1 до 3600.'],
    ['a timeout past the bound', 'http_api', { ...HTTP, timeout_seconds: '3601' }, 'Время ожидания: целое число секунд от 1 до 3600.'],
    ['a fractional timeout', 'http_api', { ...HTTP, timeout_seconds: '1.5' }, 'Время ожидания: целое число секунд от 1 до 3600.'],
    ['an address without a scheme', 'http_api', { ...HTTP, base_url: 'шлюз.example' }, 'Адрес: нужен адрес вида https://узел или https://узел:порт без пробелов.'],
    ['an address with a space', 'http_api', { ...HTTP, base_url: 'https://шлюз.example/a b' }, 'Адрес: нужен адрес вида https://узел или https://узел:порт без пробелов.'],
    ['parallel calls past the bound', 'http_api', { ...HTTP, max_parallel_calls: '17' }, 'Параллельных вызовов: целое число от 1 до 16.'],
    ['an unknown way of connecting', 'http_api', { ...HTTP, transport: 'carrier' }, 'Выберите способ связи.'],
    ['a tunnel without a user', 'http_api', { ...HTTP, transport: 'ssh_tunnel', ssh_host: 'node.example', ssh_port: '22', ssh_user: '' }, 'Пользователь SSH: латинские буквы, цифры, точка, дефис и подчёркивание.'],
    ['a port of zero', 'ssh_command', { ...SSH, ssh_port: '0' }, 'Порт SSH: целое число от 1 до 65535.'],
    ['a host with a space', 'ssh_command', { ...SSH, ssh_host: 'узел example' }, 'Узел SSH: имя или адрес узла без пробелов.'],
    ['no profile', 'ssh_command', { ...SSH, ssh_profile: '' }, 'Выберите профиль команды.'],
    ['an answer deadline of nine', 'pull', { ...PULL, answer_deadline_seconds: '9' }, 'Срок ответа: целое число секунд от 10 до 3600.'],
    ['seventeen claimed tasks', 'pull', { ...PULL, max_claimed_tasks: '17' }, 'Заданий в работе: целое число от 1 до 16.'],
  ];
  for (const [name, kind, fields, problem] of problems) {
    it(`refuses ${name} with a sentence next to the field, sending nothing`, () => {
      expect(read(kind, fields)).toEqual({ ok: false, problem });
    });
  }
});

describe('the destination a key is bound to', () => {
  it('is the transport, the SSH endpoint where it applies, and the normalised origin', () => {
    expect(destinationOf({ base_url: 'HTTPS://Gateway.Example/api/v1', transport: 'direct' })).toBe('direct||https://gateway.example:443');
    expect(destinationOf({ base_url: 'http://10.0.0.5:8000', transport: 'vpn' })).toBe('vpn||http://10.0.0.5:8000');
    expect(destinationOf({ base_url: 'http://localhost:11434', transport: 'ssh_tunnel', ssh_host: 'Node.Example', ssh_port: 22 }))
      .toBe('ssh_tunnel|node.example:22|http://localhost:11434');
    expect(sshEndpointOf({ ssh_host: 'Host', ssh_port: 2200 })).toBe('host:2200');
    expect(normalisedOrigin('ftp://x')).toBeNull();
    expect(normalisedOrigin(undefined)).toBeNull();
  });

  it('says the key moves when the origin, the way of connecting or the tunnel changes, and only then', () => {
    const base = { base_url: 'https://gateway.example/api/v1', transport: 'direct' as const };
    expect(destinationChanged('http_api', base, { ...base, base_url: 'https://gateway.example:443/other/path' })).toBe(false);
    expect(destinationChanged('http_api', base, { ...base, base_url: 'https://gateway.example:8443/api/v1' })).toBe(true);
    expect(destinationChanged('http_api', base, { ...base, base_url: 'http://gateway.example/api/v1' })).toBe(true);
    expect(destinationChanged('http_api', base, { ...base, transport: 'vpn' })).toBe(true);
    const tunnel = { base_url: 'http://localhost:11434', transport: 'ssh_tunnel' as const, ssh_host: 'a', ssh_port: 22 };
    expect(destinationChanged('http_api', tunnel, { ...tunnel, ssh_host: 'b' })).toBe(true);
    expect(destinationChanged('http_api', tunnel, { ...tunnel })).toBe(false);
    expect(destinationChanged('ssh_command', { ssh_host: 'a', ssh_port: 22 }, { ssh_host: 'a', ssh_port: 2200 })).toBe(true);
    expect(destinationChanged('pull', {}, { base_url: 'https://x' })).toBe(false);
  });

  it('warns while the draft is typed: a new address moves the key, a new model does not', () => {
    const current = READY.detail.revisions[0] as ExecutorRevision;
    const same = { ...HTTP, base_url: current.base_url as string, max_parallel_calls: String(current.max_parallel_calls) };
    expect(draftMovesTheKey('http_api', current, form(same), PINNED)).toBe(false);
    expect(draftMovesTheKey('http_api', current, form({ ...same, pin_id: 'модель-быстрая' }), PINNED)).toBe(false);
    expect(draftMovesTheKey('http_api', current, form({ ...same, base_url: 'https://другой.example/api' }), PINNED)).toBe(true);
    expect(draftMovesTheKey('http_api', current, form({ ...same, transport: 'vpn' }), PINNED)).toBe(true);
    // A draft that does not read yet says nothing.
    expect(draftMovesTheKey('http_api', current, form({ ...same, base_url: 'не адрес' }), PINNED)).toBe(false);
  });
});

describe('starting a form, and changing one field of a revision', () => {
  it('starts a new connection from the first pinned model, metered, documents off', () => {
    const start = initialSettings(undefined, PINNED);
    expect(start).toMatchObject({
      pinId: 'модель-основная', gatewayModel: 'модель-основная', billing: 'metered',
      allowClientDocuments: false, timeoutSeconds: 120, maxParallelCalls: 1, transport: 'direct', sshPort: 22,
    });
    expect(initialSettings(undefined, []).pinId).toBe('');
  });

  it('starts a revision from the current one', () => {
    const current = revision({ connection_id: READY.connection.connection_id, revision_id: 'excr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', billing: 'not_metered', timeout_seconds: 30 });
    expect(initialSettings(current, PINNED)).toMatchObject({ billing: 'not_metered', timeoutSeconds: 30 });
  });

  it('keeps every other setting when one is changed, and carries none of the identity', () => {
    const current = READY.detail.revisions[0] as ExecutorRevision;
    const request = requestFromRevision(current, { host_key: 'новый-отпечаток' });
    expect(request).toMatchObject({ host_key: 'новый-отпечаток', base_url: current.base_url, pin_id: current.pin_id });
    for (const identity of ['revision_id', 'revision_no', 'created_at', 'created_by', 'connection_id', 'latest_probe', 'host_key_fingerprint']) {
      expect(identity in request, identity).toBe(false);
    }
  });
});
