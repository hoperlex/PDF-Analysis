import type { Account } from '@/shared/api';

/** The two router calls the form makes after a save — `next/navigation`'s, narrowed. */
export interface ProfileSaveRouter {
  refresh(): void;
  push(href: string): void;
}

/**
 * What follows a successful profile save (`C-20`): the server components are rendered again,
 * so the frame shows the subject the BFF has just refreshed, and a completed profile with a
 * `next` address goes there.
 */
export function followProfileSave(
  router: ProfileSaveRouter,
  saved: Pick<Account, 'profile_complete'>,
  next: string | null | undefined,
): void {
  router.refresh();
  if (saved.profile_complete && next) router.push(next);
}
