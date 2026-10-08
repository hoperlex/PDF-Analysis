/**
 * `/analysis-settings` — the presets of an analysis, on their way (`R-66`, group «Система»).
 *
 * An honest stub in `R-23`'s sense: it says the section is coming, what will be in it and
 * when — the "when" named by an event in words, never by a number. The owner ruled the
 * event: **together with the АР section in working order.**
 *
 * What the section would read: the presets of models and stages an administrator keeps and
 * an expert picks from when starting an analysis. The contract names an analysis profile by
 * an opaque identity on a run, and has no operation that lists or edits profiles —
 * `docs/program/W50-REGISTRY-01.md` records the measurement — so the screen shows no number
 * and invents no preset.
 */

import { RoutePlaceholder } from '@/shared/ui';

export function AnalysisSettingsPage() {
  return (
    <RoutePlaceholder
      screen="Настройки анализа"
      route="/analysis-settings"
      promise="Здесь будут наборы настроек анализа — какие модели и стадии применяются к документу: администратор ведёт эти наборы, а эксперт выбирает нужный при запуске. Экран появится вместе с полностью рабочим разделом АР."
    />
  );
}
