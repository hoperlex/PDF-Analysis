/**
 * The words of «Подключения» (`EXEC-HTTP-01`): what each kind, transport, billing, probe
 * outcome and secret state is called on the screen.
 *
 * Every table is a `Record` over the contract's own value set, so a value the contract adds
 * is a type error here until it has a Russian sentence, and a value the contract removes
 * leaves a key nothing can reach. The Latin product names that remain (`HTTP API`,
 * `OpenRouter`, `VPN`, `SSH`, `Claude Code`) are names of things standardised or sold
 * outside this programme; `rendered-language.guard.test.ts` lists each with its reason.
 */

import type {
  ExecutorApiFlavour,
  ExecutorBilling,
  ExecutorIdentityBasis,
  ExecutorKind,
  ExecutorProbeOutcome,
  ExecutorProbeState,
  ExecutorPullClient,
  ExecutorRateCheck,
  ExecutorSecretPurpose,
  ExecutorSshProfile,
  ExecutorTransport,
  ExecutorWorkKind,
} from '@/shared/api';

export const KIND_LABELS: Readonly<Record<ExecutorKind, string>> = {
  http_api: 'HTTP API',
  ssh_command: 'Команда по SSH',
  pull: 'Клиент забирает задания',
};

export const KIND_DESCRIPTIONS: Readonly<Record<ExecutorKind, string>> = {
  http_api:
    'Стенд сам обращается к модели по адресу: шлюз, OpenRouter, модель в закрытой сети или на машине за SSH-туннелем.',
  ssh_command:
    'Стенд запускает команду на удалённой машине по SSH. Ключ создаёт приложение, вам остаётся добавить его на машину.',
  pull:
    'Клиент сам приходит за заданиями на стенд: сеанс Claude Code или агент на другой машине. Стенд к нему не обращается, поэтому адрес и ключ модели не нужны: вы выпускаете токен, клиент предъявляет его при каждом обращении.',
};

export const FLAVOUR_LABELS: Readonly<Record<ExecutorApiFlavour, string>> = {
  openai_chat: 'Чат-формат (OpenRouter и совместимые шлюзы)',
  anthropic_messages: 'Формат сообщений Claude',
};

export const TRANSPORT_LABELS: Readonly<Record<ExecutorTransport, string>> = {
  direct: 'Напрямую',
  vpn: 'Через VPN',
  ssh_tunnel: 'Через SSH-туннель',
};

export const BILLING_LABELS: Readonly<Record<ExecutorBilling, string>> = {
  metered: 'Тарифицируется по тарифам закреплённой модели',
  not_metered: 'Не тарифицируется',
};

export const SSH_PROFILE_LABELS: Readonly<Record<ExecutorSshProfile, string>> = {
  claude_code_headless: 'Claude Code без интерфейса',
  custom_command: 'Своя команда на удалённой машине',
};

export const PULL_CLIENT_LABELS: Readonly<Record<ExecutorPullClient, string>> = {
  claude_code_session: 'Сеанс Claude Code',
  agent: 'Агент',
};

export const PURPOSE_LABELS: Readonly<Record<ExecutorSecretPurpose, string>> = {
  api_key: 'Ключ доступа к модели',
  ssh_private_key: 'Ключ SSH',
};

export const WORK_KIND_LABELS: Readonly<Record<ExecutorWorkKind, string>> = {
  text_analysis: 'Анализ текста',
};

export const PROBE_STATE_LABELS: Readonly<Record<ExecutorProbeState, string>> = {
  requested: 'Проверка запрошена, ждёт процесс',
  running: 'Проверка выполняется',
  finished: 'Проверка завершена',
};

export const IDENTITY_BASIS_LABELS: Readonly<Record<ExecutorIdentityBasis, string>> = {
  reported: 'модель сообщена в ответе',
  declared: 'модель заявлена исполнителем',
};

export const RATE_CHECK_LABELS: Readonly<Record<ExecutorRateCheck, string>> = {
  checked: 'стоимость в ответе сверена с тарифом',
  not_reported: 'шлюз не сообщил стоимость, сверять нечего',
  mismatch: 'стоимость в ответе расходится с тарифом',
  not_metered: 'не требуется: подключение не тарифицируется',
};

/**
 * One sentence for every probe outcome. The short phrase is what the owner named for the
 * four common refusals; the rest say what to do next in the same register.
 */
export const PROBE_OUTCOME_SENTENCES: Readonly<Record<ExecutorProbeOutcome, string>> = {
  ok: 'готово',
  ip_refused: 'IP стенда не допущен',
  credential_refused: 'ключ отклонён',
  model_mismatch: 'отвечает другая модель',
  rate_mismatch: 'стоимость в ответе не совпадает с тарифом модели',
  timeout: 'нет ответа',
  unreachable: 'адрес недоступен',
  protocol_error: 'ответ не похож на ответ модели',
  secret_unreadable: 'ключ нужно ввести заново',
  host_key_unpinned: 'отпечаток узла ещё не подтверждён',
  host_key_changed: 'отпечаток узла изменился',
  no_runner_online: 'ни один клиент не на связи',
  destination_refused: 'адрес запрещён правилами стенда',
  kind_not_served: 'этот вид подключения пока не обслуживается',
  no_worker: 'ни один процесс не взял проверку',
};

/** What to do about an outcome, where there is something to do. */
export const PROBE_OUTCOME_HINTS: Readonly<Partial<Record<ExecutorProbeOutcome, string>>> = {
  ip_refused:
    'Шлюз ответил страницей отказа: адрес стенда не внесён в список допущенных. Добавьте его на стороне шлюза.',
  credential_refused: 'Шлюз принял запрос, но не принял ключ. Введите ключ заново.',
  model_mismatch: 'Шлюз назвал в ответе не ту модель, что указана в настройках. Проверьте имя модели на шлюзе.',
  secret_unreadable:
    'Ключ введён для другого адреса или запечатан ключом, которого на стенде больше нет. Введите его заново.',
  host_key_unpinned: 'Подтвердите отпечаток узла: он будет закреплён в новых настройках.',
  host_key_changed: 'Узел представился другим отпечатком, чем закреплённый. Подтверждайте новый, только если уверены в смене.',
  no_worker: 'Проверку никто не взял за 120 секунд. Убедитесь, что процесс на связи, на вкладке «Процессы».',
  destination_refused:
    'Служебные адреса стенда, петля и частные сети закрыты. Частная сеть допускается только через VPN или SSH-туннель.',
  kind_not_served: 'Проверка и назначение для этого вида подключения появятся позже.',
  no_runner_online:
    'Клиент не взял проверочное задание за 120 секунд. Запустите сеанс или агента с токеном этого подключения и нажмите «Проверить» ещё раз.',
};

export function probeOutcomeSentence(outcome: ExecutorProbeOutcome): string {
  return PROBE_OUTCOME_SENTENCES[outcome];
}

/** The `ok` outcome is the only one that lets a connection serve work. */
export function probeSucceeded(outcome: ExecutorProbeOutcome | undefined): boolean {
  return outcome === 'ok';
}
