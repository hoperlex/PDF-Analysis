'use client';

/**
 * Where the comparison of a version sits (`UI-A-22` for this screen): «Проекты › Проект › Документ › Версия N › Сравнение», every step
 * but the last a link. The version's «Блоки» tab draws the same strip through `DocumentContext`, whose levels do not include this
 * screen, so the steps are the widget's own `contextSteps` (the last, «Блоки», replaced by «Сравнение») and the markup is local; the
 * shared widget is not changed. A name that is not read yet is the generic word, as in the strip of the other tabs.
 */

import Link from 'next/link';

import type { VersionUid } from '@/shared/api';
import { useDocumentVersion } from '@/entities/document-version';
import { useProject } from '@/entities/project';
import { contextSteps } from '@/widgets/document-context';

import styles from './stage-comparison-page.module.css';

export function ComparisonContext({ projectUid, versionUid }: { readonly projectUid: string; readonly versionUid: VersionUid }) {
  const version = useDocumentVersion(versionUid);
  const project = useProject(projectUid);
  const steps = [
    ...contextSteps(
      {
        projectUid,
        projectName: project.data?.name,
        documentUid: version.data?.document_uid,
        documentTitle: version.data?.display_title ?? version.data?.source_filename ?? undefined,
        versionUid,
        versionOrdinal: version.data?.version_ordinal,
      },
      'blocks',
    ).slice(0, -1),
    { key: 'comparison', label: 'Сравнение', href: null },
  ];
  return (
    <nav className={styles.context} aria-label="Где вы находитесь" data-context-level="comparison">
      <ol className={styles.steps}>
        {steps.map((step, index) => (
          <li key={step.key} className={styles.step} data-context-step={step.key}>
            {index === 0 ? null : <span aria-hidden="true" className="am-note">›</span>}
            {step.href === null ? <span aria-current="page"><strong>{step.label}</strong></span> : <Link href={step.href}>{step.label}</Link>}
          </li>
        ))}
      </ol>
    </nav>
  );
}
