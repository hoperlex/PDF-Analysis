/**
 * `EXEC2-WEB-WIZARD-01` — «API-провайдер»: the OpenRouter preset, a prefilled `http_api` form
 * (base URL, `openai_chat`, a pinned model), then the key, then the probe.
 *
 * The key is never a JavaScript value here: the wizard sends the person to the server-rendered key
 * form of `features/set-executor-secret` with a link, and the connection's card runs the probe after
 * it. These tests hold the form to that. Written under `R-149d`: not run in EXEC-2. None of these
 * needs a database.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import {
  OPENROUTER_BASE_URL,
  OpenRouterFixedFacts,
  OpenRouterKeyStep,
  OpenRouterSetup,
  agentRevisionRequest,
  openRouterRevisionRequest,
  readIdentity,
} from '@/features/connect-remote-agent';
import { executorSecretScreenUrl } from '@/features/set-executor-secret';
import { BILLING_LABELS, FLAVOUR_LABELS, TRANSPORT_LABELS } from '@/entities/executor-connection';

import { newClient, renderScreen } from '../screens/harness';
import { connectionId } from './executor-fixtures';
import { PINNED } from './connect-remote-agent-fixtures';

const CID = connectionId(67);

const render = (element: Parameters<typeof renderScreen>[1]) => renderScreen(newClient(), element);
const noop = () => undefined;

function form(entries: Record<string, string>): FormData {
  const data = new FormData();
  for (const [name, value] of Object.entries(entries)) data.set(name, value);
  return data;
}

const FIELDS = { display_name: 'OpenRouter', pin_id: 'модель-основная', gateway_model: 'шлюзовая-основная' };

describe('the preset’s settings', () => {
  const identity = { displayName: 'OpenRouter', pinId: 'модель-основная', gatewayModel: 'шлюзовая-основная' };

  it('fills in the gateway’s address, the chat format and a direct connection, metered by the pinned model', () => {
    expect(OPENROUTER_BASE_URL).toBe('https://openrouter.ai/api/v1');
    expect(openRouterRevisionRequest(identity)).toEqual({
      pin_id: 'модель-основная',
      gateway_model: 'шлюзовая-основная',
      billing: 'metered',
      allow_client_documents: false,
      timeout_seconds: 120,
      api_flavour: 'openai_chat',
      base_url: 'https://openrouter.ai/api/v1',
      transport: 'direct',
      max_parallel_calls: 1,
    });
  });

  it('is a revision of an http_api connection the stand will accept: no field of another kind', () => {
    const request = openRouterRevisionRequest(identity);
    for (const foreign of ['pull_client', 'answer_deadline_seconds', 'max_claimed_tasks', 'ssh_host', 'ssh_port', 'ssh_user', 'ssh_profile', 'host_key']) {
      expect(request, foreign).not.toHaveProperty(foreign);
    }
    expect(request.base_url).toMatch(/^https?:\/\/\S+$/);
  });

  it('keeps client documents off, as the list notice says they are not checked (R-149a)', () => {
    expect(openRouterRevisionRequest(identity).allow_client_documents).toBe(false);
    expect(agentRevisionRequest(identity).allow_client_documents).toBe(false);
  });

  it('makes an agent a not-metered pull connection whose client is the agent, one task at a time', () => {
    expect(agentRevisionRequest(identity)).toEqual({
      pin_id: 'модель-основная',
      gateway_model: 'шлюзовая-основная',
      billing: 'not_metered',
      allow_client_documents: false,
      timeout_seconds: 120,
      pull_client: 'agent',
      answer_deadline_seconds: 600,
      max_claimed_tasks: 1,
    });
  });
});

describe('reading the name, the model and the gateway name', () => {
  it('reads a complete form', () => {
    expect(readIdentity(form(FIELDS), PINNED)).toEqual({
      ok: true,
      identity: { displayName: 'OpenRouter', pinId: 'модель-основная', gatewayModel: 'шлюзовая-основная' },
    });
  });

  it('trims what was typed', () => {
    const reading = readIdentity(form({ ...FIELDS, display_name: '  OpenRouter  ', gateway_model: ' шлюзовая-основная ' }), PINNED);
    expect(reading.ok).toBe(true);
    if (reading.ok) expect(reading.identity.displayName).toBe('OpenRouter');
  });

  it('refuses an empty or over-long name, a model that is not pinned and an empty or over-long gateway name', () => {
    const problem = (over: Record<string, string>) => {
      const reading = readIdentity(form({ ...FIELDS, ...over }), PINNED);
      return reading.ok ? null : reading.problem;
    };
    expect(problem({ display_name: '   ' })).toBe('Укажите название подключения: до 120 символов.');
    expect(problem({ display_name: 'я'.repeat(121) })).toBe('Укажите название подключения: до 120 символов.');
    expect(problem({ pin_id: 'модель-чужая' })).toBe('Выберите модель из списка закреплённых.');
    expect(problem({ gateway_model: '' })).toBe('Укажите имя модели: до 200 символов.');
    expect(problem({ gateway_model: 'я'.repeat(201) })).toBe('Укажите имя модели: до 200 символов.');
    expect(readIdentity(form(FIELDS), [])).toEqual({ ok: false, problem: 'Выберите модель из списка закреплённых.' });
  });
});

describe('the form', () => {
  const markup = render(createElement(OpenRouterSetup, { pinnedModels: PINNED, onBack: noop }));

  it('is prefilled: the address, the format and the connection are printed as facts, not asked for', () => {
    expect(markup).toContain('data-wizard-step="api"');
    expect(markup).toContain('data-openrouter-fixed');
    expect(markup).toContain('https://openrouter.ai/api/v1');
    expect(markup).toContain(FLAVOUR_LABELS.openai_chat);
    expect(markup).toContain(TRANSPORT_LABELS.direct);
    expect(markup).toContain(BILLING_LABELS.metered);
    expect(markup).not.toContain('name="base_url"');
    expect(markup).not.toContain('name="api_flavour"');
  });

  it('asks for a name (OpenRouter), a pinned model and the gateway name', () => {
    expect(markup).toMatch(/name="display_name"[^>]*value="OpenRouter"/);
    expect(markup).toContain('name="pin_id"');
    for (const model of PINNED) expect(markup).toContain(`>${model.pin_id}</option>`);
    expect(markup).toContain('name="gateway_model"');
    expect(markup).toMatch(/name="gateway_model"[^>]*value="модель-основная"/);
  });

  it('has no key field: a key is typed into the server-rendered form on the next page', () => {
    expect(markup).not.toContain('type="password"');
    expect(markup).not.toContain('name="value"');
    expect(markup).not.toMatch(/name="[^"]*(?:key|secret)[^"]*"/i);
    expect(markup).toContain('ключ вводится на следующем шаге');
  });

  it('disables the button when there is no pinned model to choose, and says why', () => {
    const empty = render(createElement(OpenRouterSetup, { pinnedModels: [], onBack: noop }));
    expect(empty).toContain('Список закреплённых моделей пуст');
    expect(empty).toMatch(/<button[^>]*type="submit"[^>]*disabled/);
  });

  it('can be rendered on its own as the facts alone', () => {
    const facts = render(createElement(OpenRouterFixedFacts));
    expect(facts).toContain(OPENROUTER_BASE_URL);
  });
});

describe('the key, then the probe', () => {
  const markup = render(createElement(OpenRouterKeyStep, { connectionId: CID, name: 'OpenRouter' }));

  it('sends the person to the key form of this connection by a link, not by a field', () => {
    const href = executorSecretScreenUrl(CID);
    expect(markup.replaceAll('&amp;', '&')).toContain(`href="${href}"`);
    expect(markup).toContain('data-openrouter-key-link');
    expect(markup).toContain('Ввести ключ');
    expect(markup).not.toContain('<input');
    expect(markup).not.toContain('<textarea');
  });

  it('says the key is sealed and never shown again, and that «Проверить» in the card is the next step', () => {
    expect(markup).toContain('Подключение «OpenRouter» создано');
    expect(markup).toContain('ключ запечатывается при отправке и больше нигде не показывается');
    expect(markup).toContain('нажмите «Проверить» в карточке подключения');
  });
});
