'use client';

/**
 * Application providers — the composition root.
 *
 * One query client, created once per browser session and never at module scope, so that
 * a server render does not share a cache between two users' requests.
 *
 * What is deliberately absent: an authentication provider (PC-01 has none), a theme
 * provider (there is one appearance), an i18n provider (the AR corpus is Russian but the
 * shell is not localized), and any global domain store.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useState } from 'react';

import { createQueryClient } from './query-client';

export interface AppProvidersProps {
  readonly children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  const [queryClient] = useState(createQueryClient);
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
