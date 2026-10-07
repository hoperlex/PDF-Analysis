import { RoutePlaceholder } from '@/shared/ui';

export function AdminUsersPage() {
  return (
    <RoutePlaceholder
      screen="Пользователи"
      route="/admin/users"
      promise="Здесь администратор сможет просматривать учётные записи и управлять ими."
    />
  );
}
