/**
 * `/analysis-settings` — the route file for «Настройки анализа» (`R-66`).
 *
 * Delegation-only: the route decides nothing. `@/_pages/analysis-settings` lists the analysis
 * profile of every section, read-only, since `W59-ANALYSIS-SETTINGS-01` graduated it from the
 * honest stub it was.
 *
 * `W50-PLAN.md` §3.2: the route awaits `requireScreen` with its own address, `params` and
 * `searchParams` before it renders; the registry's row is `session`, roles `any`. Declared
 * `force-dynamic` because the guard reads a cookie, and a screen served from a cache is a
 * screen showing somebody else's session.
 */

import { AnalysisSettingsPage } from '@/_pages/analysis-settings';

import type { ScreenRouteProps } from '../bff/session/screen-lock';
import { requireScreen } from '../bff/session/screen-lock';

export const dynamic = 'force-dynamic';

export default async function AnalysisSettingsRoute({ params, searchParams }: ScreenRouteProps) {
  await requireScreen('/analysis-settings', { params, searchParams });
  return <AnalysisSettingsPage />;
}
