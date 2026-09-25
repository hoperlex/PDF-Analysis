'use client';

/**
 * The dashboard: four panels, `R-44`.
 *
 * Composition only — each panel owns its own query, its own failure wording and its own
 * honesty caption; this file lays them out and titles them. `D2`/`R-25`: absent, empty and
 * not-yet-produced are three different answers, and each panel below reaches a different
 * one of the three on its own — the documents and verdict panels can show `EmptyState`,
 * the run-activity panel can show either `EmptyState` (a walk that succeeded and found
 * nothing) depending on what it actually read, and the section panel is permanently
 * `NotApplicableState`, because the question it would need to answer has no operation to
 * ask yet.
 *
 * **What this file does not do.** It does not gate the grid on any panel's state — a
 * failed run-activity walk must not blank the three panels beside it, `D2`'s own
 * "must not render identically" applied to the whole screen rather than to one panel.
 */

import { DocumentsPanel } from './documents-panel';
import { VerdictsPanel } from './verdicts-panel';
import { RunActivityPanel } from './run-activity-panel';
import { SectionsPanel } from './sections-panel';
import styles from './dashboard.module.css';

// Heading ids for `aria-labelledby` only, deliberately not spelled like this stylesheet's
// own class-naming convention: `styling-layer.test.ts` scans every `.tsx` for that pattern
// and expects each hit to be a declared class or modifier, so an id that happened to start
// the same way would read as an undeclared class.
export function Dashboard() {
  return (
    <div className={styles.grid} data-widget="dashboard">
      <section className={styles.panel} aria-labelledby="dashboard-documents-heading">
        <h2 id="dashboard-documents-heading">Документы по проектам</h2>
        <DocumentsPanel />
      </section>
      <section className={styles.panel} aria-labelledby="dashboard-verdicts-heading">
        <h2 id="dashboard-verdicts-heading">Находки по вердикту</h2>
        <VerdictsPanel />
      </section>
      <section className={styles.panel} aria-labelledby="dashboard-runs-heading">
        <h2 id="dashboard-runs-heading">Прогоны и расход</h2>
        <RunActivityPanel />
      </section>
      <section className={styles.panel} aria-labelledby="dashboard-sections-heading">
        <h2 id="dashboard-sections-heading">Разбивка по разделам</h2>
        <SectionsPanel />
      </section>
    </div>
  );
}
