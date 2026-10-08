export const REGISTRATION_REFUSALS = [
  'validation', 'login_taken', 'request_pending', 'queue_full', 'throttled', 'upstream',
] as const;

export type RegistrationRefusal = (typeof REGISTRATION_REFUSALS)[number];

export function isRegistrationRefusal(value: unknown): value is RegistrationRefusal {
  return typeof value === 'string' && (REGISTRATION_REFUSALS as readonly string[]).includes(value);
}

export function registrationRefusalMessage(refusal: RegistrationRefusal): string {
  switch (refusal) {
    case 'validation': return 'Проверьте поля и повторите отправку. Заявка не создана.';
    case 'login_taken': return 'Этот адрес уже занят действующей учётной записью.';
    case 'request_pending': return 'Заявка с этим адресом уже ожидает решения администратора.';
    case 'queue_full': return 'Очередь заявок заполнена. Попробуйте позже.';
    case 'throttled': return 'Слишком много попыток с этого подключения. Подождите и попробуйте снова.';
    case 'upstream': return 'Сервер не смог подтвердить отправку заявки. Попробуйте позже.';
  }
}
