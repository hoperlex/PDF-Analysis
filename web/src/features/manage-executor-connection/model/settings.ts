/**
 * The settings of a revision: reading them out of a form, filling a form from a revision, and
 * saying whether saving them moves the key (`EXEC-HTTP-01`).
 *
 * Pure, so each rule is a function a test calls. The server checks every rule again
 * (`validate_settings`); what is checked here is what a person can fix before pressing the
 * button — a number out of range, an empty required field, a model that is not in the list —
 * so the message is a Russian sentence next to the field rather than a refusal round trip.
 *
 * Every field name is the contract's own property name, so a field the contract renames is a
 * type error in `FIELD_NAMES` and not a form that quietly posts nothing.
 */

import type {
  ExecutorApiFlavour,
  ExecutorBilling,
  ExecutorKind,
  ExecutorPinnedModel,
  ExecutorRevision,
  ExecutorSshProfile,
  ExecutorPullClient,
  ExecutorTransport,
  ReviseExecutorConnectionRequest,
} from '@/shared/api';
import {
  EXECUTOR_API_FLAVOUR_VALUES,
  EXECUTOR_BILLING_VALUES,
  EXECUTOR_PULL_CLIENT_VALUES,
  EXECUTOR_SSH_PROFILE_VALUES,
  EXECUTOR_TRANSPORT_VALUES,
} from '@/shared/api';
import { destinationChanged } from '@/entities/executor-connection';

export const TIMEOUT_DEFAULT_SECONDS = 120;
export const TIMEOUT_MAX_SECONDS = 3600;
export const PARALLEL_DEFAULT = 1;
export const PARALLEL_MAX = 16;
export const SSH_PORT_DEFAULT = 22;
export const ANSWER_DEADLINE_DEFAULT_SECONDS = 600;
export const ANSWER_DEADLINE_MIN_SECONDS = 10;
export const CLAIMED_TASKS_DEFAULT = 1;
export const CLAIMED_TASKS_MAX = 16;

/** The form's field names, one place. */
export const FIELD_NAMES = {
  displayName: 'display_name',
  kind: 'kind',
  pinId: 'pin_id',
  gatewayModel: 'gateway_model',
  billing: 'billing',
  allowClientDocuments: 'allow_client_documents',
  timeoutSeconds: 'timeout_seconds',
  apiFlavour: 'api_flavour',
  baseUrl: 'base_url',
  transport: 'transport',
  maxParallelCalls: 'max_parallel_calls',
  sshHost: 'ssh_host',
  sshPort: 'ssh_port',
  sshUser: 'ssh_user',
  sshProfile: 'ssh_profile',
  hostKey: 'host_key',
  pullClient: 'pull_client',
  answerDeadlineSeconds: 'answer_deadline_seconds',
  maxClaimedTasks: 'max_claimed_tasks',
} as const;

export type SettingsReading =
  | { readonly ok: true; readonly body: ReviseExecutorConnectionRequest }
  | { readonly ok: false; readonly problem: string };

function text(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === 'string' ? value.trim() : '';
}

function whole(value: string): number | null {
  return /^[0-9]{1,6}$/.test(value) ? Number(value) : null;
}

function member<T extends string>(values: readonly T[], value: string): T | null {
  return (values as readonly string[]).includes(value) ? (value as T) : null;
}

function inRange(value: number | null, min: number, max: number): value is number {
  return value !== null && value >= min && value <= max;
}

/**
 * Read a revision out of a posted form. The server needs the full settings, never a patch, so
 * every field the kind takes is read, and every field it does not take is left out — the
 * server refuses a field that does not belong to the kind.
 */
export function readRevision(
  kind: ExecutorKind,
  form: FormData,
  pinnedModels: readonly ExecutorPinnedModel[],
): SettingsReading {
  const pinId = text(form, FIELD_NAMES.pinId);
  if (!pinnedModels.some((model) => model.pin_id === pinId)) {
    return { ok: false, problem: 'Выберите модель из списка закреплённых.' };
  }
  const gatewayModel = text(form, FIELD_NAMES.gatewayModel);
  if (gatewayModel === '' || gatewayModel.length > 200) {
    return { ok: false, problem: 'Укажите имя модели на шлюзе: до 200 символов.' };
  }
  const billing = member<ExecutorBilling>(EXECUTOR_BILLING_VALUES, text(form, FIELD_NAMES.billing));
  if (billing === null) return { ok: false, problem: 'Выберите, тарифицируется ли подключение.' };
  const timeout = whole(text(form, FIELD_NAMES.timeoutSeconds));
  if (!inRange(timeout, 1, TIMEOUT_MAX_SECONDS)) {
    return { ok: false, problem: `Время ожидания: целое число секунд от 1 до ${TIMEOUT_MAX_SECONDS}.` };
  }
  let body: ReviseExecutorConnectionRequest = {
    pin_id: pinId,
    gateway_model: gatewayModel,
    billing,
    allow_client_documents: form.get(FIELD_NAMES.allowClientDocuments) !== null,
    timeout_seconds: timeout,
  };

  if (kind === 'http_api') {
    const flavour = member<ExecutorApiFlavour>(EXECUTOR_API_FLAVOUR_VALUES, text(form, FIELD_NAMES.apiFlavour));
    if (flavour === null) return { ok: false, problem: 'Выберите формат запросов.' };
    const baseUrl = text(form, FIELD_NAMES.baseUrl);
    if (!/^https?:\/\/\S+$/i.test(baseUrl) || baseUrl.length > 2048) {
      return { ok: false, problem: 'Адрес: нужен адрес вида https://узел или https://узел:порт без пробелов.' };
    }
    const transport = member<ExecutorTransport>(EXECUTOR_TRANSPORT_VALUES, text(form, FIELD_NAMES.transport));
    if (transport === null) return { ok: false, problem: 'Выберите способ связи.' };
    const parallel = whole(text(form, FIELD_NAMES.maxParallelCalls));
    if (!inRange(parallel, 1, PARALLEL_MAX)) {
      return { ok: false, problem: `Параллельных вызовов: целое число от 1 до ${PARALLEL_MAX}.` };
    }
    body = { ...body, api_flavour: flavour, base_url: baseUrl, transport, max_parallel_calls: parallel };
    if (transport === 'ssh_tunnel') {
      const ssh = readSshEndpoint(form);
      if (!ssh.ok) return ssh;
      body = { ...body, ...ssh.fields };
    }
    return { ok: true, body };
  }

  if (kind === 'ssh_command') {
    const profile = member<ExecutorSshProfile>(EXECUTOR_SSH_PROFILE_VALUES, text(form, FIELD_NAMES.sshProfile));
    if (profile === null) return { ok: false, problem: 'Выберите профиль команды.' };
    const ssh = readSshEndpoint(form);
    if (!ssh.ok) return ssh;
    return { ok: true, body: { ...body, ssh_profile: profile, ...ssh.fields } };
  }

  const client = member<ExecutorPullClient>(EXECUTOR_PULL_CLIENT_VALUES, text(form, FIELD_NAMES.pullClient));
  if (client === null) return { ok: false, problem: 'Выберите клиента.' };
  const deadline = whole(text(form, FIELD_NAMES.answerDeadlineSeconds));
  if (!inRange(deadline, ANSWER_DEADLINE_MIN_SECONDS, TIMEOUT_MAX_SECONDS)) {
    return { ok: false, problem: `Срок ответа: целое число секунд от ${ANSWER_DEADLINE_MIN_SECONDS} до ${TIMEOUT_MAX_SECONDS}.` };
  }
  const claimed = whole(text(form, FIELD_NAMES.maxClaimedTasks));
  if (!inRange(claimed, 1, CLAIMED_TASKS_MAX)) {
    return { ok: false, problem: `Заданий в работе: целое число от 1 до ${CLAIMED_TASKS_MAX}.` };
  }
  return {
    ok: true,
    body: { ...body, pull_client: client, answer_deadline_seconds: deadline, max_claimed_tasks: claimed },
  };
}

type SshFields = Pick<ReviseExecutorConnectionRequest, 'ssh_host' | 'ssh_port' | 'ssh_user' | 'host_key'>;

function readSshEndpoint(
  form: FormData,
): { readonly ok: true; readonly fields: SshFields } | { readonly ok: false; readonly problem: string } {
  const host = text(form, FIELD_NAMES.sshHost);
  if (!/^(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|\[[0-9A-Fa-f:.]{2,45}\])$/.test(host)) {
    return { ok: false, problem: 'Узел SSH: имя или адрес узла без пробелов.' };
  }
  const port = whole(text(form, FIELD_NAMES.sshPort));
  if (!inRange(port, 1, 65535)) return { ok: false, problem: 'Порт SSH: целое число от 1 до 65535.' };
  const user = text(form, FIELD_NAMES.sshUser);
  if (!/^[A-Za-z_][A-Za-z0-9_.-]{0,63}$/.test(user)) {
    return { ok: false, problem: 'Пользователь SSH: латинские буквы, цифры, точка, дефис и подчёркивание.' };
  }
  const hostKey = text(form, FIELD_NAMES.hostKey);
  return {
    ok: true,
    fields: {
      ssh_host: host,
      ssh_port: port,
      ssh_user: user,
      ...(hostKey === '' ? {} : { host_key: hostKey }),
    },
  };
}

/** The values a form starts from for a new connection of `kind`. */
export interface SettingsInitial {
  readonly pinId: string;
  readonly gatewayModel: string;
  readonly billing: ExecutorBilling;
  readonly allowClientDocuments: boolean;
  readonly timeoutSeconds: number;
  readonly apiFlavour: ExecutorApiFlavour;
  readonly baseUrl: string;
  readonly transport: ExecutorTransport;
  readonly maxParallelCalls: number;
  readonly sshHost: string;
  readonly sshPort: number;
  readonly sshUser: string;
  readonly sshProfile: ExecutorSshProfile;
  readonly hostKey: string;
  readonly pullClient: ExecutorPullClient;
  readonly answerDeadlineSeconds: number;
  readonly maxClaimedTasks: number;
}

export function initialSettings(
  revision: ExecutorRevision | undefined,
  pinnedModels: readonly ExecutorPinnedModel[],
): SettingsInitial {
  const firstPin = pinnedModels[0]?.pin_id ?? '';
  return {
    pinId: revision?.pin_id ?? firstPin,
    gatewayModel: revision?.gateway_model ?? firstPin,
    billing: revision?.billing ?? 'metered',
    allowClientDocuments: revision?.allow_client_documents ?? false,
    timeoutSeconds: revision?.timeout_seconds ?? TIMEOUT_DEFAULT_SECONDS,
    apiFlavour: revision?.api_flavour ?? 'openai_chat',
    baseUrl: revision?.base_url ?? '',
    transport: revision?.transport ?? 'direct',
    maxParallelCalls: revision?.max_parallel_calls ?? PARALLEL_DEFAULT,
    sshHost: revision?.ssh_host ?? '',
    sshPort: revision?.ssh_port ?? SSH_PORT_DEFAULT,
    sshUser: revision?.ssh_user ?? '',
    sshProfile: revision?.ssh_profile ?? 'claude_code_headless',
    hostKey: revision?.host_key ?? '',
    pullClient: revision?.pull_client ?? 'claude_code_session',
    answerDeadlineSeconds: revision?.answer_deadline_seconds ?? ANSWER_DEADLINE_DEFAULT_SECONDS,
    maxClaimedTasks: revision?.max_claimed_tasks ?? CLAIMED_TASKS_DEFAULT,
  };
}

/**
 * The same settings as a request, for a revision that changes one field and keeps the rest
 * (confirming an observed host key). `null` when the revision lacks a field its kind needs.
 */
export function requestFromRevision(
  revision: ExecutorRevision,
  changes: Partial<ReviseExecutorConnectionRequest> = {},
): ReviseExecutorConnectionRequest {
  const base: ReviseExecutorConnectionRequest = {
    pin_id: revision.pin_id,
    gateway_model: revision.gateway_model,
    billing: revision.billing,
    allow_client_documents: revision.allow_client_documents,
    timeout_seconds: revision.timeout_seconds,
    ...(revision.api_flavour === undefined ? {} : { api_flavour: revision.api_flavour }),
    ...(revision.base_url === undefined ? {} : { base_url: revision.base_url }),
    ...(revision.transport === undefined ? {} : { transport: revision.transport }),
    ...(revision.max_parallel_calls === undefined ? {} : { max_parallel_calls: revision.max_parallel_calls }),
    ...(revision.ssh_host === undefined ? {} : { ssh_host: revision.ssh_host }),
    ...(revision.ssh_port === undefined ? {} : { ssh_port: revision.ssh_port }),
    ...(revision.ssh_user === undefined ? {} : { ssh_user: revision.ssh_user }),
    ...(revision.host_key === undefined ? {} : { host_key: revision.host_key }),
    ...(revision.ssh_profile === undefined ? {} : { ssh_profile: revision.ssh_profile }),
    ...(revision.pull_client === undefined ? {} : { pull_client: revision.pull_client }),
    ...(revision.answer_deadline_seconds === undefined ? {} : { answer_deadline_seconds: revision.answer_deadline_seconds }),
    ...(revision.max_claimed_tasks === undefined ? {} : { max_claimed_tasks: revision.max_claimed_tasks }),
  };
  return { ...base, ...changes };
}

/**
 * True when saving the form over `current` moves the destination a key is bound to, so the
 * key entered for `current` will not open for the new revision. A form that does not read
 * (a problem the person is still fixing) says nothing.
 */
export function draftMovesTheKey(
  kind: ExecutorKind,
  current: ExecutorRevision,
  form: FormData,
  pinnedModels: readonly ExecutorPinnedModel[],
): boolean {
  const reading = readRevision(kind, form, pinnedModels);
  if (!reading.ok) return false;
  return destinationChanged(kind, current, reading.body);
}
