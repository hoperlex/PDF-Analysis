import { RoutePlaceholder } from '@/shared/ui';

export function RegisterSubmittedPage() {
  return (
    <RoutePlaceholder
      screen="Заявка на регистрацию"
      route="/register/submitted"
      promise="Здесь будет подтверждение отправки заявки. Администратор примет решение; состояние заявки можно будет узнать при входе."
    />
  );
}
