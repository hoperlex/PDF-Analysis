'use client';

/**
 * Upload one AR PDF and, once it is published, start a run over it.
 *
 * The accepted envelope is on screen **before** the file picker, not only in the
 * rejection that follows a bad choice. Every line of it names a refusal the server can
 * return, so a later `validation_failed` reads as the rule that was already stated
 * rather than as an arbitrary "no".
 *
 * The published version is shown as an immutable panel. The run control appears only
 * after a version exists, because there is nothing to run over until then.
 */

import { useState } from 'react';

import type { DocumentVersion, ProjectUid, RunStatus } from '@/shared/api';
import { EmptyState } from '@/shared/ui';
import { PC01_UPLOAD_ENVELOPE, UPLOAD_ENVELOPE_RULES, VersionPanel } from '@/entities/document-version';
import { UploadDocumentForm } from '@/features/upload-document';
import { StartRunControl } from '@/features/start-run';

export interface UploadPanelProps {
  readonly projectUid: ProjectUid;
  /** Called when a run has been started over the uploaded version. */
  readonly onRunStarted?: ((run: RunStatus) => void) | undefined;
}

export function UploadPanel({ projectUid, onRunStarted }: UploadPanelProps) {
  const [version, setVersion] = useState<DocumentVersion | null>(null);

  return (
    <section>
      <h2>Upload</h2>

      <div className="am-state" role="note">
        <p className="am-state__title">What this accepts</p>
        <div className="am-state__detail">
          <ul>
            {UPLOAD_ENVELOPE_RULES.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
          <p>
            A file outside this envelope is refused with the reason on screen. Text is
            never recovered by optical recognition instead, and a partially readable
            document is never accepted quietly. The limits are{' '}
            {PC01_UPLOAD_ENVELOPE.maxBytesLabel} and {PC01_UPLOAD_ENVELOPE.maxPages} pages.
          </p>
        </div>
      </div>

      <UploadDocumentForm projectUid={projectUid} onUploaded={setVersion} />

      <h2>Published version</h2>
      {version === null ? (
        <EmptyState
          title="No version published in this session."
          detail="Upload a PDF above. A published version is immutable: nothing here edits or replaces one."
        />
      ) : (
        <>
          <VersionPanel version={version} />
          <h2>Run</h2>
          <StartRunControl
            versionUid={version.version_uid}
            {...(onRunStarted === undefined ? {} : { onStarted: onRunStarted })}
          />
        </>
      )}
    </section>
  );
}
