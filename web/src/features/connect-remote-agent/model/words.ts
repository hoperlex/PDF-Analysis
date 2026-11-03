/**
 * The words of the «Добавить подключение» wizard and of the agent lifecycle
 * (`EXEC2-WEB-WIZARD-01`, ADR-0026 decisions 4 to 9, owner ruling `R-149b`).
 *
 * Every table is a `Record` over the contract's own value set, so a value the contract adds is a
 * type error here until it has a Russian sentence, and a value the contract removes leaves a key
 * nothing can reach. The Latin product names that remain (`Ubuntu`, `SSH`, `OpenRouter`,
 * `Claude Code`, `API`) are names of things sold or standardised outside this programme.
 *
 * Two rules the sentences keep. A command a person has to type is **never** composed into a
 * sentence: it lives in a copy box (`ui/copy-box.tsx`) so the sentence around it stays Russian
 * and the command stays exactly what the official client documents. And a sentence about a
 * subscription says only what `R-149b` allows: the agent calls the official clients in their
 * documented non-interactive mode under the holder's own login, and the stand copies no
 * credential, imitates no person and evades no limit.
 */

import type {
  ExecutorAgentInstallFailure,
  ExecutorAgentInstallState,
  ExecutorEnrollmentState,
  ExecutorProbeOutcome,
  RunnerCliAuthState,
  RunnerCliName,
} from '@/shared/api';

import type { AgentStepId } from './lifecycle';

// ------------------------------------------------------------------------------ the wizard

export const WIZARD_OPEN_LABEL = 'Добавить подключение';
export const WIZARD_CLOSE_LABEL = 'Закрыть мастер';
export const WIZARD_BACK_LABEL = 'Назад';

export const KIND_CHOICE_TITLE = 'Что подключаем?';

/** The two equal choices of the first screen. */
export const KIND_CHOICES = {
  agent: {
    title: 'Удалённый Ubuntu-агент',
    text:
      'Агент на вашем сервере с Ubuntu забирает задания стенда и отвечает на них через официальные ' +
      'клиенты командной строки (Claude Code или codex) под вашими подписками.',
    action: 'Подключить агента',
  },
  api: {
    title: 'API-провайдер',
    text:
      'Стенд сам обращается к модели по адресу провайдера с вашим ключом. Готовая заготовка для ' +
      'OpenRouter: адрес, формат запросов и модель уже заполнены.',
    action: 'Подключить провайдера',
  },
} as const;

export const MANUAL_LABEL = 'Настроить подключение вручную (все поля)';

/** The two equal cards of the agent screen (path A and path B). */
export const PATH_CHOICE_TITLE = 'Как установить агента?';
export const PATH_CHOICES = {
  ssh: {
    title: 'Установить по SSH',
    text:
      'Стенд сам зайдёт на сервер по SSH и установит агента. Нужен доступ по ключу и права на ' +
      'установку. Пароли не принимаются.',
    action: 'Выбрать установку по SSH',
  },
  command: {
    title: 'Выполнить команду на Ubuntu',
    text:
      'Вы копируете одну команду и запускаете её на сервере сами. Стенду доступ к серверу не нужен. ' +
      'Команда показывается один раз и действует 15 минут.',
    action: 'Выбрать команду',
  },
} as const;

export const IDENTITY_TITLE = 'Название и модель';
export const IDENTITY_NAME_LABEL = 'Название подключения';
export const IDENTITY_MODEL_LABEL = 'Модель';
export const IDENTITY_GATEWAY_LABEL = 'Имя модели, под которым клиент ответит';
export const IDENTITY_GATEWAY_HINT =
  'Точное имя модели, которое укажет клиент командной строки: стенд сверит его с ответом пробы и ' +
  'отклонит ответ другой модели. По умолчанию это закреплённый идентификатор модели.';
export const IDENTITY_BILLING_NOTE =
  'Подключение создаётся без тарификации: ответ клиента на подписке стенд не оценивает и стоимость ' +
  'не выдумывает. Остальные настройки можно изменить в карточке подключения.';

export const NO_PINNED_MODELS = 'Список закреплённых моделей пуст: подключение нельзя настроить.';

// ------------------------------------------------------------------------- path A, over SSH

export const SSH_FORM_TITLE = 'Установка по SSH';
export const SSH_FORM_INTRO =
  'Укажите сервер и пользователя. Пользователю нужны права установить службу без запроса пароля. ' +
  'Пароли не принимаются и нигде не сохраняются.';
export const SSH_PRIVATE_RANGE_HINT =
  'Стенд принимает адреса частных сетей (локальные адреса) только тогда, когда это разрешено в ' +
  'настройках стенда его администратором; иначе установка завершится отказом. Если разрешения нет, ' +
  'выберите путь «Выполнить команду на Ubuntu».';
export const SSH_HOST_LABEL = 'Узел SSH';
export const SSH_PORT_LABEL = 'Порт SSH';
export const SSH_USER_LABEL = 'Пользователь SSH';
export const SSH_ACCESS_LEGEND = 'Как стенд войдёт на сервер';
/**
 * The one way in the wizard offers: the stand makes the key. The private half stays on the stand and
 * the administrator adds the shown public line. Private keys and passwords are not typed into this
 * application (the secret-door rule keeps secrets out of client scripts).
 */
export const SSH_ACCESS_FORM_TITLE = 'Ключ создаст стенд';
export const SSH_ACCESS_FORM_TEXT =
  'Стенд создаст пару ключей и покажет строку для файла authorized_keys нужного пользователя. ' +
  'Закрытая часть остаётся на стенде и удаляется после установки. Закрытые ключи и пароли в это ' +
  'приложение не вводятся.';
/** How a session shows its access, for a session read back from the API (including one made over it). */
export const SSH_ACCESS_LABELS = {
  generated_key: 'ключ создал стенд',
  pasted_key: 'закрытый ключ передан через API',
} as const;
export const SSH_SUBMIT_LABEL = 'Начать установку';

export const INSTALL_STATE_LABELS: Readonly<Record<ExecutorAgentInstallState, string>> = {
  requested: 'Установка запрошена, ждёт процесс стенда',
  scanning: 'Читается отпечаток ключа сервера',
  awaiting_host_key: 'Нужно подтвердить отпечаток сервера',
  installing: 'Агент устанавливается',
  succeeded: 'Агент установлен',
  failed: 'Установка не удалась',
};

export const INSTALL_STATE_HINTS: Readonly<Record<ExecutorAgentInstallState, string>> = {
  requested: 'Процесс стенда скоро возьмёт установку. Страница обновляется сама.',
  scanning: 'Стенд подключается к серверу только затем, чтобы прочитать отпечаток его ключа.',
  awaiting_host_key:
    'Сверьте отпечаток ниже с тем, что показывает сам сервер, и подтвердите его. Без подтверждения установка не пойдёт дальше.',
  installing: 'Стенд запускает установщик на сервере. Страница обновляется сама.',
  succeeded: 'Агент зарегистрируется на стенде сам. Ход регистрации виден ниже и в карточке подключения.',
  failed: 'Причина названа ниже. Подключение осталось: установку можно повторить.',
};

export const AUTHORIZED_KEYS_TITLE = 'Строка для файла authorized_keys';
export const AUTHORIZED_KEYS_HINT =
  'Добавьте эту строку в файл authorized_keys того пользователя, которого вы указали, на сервере. ' +
  'После установки стенд удалит её сам.';
export const FINGERPRINT_TITLE = 'Отпечаток ключа сервера';
export const FINGERPRINT_HINT =
  'Сравните его с отпечатком, который показывает сам сервер, например на его консоли или у ' +
  'провайдера. Подтверждение без сверки отдаёт установку на сервер тому, кто успел подменить ключ.';
export const FINGERPRINT_CHECK_LABEL = 'Я сверил отпечаток с сервером';
export const FINGERPRINT_CONFIRM_LABEL = 'Подтвердить отпечаток';
export const KEY_REMOVED_NOTE = 'Ключ стенда удалён с сервера, его закрытая часть уничтожена.';
export const KEY_NOT_REMOVED_NOTE =
  'Ключ стенда пока не удалён с сервера. Если установка закончена, удалите его строку из authorized_keys вручную.';
export const INSTALL_RETRY_LABEL = 'Повторить установку';
export const INSTALL_FAILED_TITLE = 'Установка не удалась';

/** One sentence for every sanitised reason an install can fail (`ExecutorAgentInstallFailure`). */
export const INSTALL_FAILURE_SENTENCES: Readonly<Record<ExecutorAgentInstallFailure, string>> = {
  host_unreachable:
    'Стенд не подключился к серверу. Причин две. Либо адрес закрыт правилами стенда: адреса частных сетей (локальные адреса) стенд принимает только тогда, когда это разрешено в его настройках администратором, а служебные адреса стенда и петлю не принимает никогда; такой адрес отклоняется, а не просто не отвечает. Если разрешения нет, выберите путь «Выполнить команду на Ubuntu»: команду вы запускаете на самом сервере. Либо сервер недоступен: проверьте адрес, порт и то, что сервер принимает подключения со стенда.',
  ssh_refused:
    'Сервер отклонил вход по SSH. Проверьте имя пользователя и то, что ключ добавлен в файл authorized_keys именно этого пользователя.',
  host_key_changed:
    'Отпечаток ключа сервера изменился между проверкой и установкой. Установка остановлена: начните заново и сверьте отпечаток.',
  host_key_not_confirmed:
    'Отпечаток ключа сервера не подтвердили вовремя. Начните установку заново и подтвердите отпечаток.',
  sudo_password_required:
    'Пользователю нужны права администратора без пароля: при повышении прав сервер запросил пароль. Разрешите пользователю установку без пароля или выберите путь «Выполнить команду на Ubuntu», где команду запускаете вы сами.',
  unsupported_platform:
    'Сервер не поддерживается: агент ставится только на Ubuntu LTS.',
  package_unavailable:
    'Пакет агента недоступен на стенде. Это вопрос к тому, кто разворачивал стенд.',
  install_failed:
    'Установка не завершилась: установщик на сервере вернул ошибку. Подробности стенд не передаёт; повторите установку или выберите путь с командой.',
  enrollment_failed:
    'Агент установлен, но не зарегистрировался на стенде. Повторите установку или получите новую команду.',
  secret_unreadable:
    'Доступ к серверу не удалось прочитать на стенде. Начните заново и укажите ключ ещё раз.',
  no_worker:
    'Ни один процесс стенда не взял установку. Убедитесь, что процесс на связи, на вкладке «Процессы».',
  timed_out: 'Установка не уложилась в отведённое время. Повторите её.',
};

// ------------------------------------------------------------------------- path B, the command

export const COMMAND_START_TITLE = 'Команда установки';
export const COMMAND_START_INTRO =
  'Стенд создаст подключение и выдаст одну команду. Выполните её на сервере с Ubuntu от имени ' +
  'пользователя с правами установки. Команда одноразовая и действует 15 минут.';
export const COMMAND_GET_LABEL = 'Получить команду';
export const COMMAND_NEW_LABEL = 'Новая команда';
export const COMMAND_SHOWN_TITLE = 'Команда установки';
export const COMMAND_SHOWN_ONCE =
  'Команда показана один раз и больше показана не будет. Скопируйте её сейчас: после закрытия ' +
  'этого окна увидеть её снова нельзя. Потерянную команду заменяют новой.';
export const COMMAND_FIELD_LABEL = 'Команда установки';
export const COMMAND_NEW_NOTE = 'Прежняя команда больше не действует: действует только эта.';
export const COMMAND_NEW_HINT =
  'Новая команда отменяет прежнюю, если её ещё не использовали.';
export const COMMAND_CLOSE_LABEL = 'Я скопировал команду, закрыть';
export const COMMAND_EXPIRED_TITLE = 'Команда устарела';
export const COMMAND_EXPIRED_TEXT =
  'Срок действия команды истёк, а агент не зарегистрировался. Получите новую команду.';
export const COPY_LABEL = 'Скопировать';
export const COPIED_LABEL = 'Скопировано.';
export const COMMAND_NO_SECRET_NOTE =
  'Секрет регистрации передаётся установщику через переменную окружения, а не через аргументы команды.';

export const ENROLLMENT_STATE_LABELS: Readonly<Record<ExecutorEnrollmentState, string>> = {
  pending: 'ждёт использования',
  redeemed: 'использована',
  expired: 'устарела',
  revoked: 'заменена или отозвана',
};

// ------------------------------------------------------------------------------- the lifecycle

export const LIFECYCLE_TITLE = 'Удалённый агент';
export const LIFECYCLE_INDEPENDENT_NOTE =
  'Четыре состояния клиента независимы: установка клиента, действительный вход, отметка ' +
  'администратора и пройденная проба модели. Ни одно из них не следует из другого.';

export const STEP_LABELS: Readonly<Record<AgentStepId, string>> = {
  registration: 'Регистрация агента',
  online: 'Агент в сети',
  installed: 'Клиент командной строки установлен',
  login: 'Вход клиента действителен',
  authorised: 'Разрешено для интеграции',
  probe: 'Проба модели пройдена',
  ready: 'Готово к работе',
};

export const STEP_STATE_LABELS = {
  done: 'выполнено',
  waiting: 'ожидание',
  attention: 'нужно действие',
  inert: 'не отмечено',
} as const;

export const CLI_NAMES: Readonly<Record<RunnerCliName, string>> = {
  claude: 'Claude Code',
  codex: 'codex',
};

export const CLI_AUTH_LABELS: Readonly<Record<RunnerCliAuthState, string>> = {
  valid: 'вход действителен',
  login_required: 'нужен вход',
  unknown: 'состояние входа неизвестно',
};

/**
 * The official login commands (`R-149b`): run on the server as the agent's service user, in the
 * client's own documented flow. The person signs in on their own device; nothing is copied.
 */
export const LOGIN_COMMANDS: Readonly<Record<RunnerCliName, string>> = {
  codex: 'sudo -u pdf-agent -H codex login --device-auth',
  claude: 'sudo -u pdf-agent -H claude auth login',
};

export const LOGIN_GUIDANCE_TITLE = 'Как войти в клиент';
export const LOGIN_GUIDANCE_TEXT =
  'Выполните на сервере официальную команду входа от имени служебного пользователя агента. ' +
  'Команда покажет ссылку и код: откройте ссылку на своём устройстве и подтвердите вход под своей ' +
  'учётной записью. Пароли и ключи в это приложение не вводятся, учётные данные никуда не копируются.';
export const LOGIN_COMMAND_LABEL = 'Команда входа';
export const RECHECK_LABEL = 'Проверить снова';
export const RECHECK_HINT =
  'Агент сообщает о клиентах при запуске и периодически, поэтому новое состояние появится не сразу. ' +
  'Кнопка читает последнее сообщение агента.';
export const MISSING_CLI_TITLE = 'Клиент командной строки не найден';
export const MISSING_CLI_TEXT =
  'Установите официальный клиент (Claude Code или codex) для служебного пользователя агента по ' +
  'документации клиента и нажмите «Проверить снова». Сам агент клиентов не устанавливает.';
export const UNKNOWN_LOGIN_TEXT =
  'Клиент не умеет сообщать состояние входа сам. Если вход ещё не выполнен, выполните его командой ниже, затем запустите пробу модели: она покажет, работает ли вход.';

/** The `R-149b` note beside the administrator's mark. */
export const INTEGRATION_NOTE =
  'Отметку ставит администратор. Она значит: работа через клиентов командной строки на этом сервере ' +
  'разрешена условиями их подписок и правилами проекта. Стенд подписку не проверяет и отметку из ' +
  'входа клиента не выводит. Агент вызывает только официальные клиенты в их штатном ' +
  'неинтерактивном режиме под входом самого владельца подписки: он не имитирует человека, не ' +
  'копирует учётные данные между серверами и не обходит лимиты провайдера.';
export const INTEGRATION_SET_LABEL = 'Отметить как разрешённое';
export const INTEGRATION_CLEAR_LABEL = 'Снять отметку';
export const INTEGRATION_CONFIRM_LABEL = 'Подтверждаю отметку';
export const INTEGRATION_CANCEL_LABEL = 'Отмена';
export const INTEGRATION_ASK_TEXT =
  'Поставить отметку «разрешено для интеграции»? Это ваше решение как администратора, оно попадёт в журнал.';

/** What the lifecycle says about the probe of a pull agent, where the gateway wording would mislead. */
export const AGENT_PROBE_HINTS: Readonly<Partial<Record<ExecutorProbeOutcome, string>>> = {
  no_runner_online:
    'Агент не взял проверочное задание за 120 секунд: он не в сети или занят. Проверьте, что служба агента запущена, и запустите пробу ещё раз.',
  model_mismatch:
    'Неподдерживаемая модель: клиент ответил другой моделью, чем указана в настройках. Измените в настройках имя модели на то, которое называет клиент, или выберите модель, которую он поддерживает.',
  credential_refused:
    'Клиент отклонил вход. Выполните вход ещё раз по подсказке выше и запустите пробу снова.',
  timeout: 'Клиент не ответил за отведённое время. Проверьте вход клиента и запустите пробу снова.',
  protocol_error:
    'Ответ клиента не похож на ответ модели. Проверьте, что клиент официальный и обновлён, и запустите пробу снова.',
  kind_not_served: 'Проба для этого вида подключения пока не обслуживается стендом.',
};

// ------------------------------------------------------------------------- moving to a server

export const MOVE_LABEL = 'Перенести на другой сервер';
export const MOVE_TITLE = 'Перенос агента на другой сервер';
export const MOVE_TEXT =
  'Агент переносится новой установкой для того же подключения: название, настройки, назначения и ' +
  'история остаются. Вход в клиентов командной строки на новом сервере выполняется заново ' +
  'официальным способом, учётные данные не копируются. Когда новый агент выйдет в сеть, вы сможете ' +
  'отозвать токен прежнего. Работа, которая идёт сейчас, завершается по обычным правилам: ответ, ' +
  'исход которого неизвестен, не отправляется повторно.';
export const MOVE_CANCEL_LABEL = 'Отменить перенос';
export const MOVE_PENDING_NOTE =
  'Новый агент ожидает регистрации. Прежний продолжает работать, пока вы не отзовёте его токен.';
export const OLD_TOKEN_TITLE = 'Прежний токен агента';
export const OLD_TOKEN_TEXT =
  'Новый агент в сети, а токен прежнего всё ещё действует. Если агент перенесён, отзовите прежний ' +
  'токен: его следующее обращение будет отклонено.';
export const OLD_TOKEN_REVOKE_LABEL = 'Отозвать прежний токен';
export const OLD_TOKEN_CONFIRM_LABEL = 'Подтвердить отзыв';
export const OLD_TOKEN_CONFIRM_TEXT =
  'Отозвать этот токен? Задание, которое прежний агент держит сейчас, вернётся в очередь или истечёт по обычным правилам.';

// ---------------------------------------------------------------------------- the API provider

export const OPENROUTER_TITLE = 'API-провайдер: OpenRouter';
export const OPENROUTER_INTRO =
  'Заготовка для OpenRouter. Адрес и формат запросов уже заполнены. Осталось назвать подключение и ' +
  'выбрать модель; ключ вводится на следующем шаге, затем подключение проверяется.';
export const OPENROUTER_DEFAULT_NAME = 'OpenRouter';
export const OPENROUTER_NAME_LABEL = 'Название подключения';
export const OPENROUTER_MODEL_LABEL = 'Модель';
export const OPENROUTER_GATEWAY_LABEL = 'Имя модели у OpenRouter';
export const OPENROUTER_GATEWAY_HINT =
  'Имя модели в том виде, как её называет OpenRouter. Оно уходит в запрос и сверяется с моделью, которую назвал ответ.';
export const OPENROUTER_SUBMIT_LABEL = 'Создать подключение';
export const OPENROUTER_KEY_TITLE = 'Следующий шаг: ключ';
export const OPENROUTER_KEY_TEXT =
  'Настройки сохранены. Теперь введите ключ OpenRouter на отдельной странице: ' +
  'ключ запечатывается при отправке и больше нигде не показывается. После сохранения ключа нажмите ' +
  '«Проверить» в карточке подключения.';
export const OPENROUTER_KEY_LINK_LABEL = 'Ввести ключ';
export const OPENROUTER_FIXED_TITLE = 'Что уже заполнено';

// ------------------------------------------------------------------------------ the failures

/** The sentence for a definite refusal, keyed by `conflict_reason`. */
export const CONFLICT_SENTENCES: Readonly<Record<string, string>> = {
  enrollment_shown_once:
    'Эта команда уже была показана и повторно показана быть не может. Нажмите «Новая команда»: прежняя перестанет действовать.',
  enrollment_redeemed:
    'Команда уже использована: агент зарегистрирован. Для другого сервера получите новую команду.',
  install_in_progress:
    'Установка по SSH для этого подключения ещё не закончена. Дождитесь её окончания и повторите.',
  install_not_awaiting_host_key:
    'Установка уже не ждёт подтверждения отпечатка. Состояние обновится само.',
  host_key_changed:
    'Подтверждённый вами отпечаток не совпал с тем, что увидел стенд. Сверьте отпечаток заново.',
};

/** The sentence for a missing dependency, keyed by `dependency`. */
export const DEPENDENCY_SENTENCES: Readonly<Record<string, string>> = {
  agent_package:
    'На стенде нет пакета агента: образ собран без него. Установить агента нельзя, пока образ не пересоберут. Это вопрос к тому, кто разворачивал стенд.',
  public_origin:
    'На стенде не задан публичный адрес, поэтому команду установки составить нельзя. Это вопрос к тому, кто разворачивал стенд.',
};

/** The sentence for a refused field, keyed `field/constraint`. */
export const VALIDATION_SENTENCES: Readonly<Record<string, string>> = {
  'kind/kind_not_pull':
    'Агент ставится только для подключения вида «Клиент забирает задания».',
  'ssh_host/format': 'Узел SSH: имя или адрес узла без пробелов.',
  'ssh_port/range': 'Порт SSH: целое число от 1 до 65535.',
  'ssh_user/format': 'Пользователь SSH: латинские буквы, цифры, точка, дефис и подчёркивание.',
  'host_key_fingerprint/pattern': 'Отпечаток не разобран: подтверждайте тот, что показал стенд.',
};

/** What an unknown outcome of a command that shows a secret once tells the person to do. */
export const COMMAND_UNKNOWN_OUTCOME =
  'Исход команды неизвестен: команда могла быть выпущена, но вы её не увидели. Нажмите «Новая ' +
  'команда»: прежняя, если она была выпущена, перестанет действовать.';
