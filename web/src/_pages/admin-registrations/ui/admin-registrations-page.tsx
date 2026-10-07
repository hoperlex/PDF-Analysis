import { RoutePlaceholder } from '@/shared/ui';

export function AdminRegistrationsPage() {
  return (
    <RoutePlaceholder
      screen="Заявки на регистрацию"
      route="/admin/registrations"
      promise="Здесь администратор сможет просматривать заявки на регистрацию и принимать решения по ним."
    />
  );
}
