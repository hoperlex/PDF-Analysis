/**
 * One published version as a row.
 *
 * Presentational. It takes a contract `DocumentVersion` and an address to open it at,
 * and holds no query and no route policy: the screen that knows where the reader came
 * from decides the href.
 *
 * `version_ordinal` is rendered and is never the link target — the contract refuses it as
 * a path parameter, and addressing a version by its ordinal would build an identity out
 * of a display value. The link carries `version_uid`.
 *
 * `W59-SECTION-UI-01`: every row carries the version's confirmed stage and section, or
 * «Раздел не подтверждён», from the contract's own `classification` field — so a document's
 * version list and the project structure say the same thing the version screen does.
 *
 * **Dense, as the original's version bar** (`UI-A-24`): the number, the title, the badges and the link to the
 * document sit on one line, the facts and the identity on the next, instead of a bordered block of five paragraphs.
 *
 * `UI-A-45`: a version that carries the contract's `audit` (the document's current version, as `listDocuments` or the
 * document screen read it) draws the chip of its audit state after the badges, as a document card does; one that carries
 * none -- an older version, which no read gives an audit -- draws no chip, and so says nothing about its runs.
 *
 * `CMP-VERSION-MARK-01`: a version admitted for comparison only (`upload_kind` `comparison_pdf`)
 * carries the mark «PDF без пакета портала» under its badges. Any
 * other version, and a version without the field, draws exactly what it drew before.
 */

import Link from 'next/link';

import type { DocumentVersion } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { formatBytes } from '../model/upload-envelope';
import { isComparisonOnly } from '../model/upload-kind';
import { AuditChip } from './audit-chip';
import { ClassificationBadges } from './classification-badges';
import { ComparisonOnlyMark } from './comparison-only-mark';
import styles from './version-row.module.css';

export interface VersionRowProps {
  readonly version: DocumentVersion;
  /** Where this row opens. Built by the screen, never by the row. */
  readonly href: string;
  /** An optional second address, e.g. the document this version belongs to. */
  readonly secondary?: { readonly href: string; readonly label: string } | undefined;
  /** `UI-A-45`: where «Разбор» of a result run opens, for the chip of a version that was run; the screen builds it. */
  readonly reviewAddress?: ((runId: string) => string) | undefined;
}

export function VersionRow({ version, href, secondary, reviewAddress }: VersionRowProps) {
  return (
    <li
      className={styles.row}
      data-version-uid={version.version_uid}
      data-document-uid={version.document_uid}
    >
      <div className={styles.head}>
        <span className={styles.ordinal} title="Номер версии документа">V{version.version_ordinal}</span>
        <Link className={styles.title} href={href}>
          {version.display_title ?? version.source_filename ?? version.version_uid}
        </Link>
        <ClassificationBadges classification={version.classification} />
        {version.audit === undefined ? null : (
          <AuditChip
            audit={version.audit}
            reviewHref={
              version.audit.result_run_id === undefined || reviewAddress === undefined
                ? undefined
                : reviewAddress(version.audit.result_run_id)
            }
          />
        )}
        {isComparisonOnly(version) ? <ComparisonOnlyMark version={version} /> : null}
        {secondary === undefined ? null : (
          <Link className={styles.secondary} href={secondary.href}>{secondary.label}</Link>
        )}
      </div>
      <p className={styles.facts}>
        страниц {version.page_count} · {formatBytes(version.byte_size)} · опубликовано{' '}
        {formatInstant(version.published_at)} · <code>{version.version_uid}</code>
      </p>
    </li>
  );
}
