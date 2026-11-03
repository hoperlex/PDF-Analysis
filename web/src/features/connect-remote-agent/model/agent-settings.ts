/**
 * What the wizard sends (`EXEC2-WEB-WIZARD-01`): reading its forms, and the first revision of the
 * two kinds of connection it creates.
 *
 * **An agent connection** is a `pull` connection whose client is `agent` (ADR-0026 decision 6). Its
 * first revision carries only what a person decides in the wizard — a name, a pinned model and the
 * name the client will answer under — and the defaults of a subscription: not metered (the stand
 * does not know what a reply on a subscription costs and does not invent it), no client documents
 * (`R-149a`), one task at a time (the installer writes `concurrency = 1`). Everything else is
 * changed afterwards on the connection's card.
 *
 * **The OpenRouter preset** is an `http_api` connection with the gateway's address and the
 * `openai_chat` format filled in, metered by the pinned model's rates, called directly, one call at
 * a time. The key is not here: it never becomes a JavaScript value, so it is entered on the
 * server-rendered key screen (`features/set-executor-secret`).
 *
 * Pure: a form goes in, a request or a problem comes out, so each rule is a function a test calls.
 * The server checks every rule again; what is checked here is what a person can fix before pressing
 * the button.
 */

import type {
  CreateExecutorAgentInstallRequest,
  ExecutorPinnedModel,
  ReviseExecutorConnectionRequest,
} from '@/shared/api';
import {
  ANSWER_DEADLINE_DEFAULT_SECONDS,
  CLAIMED_TASKS_DEFAULT,
  FIELD_NAMES,
  PARALLEL_DEFAULT,
  TIMEOUT_DEFAULT_SECONDS,
  readSshEndpoint,
} from '@/features/manage-executor-connection';

/** The address and format the OpenRouter preset fills in. */
export const OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1';

export interface AgentIdentity {
  readonly displayName: string;
  readonly pinId: string;
  readonly gatewayModel: string;
}

export type IdentityReading =
  | { readonly ok: true; readonly identity: AgentIdentity }
  | { readonly ok: false; readonly problem: string };

function text(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === 'string' ? value.trim() : '';
}

/**
 * The name, the pinned model and the gateway name out of a posted form. The model must be one of the
 * pinned set the list answered with (a revision naming another is refused, `model_not_pinned`).
 */
export function readIdentity(form: FormData, pinnedModels: readonly ExecutorPinnedModel[]): IdentityReading {
  const displayName = text(form, FIELD_NAMES.displayName);
  if (displayName === '' || displayName.length > 120) {
    return { ok: false, problem: 'Укажите название подключения: до 120 символов.' };
  }
  const pinId = text(form, FIELD_NAMES.pinId);
  if (!pinnedModels.some((model) => model.pin_id === pinId)) {
    return { ok: false, problem: 'Выберите модель из списка закреплённых.' };
  }
  const gatewayModel = text(form, FIELD_NAMES.gatewayModel);
  if (gatewayModel === '' || gatewayModel.length > 200) {
    return { ok: false, problem: 'Укажите имя модели: до 200 символов.' };
  }
  return { ok: true, identity: { displayName, pinId, gatewayModel } };
}

/** The first revision of an agent connection (see the header). */
export function agentRevisionRequest(identity: AgentIdentity): ReviseExecutorConnectionRequest {
  return {
    pin_id: identity.pinId,
    gateway_model: identity.gatewayModel,
    billing: 'not_metered',
    allow_client_documents: false,
    timeout_seconds: TIMEOUT_DEFAULT_SECONDS,
    pull_client: 'agent',
    answer_deadline_seconds: ANSWER_DEADLINE_DEFAULT_SECONDS,
    max_claimed_tasks: CLAIMED_TASKS_DEFAULT,
  };
}

/** The first revision of the OpenRouter preset (see the header). */
export function openRouterRevisionRequest(identity: AgentIdentity): ReviseExecutorConnectionRequest {
  return {
    pin_id: identity.pinId,
    gateway_model: identity.gatewayModel,
    billing: 'metered',
    allow_client_documents: false,
    timeout_seconds: TIMEOUT_DEFAULT_SECONDS,
    api_flavour: 'openai_chat',
    base_url: OPENROUTER_BASE_URL,
    transport: 'direct',
    max_parallel_calls: PARALLEL_DEFAULT,
  };
}

export type InstallReading =
  | { readonly ok: true; readonly body: CreateExecutorAgentInstallRequest }
  | { readonly ok: false; readonly problem: string };

/**
 * The install form: host, port and user, judged by the revision form's own patterns. **That is all it
 * reads.** The way the stand gets in is always `generated_key` — the stand makes the key pair, keeps
 * the private half and shows the line to add — so the request is built here and no field of the form
 * can change it. The wizard has no password field and no private-key field, reads no key, parses no
 * key, and no request it builds carries a private-key field; a secret never becomes a value of this client.
 */
export function readInstall(form: FormData): InstallReading {
  const endpoint = readSshEndpoint(form);
  if (!endpoint.ok) return endpoint;
  return {
    ok: true,
    body: {
      ssh_host: endpoint.fields.ssh_host ?? '',
      ssh_port: endpoint.fields.ssh_port ?? 22,
      ssh_user: endpoint.fields.ssh_user ?? '',
      access: 'generated_key',
    },
  };
}

/** The intent signature of an install request, for the idempotency key. */
export function installSignature(connectionId: string, body: CreateExecutorAgentInstallRequest): string {
  return JSON.stringify([connectionId, body.ssh_host, body.ssh_port, body.ssh_user, body.access]);
}
