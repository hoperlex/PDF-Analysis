/**
 * Public API of `_app`. The root layout in `app/` imports from here and from nothing
 * deeper.
 */

export type { AppProvidersProps } from './providers';
export { AppProviders } from './providers';

export type { AppFrameProps } from './app-frame';
export { AppFrame } from './app-frame';

export { createQueryClient } from './query-client';
