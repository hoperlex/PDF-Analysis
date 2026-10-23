'use client';

/**
 * The fields of one revision (`EXEC-HTTP-01`), for a new connection and for a new revision of
 * an existing one.
 *
 * The model is a **select over the pinned set** the list answered with (`pinned_models`): a
 * revision that names an unpinned model is refused by the server (`model_not_pinned`), so the
 * form offers no other, and the pinned rates are printed beside the choice. The name the
 * gateway understands is a second field, because the pin id is what tariffs and the input
 * budget follow and the gateway name is what is sent and compared with the model the answer
 * reports; neither is derived from the other.
 *
 * Fields that belong to another kind or another transport are not drawn, so a form never
 * posts a field the server would refuse. Nothing here is a secret: the key is entered
 * elsewhere, through a form that is never a JavaScript value.
 */

import { useState } from 'react';

import type { ExecutorKind, ExecutorPinnedModel, ExecutorRevision, ExecutorTransport } from '@/shared/api';
import {
  EXECUTOR_API_FLAVOUR_VALUES,
  EXECUTOR_BILLING_VALUES,
  EXECUTOR_PULL_CLIENT_VALUES,
  EXECUTOR_SSH_PROFILE_VALUES,
  EXECUTOR_TRANSPORT_VALUES,
} from '@/shared/api';
import {
  BILLING_LABELS,
  FLAVOUR_LABELS,
  PULL_CLIENT_LABELS,
  SSH_PROFILE_LABELS,
  TRANSPORT_LABELS,
} from '@/entities/executor-connection';

import {
  ANSWER_DEADLINE_MIN_SECONDS,
  CLAIMED_TASKS_MAX,
  FIELD_NAMES,
  PARALLEL_MAX,
  TIMEOUT_MAX_SECONDS,
  initialSettings,
} from '../model/settings';

export interface SettingsFieldsProps {
  readonly kind: ExecutorKind;
  readonly pinnedModels: readonly ExecutorPinnedModel[];
  /** The revision the form starts from; absent for a new connection. */
  readonly initial?: ExecutorRevision | undefined;
  /** Distinguishes the ids of two forms on one page. */
  readonly idPrefix: string;
}

function rateSentence(model: ExecutorPinnedModel | undefined): string {
  return model === undefined
    ? 'Список закреплённых моделей пуст: подключение нельзя настроить.'
    : `Закреплённые тарифы: вход ${model.input_per_mtok_usd} $, выход ${model.output_per_mtok_usd} $ за миллион токенов.`;
}

export function SettingsFields({ kind, pinnedModels, initial, idPrefix }: SettingsFieldsProps) {
  const start = initialSettings(initial, pinnedModels);
  const [pinId, setPinId] = useState(start.pinId);
  const [gatewayModel, setGatewayModel] = useState(start.gatewayModel);
  const [transport, setTransport] = useState<ExecutorTransport>(start.transport);
  const id = (name: string): string => `${idPrefix}-${name}`;
  const pinned = pinnedModels.find((model) => model.pin_id === pinId);
  const tunnelled = kind === 'ssh_command' || (kind === 'http_api' && transport === 'ssh_tunnel');

  function choosePin(next: string) {
    // The gateway name follows the pin until the person has written their own.
    if (gatewayModel === '' || gatewayModel === pinId) setGatewayModel(next);
    setPinId(next);
  }

  return (
    <>
      {kind === 'http_api' ? (
        <>
          <div className="am-form__field">
            <label htmlFor={id('base-url')}>Адрес</label>
            <input
              id={id('base-url')}
              name={FIELD_NAMES.baseUrl}
              type="text"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              required
              maxLength={2048}
              defaultValue={start.baseUrl}
              placeholder="https://openrouter.ai/api/v1"
            />
            <p className="am-form__hint">
              Адрес без параметров. Если указан только узел, к нему добавляется стандартный путь
              запроса чата; если указан путь, к нему добавляется окончание запроса чата.
            </p>
          </div>
          <div className="am-form__field">
            <label htmlFor={id('flavour')}>Формат запросов</label>
            <select id={id('flavour')} name={FIELD_NAMES.apiFlavour} defaultValue={start.apiFlavour}>
              {EXECUTOR_API_FLAVOUR_VALUES.map((flavour) => (
                <option key={flavour} value={flavour}>{FLAVOUR_LABELS[flavour]}</option>
              ))}
            </select>
          </div>
          <div className="am-form__field">
            <label htmlFor={id('transport')}>Способ связи</label>
            <select
              id={id('transport')}
              name={FIELD_NAMES.transport}
              value={transport}
              onChange={(event) => setTransport(event.target.value as ExecutorTransport)}
            >
              {EXECUTOR_TRANSPORT_VALUES.map((value) => (
                <option key={value} value={value}>{TRANSPORT_LABELS[value]}</option>
              ))}
            </select>
            <p className="am-form__hint">
              Частная сеть допускается только через VPN или SSH-туннель; служебные адреса стенда и
              петля закрыты всегда.
            </p>
          </div>
        </>
      ) : null}

      {kind === 'ssh_command' ? (
        <div className="am-form__field">
          <label htmlFor={id('profile')}>Профиль команды</label>
          <select id={id('profile')} name={FIELD_NAMES.sshProfile} defaultValue={start.sshProfile}>
            {EXECUTOR_SSH_PROFILE_VALUES.map((profile) => (
              <option key={profile} value={profile}>{SSH_PROFILE_LABELS[profile]}</option>
            ))}
          </select>
          <p className="am-form__hint">Какая команда выполнится, решает принудительная команда в файле ключей на удалённой машине.</p>
        </div>
      ) : null}

      {tunnelled ? (
        <>
          <div className="am-form__field">
            <label htmlFor={id('ssh-host')}>Узел SSH</label>
            <input id={id('ssh-host')} name={FIELD_NAMES.sshHost} type="text" autoComplete="off" spellCheck={false} required maxLength={253} defaultValue={start.sshHost} />
          </div>
          <div className="am-form__field">
            <label htmlFor={id('ssh-port')}>Порт SSH</label>
            <input id={id('ssh-port')} name={FIELD_NAMES.sshPort} type="number" required min={1} max={65535} defaultValue={start.sshPort} />
          </div>
          <div className="am-form__field">
            <label htmlFor={id('ssh-user')}>Пользователь SSH</label>
            <input id={id('ssh-user')} name={FIELD_NAMES.sshUser} type="text" autoComplete="off" spellCheck={false} required maxLength={64} defaultValue={start.sshUser} />
          </div>
          <div className="am-form__field">
            <label htmlFor={id('host-key')}>Отпечаток узла (необязательно)</label>
            <input id={id('host-key')} name={FIELD_NAMES.hostKey} type="text" autoComplete="off" spellCheck={false} maxLength={2048} defaultValue={start.hostKey} placeholder="Строка открытого ключа узла" />
            <p className="am-form__hint">
              Оставьте пустым: после первой проверки приложение покажет увиденный отпечаток, и вы
              закрепите его одним нажатием.
            </p>
          </div>
        </>
      ) : null}

      {kind === 'pull' ? (
        <>
          <div className="am-form__field">
            <label htmlFor={id('pull-client')}>Клиент</label>
            <select id={id('pull-client')} name={FIELD_NAMES.pullClient} defaultValue={start.pullClient}>
              {EXECUTOR_PULL_CLIENT_VALUES.map((client) => (
                <option key={client} value={client}>{PULL_CLIENT_LABELS[client]}</option>
              ))}
            </select>
          </div>
          <div className="am-form__field">
            <label htmlFor={id('deadline')}>Срок ответа, секунд</label>
            <input id={id('deadline')} name={FIELD_NAMES.answerDeadlineSeconds} type="number" required min={ANSWER_DEADLINE_MIN_SECONDS} max={TIMEOUT_MAX_SECONDS} defaultValue={start.answerDeadlineSeconds} />
          </div>
          <div className="am-form__field">
            <label htmlFor={id('claimed')}>Заданий в работе одновременно</label>
            <input id={id('claimed')} name={FIELD_NAMES.maxClaimedTasks} type="number" required min={1} max={CLAIMED_TASKS_MAX} defaultValue={start.maxClaimedTasks} />
          </div>
        </>
      ) : null}

      <div className="am-form__field">
        <label htmlFor={id('pin')}>Модель</label>
        <select id={id('pin')} name={FIELD_NAMES.pinId} value={pinId} onChange={(event) => choosePin(event.target.value)} required>
          {pinnedModels.map((model) => (
            <option key={model.pin_id} value={model.pin_id}>{model.pin_id}</option>
          ))}
        </select>
        <p className="am-form__hint">{rateSentence(pinned)}</p>
      </div>
      <div className="am-form__field">
        <label htmlFor={id('gateway')}>Имя модели на шлюзе</label>
        <input id={id('gateway')} name={FIELD_NAMES.gatewayModel} type="text" autoComplete="off" spellCheck={false} required maxLength={200} value={gatewayModel} onChange={(event) => setGatewayModel(event.target.value)} />
        <p className="am-form__hint">
          {kind === 'pull'
            ? 'Это точное имя модели, под которым клиент обязан ответить: стенд отклоняет ответ, в котором заявлена другая модель. Сеанс Claude Code называет её так, как показывает выбор модели в сеансе.'
            : 'Это имя уходит в запрос и сверяется с моделью, которую назвал ответ. Если шлюз называет модель иначе, чем закреплённый идентификатор, впишите его имя.'}
        </p>
      </div>

      {kind === 'http_api' ? (
        <div className="am-form__field">
          <label htmlFor={id('parallel')}>Параллельных вызовов</label>
          <input id={id('parallel')} name={FIELD_NAMES.maxParallelCalls} type="number" required min={1} max={PARALLEL_MAX} defaultValue={start.maxParallelCalls} />
        </div>
      ) : null}
      <div className="am-form__field">
        <label htmlFor={id('timeout')}>Время ожидания ответа, секунд</label>
        <input id={id('timeout')} name={FIELD_NAMES.timeoutSeconds} type="number" required min={1} max={TIMEOUT_MAX_SECONDS} defaultValue={start.timeoutSeconds} />
      </div>
      <div className="am-form__field">
        <label htmlFor={id('billing')}>Тарификация</label>
        <select id={id('billing')} name={FIELD_NAMES.billing} defaultValue={start.billing}>
          {EXECUTOR_BILLING_VALUES.map((billing) => (
            <option key={billing} value={billing}>{BILLING_LABELS[billing]}</option>
          ))}
        </select>
        <p className="am-form__hint">
          Тарифы вводить не нужно: они берутся из закреплённой модели. Без тарификации прогон
          показывает «не тарифицируется», а не ноль.
          {kind === 'pull' ? ' Для сеанса на подписке выберите «Не тарифицируется»: стенд не знает стоимости ответа клиента и не выдумывает её.' : ''}
        </p>
      </div>
      <label className="am-form__field">
        <span>
          <input type="checkbox" name={FIELD_NAMES.allowClientDocuments} defaultChecked={start.allowClientDocuments} />{' '}
          Разрешить отправлять документы заказчика
        </span>
        <span className="am-form__hint">
          По умолчанию выключено: пока закрытая бета идёт на тестовых данных, документы заказчика
          внешним подключениям не отправляются.
        </span>
      </label>
    </>
  );
}
