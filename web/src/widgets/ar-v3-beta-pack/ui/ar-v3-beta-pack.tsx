'use client';

/**
 * Whether the reviewed AR v3 beta pack is installed, and who attested it
 * (`AR-V3-BETA-PACK-STATUS-WEB-01`).
 *
 * Five states, each said in words of its own and each reached by a different answer:
 *
 *   loading        the read is in flight;
 *   error          the read failed (a sentence of its own, with a retry — it is a read);
 *   not installed  the server has no pack, so the six checks cannot start and the run list
 *                  draws no start control at all;
 *   installed      the profile, the first twelve characters of the sealed digest (and no more of
 *                  it anywhere in the markup — not in a title, a data attribute or a hidden
 *                  element), the six scopes and the reviewer's record, followed by the sentence
 *                  that the record is not checked;
 *   fault          the answer breaks the contract (installed without a review, a wrong scope
 *                  list, a state nobody declared). It is never drawn as installed and never as an
 *                  empty state; the run list offers nothing on it either.
 *
 * The attestation is printed as the manifest carried it: a record, not a verdict. Every value
 * is rendered as text, so a reviewer's free text cannot become markup.
 */

import { failureMessage } from '@/shared/api';
import { useArV3PackStatus } from '@/entities/audit-run';
import type { ArV3PackReading } from '@/entities/audit-run';
import { ErrorState, LoadingState } from '@/shared/ui';

import {
  ATTESTATION_SENTENCE,
  PACK_FAULT_DETAIL,
  PACK_FAULT_TITLE,
  PACK_INSTALLED_SENTENCE,
  PACK_NOT_INSTALLED_SENTENCE,
  PACK_READ_FAILED_TITLE,
  PACK_TITLE,
  packDigestShown,
} from '../model/pack-presentation';

import styles from './ar-v3-beta-pack.module.css';

type Installed = Extract<ArV3PackReading, { kind: 'installed' }>;

function InstalledPack({ pack }: { readonly pack: Installed }) {
  return (
    <>
      <p data-ar-v3-pack-state="installed">{PACK_INSTALLED_SENTENCE}</p>
      <dl className={styles.facts}>
        <dt>Профиль анализа</dt>
        <dd>
          <code>{pack.analysisProfileId}</code>
        </dd>
        <dt>Контрольная сумма пакета</dt>
        <dd>
          <code>{packDigestShown(pack.packSha256)}</code>
        </dd>
        <dt>Области шести проверок</dt>
        <dd data-ar-v3-pack-scopes={pack.scopeIds.join(' ')}>{pack.scopeIds.join(', ')}</dd>
      </dl>
      <div className={styles.attestation} data-ar-v3-pack-attestation>
        <h3>Запись рецензента</h3>
        <dl className={styles.facts}>
          <dt>Рецензент</dt>
          <dd>{pack.review.reviewer}</dd>
          <dt>В качестве</dt>
          <dd>{pack.review.capacity}</dd>
          <dt>Дата рецензии</dt>
          <dd>
            <time dateTime={pack.review.reviewed_at}>{pack.review.reviewed_at}</time>
          </dd>
          <dt>Ссылка на решение</dt>
          <dd>{pack.review.decision_ref}</dd>
          <dt>Что именно рецензировано</dt>
          <dd>{pack.review.scope_statement}</dd>
        </dl>
        <p className="am-note">
          <em>{ATTESTATION_SENTENCE}</em>
        </p>
      </div>
    </>
  );
}

export function ArV3BetaPack() {
  const { view, refetch } = useArV3PackStatus();

  if (view.phase === 'loading') {
    return <LoadingState what="статуса пакета проверенных норм АР v3" />;
  }

  if (view.phase === 'error') {
    const failure = failureMessage(view.error);
    return (
      <div data-ar-v3-pack-status="error">
        <ErrorState
          title={PACK_READ_FAILED_TITLE}
          detail={<span data-ar-v3-pack-failure={failure.kind}>{failure.detail}</span>}
          correlationId={failure.correlationId}
          onRetry={refetch}
        />
      </div>
    );
  }

  const { reading } = view;

  if (reading.kind === 'fault') {
    return (
      <div data-ar-v3-pack-status="fault" data-ar-v3-pack-fault={reading.reason}>
        <ErrorState title={PACK_FAULT_TITLE} detail={PACK_FAULT_DETAIL} onRetry={refetch} />
      </div>
    );
  }

  return (
    <section
      className={styles.panel}
      aria-labelledby="ar-v3-pack-title"
      data-ar-v3-pack-status={reading.kind}
    >
      <h2 id="ar-v3-pack-title">{PACK_TITLE}</h2>
      {reading.kind === 'installed' ? (
        <InstalledPack pack={reading} />
      ) : (
        <p data-ar-v3-pack-state="not_installed">{PACK_NOT_INSTALLED_SENTENCE}</p>
      )}
    </section>
  );
}
