import { RoutePlaceholder } from '@/shared/ui';

export function RegisterPage() {
  return (
    <RoutePlaceholder
      screen="Регистрация"
      route="/register"
      promise="Здесь можно будет подать заявку на учётную запись. После решения администратора состояние заявки будет показано при входе."
    />
  );
}
