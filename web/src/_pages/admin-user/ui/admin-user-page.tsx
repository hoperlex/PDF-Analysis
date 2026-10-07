import { routes } from '@/shared/lib';
import { RoutePlaceholder } from '@/shared/ui';

export interface AdminUserPageProps {
  readonly userUid: string;
}

export function AdminUserPage({ userUid }: AdminUserPageProps) {
  return (
    <RoutePlaceholder
      screen="Пользователь"
      route={routes.user(userUid)}
      promise="Здесь администратор сможет просматривать и изменять учётную запись пользователя."
    />
  );
}
