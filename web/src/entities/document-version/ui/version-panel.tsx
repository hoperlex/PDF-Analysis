/**
 * The immutable version panel.
 *
 * A published `DocumentVersion` is an input state that no endpoint modifies, so this
 * panel is read-only by construction: there is nothing to edit and no control that
 * pretends otherwise.
 *
 * What it shows is the identity a reviewer needs to prove which bytes were analysed —
 * the version identity, the page count, the byte size and the SHA-256 — plus the input
 * manifest, which carries a role, a media type, a size and a checksum per entry.
 *
 * What it never shows is a storage address. `version_ordinal` is rendered as a label and
 * is never a link target: the contract refuses it as a path parameter, and a UI that
 * addressed a version by its ordinal would be building an identity out of a display
 * value.
 */

import type { DocumentVersion } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { formatBytes } from '../model/upload-envelope';

export interface VersionPanelProps {
  readonly version: DocumentVersion;
}

function Field({ label, children }: { readonly label: string; readonly children: React.ReactNode }) {
  return (
    <p>
      <strong>{label}</strong> {children}
    </p>
  );
}

export function VersionPanel({ version }: VersionPanelProps) {
  return (
    <div className="am-state" data-version-uid={version.version_uid}>
      <p className="am-state__title">
        {version.display_title ?? version.source_filename ?? 'Опубликованная версия'}
      </p>
      <div className="am-state__detail">
        <Field label="Версия">
          <code>{version.version_uid}</code>
        </Field>
        <Field label="Документ">
          <code>{version.document_uid}</code>
        </Field>
        <Field label="Ordinal">
          {version.version_ordinal} <em>(только порядок отображения, не идентификатор)</em>
        </Field>
        <Field label="Media type">{version.media_type}</Field>
        <Field label="Pages">{version.page_count}</Field>
        <Field label="Size">
          {formatBytes(version.byte_size)} ({version.byte_size} bytes)
        </Field>
        <Field label="SHA-256">
          <code>{version.sha256}</code>
        </Field>
        <Field label="Published">{formatInstant(version.published_at)}</Field>
        {version.source_filename !== undefined && version.source_filename !== null ? (
          <Field label="Uploaded as">
            {version.source_filename} <em>(для отображения, не идентификатор)</em>
          </Field>
        ) : null}
        <p>
          <strong>Входной манифест</strong>
        </p>
        <ul>
          {version.input_manifest.map((entry) => (
            <li key={`${entry.role}:${entry.sha256}`}>
              {entry.role} · {entry.media_type} · {formatBytes(entry.size_bytes)} ·{' '}
              <code>{entry.sha256}</code>
            </li>
          ))}
        </ul>
        <p>
          <em>
            Эта версия и её манифест неизменяемы. Ни один метод API их не меняет.
          </em>
        </p>
      </div>
    </div>
  );
}
