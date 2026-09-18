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
 */

import Link from 'next/link';

import type { DocumentVersion } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { formatBytes } from '../model/upload-envelope';

export interface VersionRowProps {
  readonly version: DocumentVersion;
  /** Where this row opens. Built by the screen, never by the row. */
  readonly href: string;
  /** An optional second address, e.g. the document this version belongs to. */
  readonly secondary?: { readonly href: string; readonly label: string } | undefined;
}

export function VersionRow({ version, href, secondary }: VersionRowProps) {
  return (
    <li
      className="am-state"
      style={{ marginBottom: '0.5rem' }}
      data-version-uid={version.version_uid}
      data-document-uid={version.document_uid}
    >
      <p className="am-state__title">
        <Link href={href}>
          {version.display_title ?? version.source_filename ?? version.version_uid}
        </Link>
      </p>
      <div className="am-state__detail">
        <p>
          <code>{version.version_uid}</code>
        </p>
        <p>
          Version {version.version_ordinal} · {version.page_count} pages ·{' '}
          {formatBytes(version.byte_size)} · published {formatInstant(version.published_at)}
        </p>
        {secondary === undefined ? null : (
          <p>
            <Link href={secondary.href}>{secondary.label}</Link>
          </p>
        )}
      </div>
    </li>
  );
}
