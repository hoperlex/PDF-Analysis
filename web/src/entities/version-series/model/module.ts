/**
 * Which comparison module the deployment serves (`ProductVersion.comparison_modules`, ADR-0025
 * decision 23).
 *
 * The value is a fact about the deployment and not about an account, and it is the only thing this
 * file reads. `none` (the default, and what an old server omits) serves neither module; `versions`
 * «Сравнение версий»; `versions,stages` both. A screen that needs the module asks
 * {@link versionsModuleOn}; it never compares the string itself, so a third value of the closed set
 * is judged in one place.
 */

import type { ComparisonModules } from '@/shared/api';

/** Whether «Сравнение версий» is served. An absent value is `none`. */
export function versionsModuleOn(modules: ComparisonModules | undefined): boolean {
  return modules === 'versions' || modules === 'versions,stages';
}

/** What a screen says about a module that is off, before it has asked an operation anything. */
export const MODULE_OFF_TITLE = 'Модуль «Сравнение версий» выключен';
export const MODULE_OFF_DETAIL =
  'На этом стенде модуль не включён, поэтому его операции ничего не делают. Включает его администратор стенда.';
