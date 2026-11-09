import type { ScreenAddress } from '@/shared/config';

/**
 * The «База знаний» screen's address, a registry row. The side menu names the item this entity's total belongs to by it
 * (`UI-A-06`); `satisfies ScreenAddress` makes the compiler refuse it the day the row is renamed.
 */
export const KNOWLEDGE_BASE_SCREEN = '/knowledge-base' satisfies ScreenAddress;
