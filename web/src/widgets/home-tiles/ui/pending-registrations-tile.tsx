'use client';

/**
 * The administrator's tile: how many registration requests wait for a decision
 * (`pending_total`, `listRegistrations`).
 *
 * **Only a session holding `admin` mounts it**, and mounting it is what makes the request:
 * the home page decides from the session's roles, and an expert's home page never asks
 * (`R-60` — managing requests is an administrator's operation). A count and nothing else: no
 * applicant's name, e-mail or reason is selected out of the answer.
 *
 * `href` is the registration screen when the registry has its row, and `null` until then
 * (`registrationsScreenLink`); in `W50` there is no row, so the count stands without a link.
 */

import Link from 'next/link';

import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import { usePendingRegistrationTotal } from '../api/home-reads';
import { classifyRegistrationsFailure } from '../model/read-failure';
import {
  NO_PENDING_REGISTRATIONS_DETAIL,
  NO_PENDING_REGISTRATIONS_TITLE,
  REGISTRATIONS_LOADING,
} from './copy';
import styles from './home-tiles.module.css';

export interface PendingRegistrationsTileProps {
  /** The registration screen's address, or `null` while the registry has no row for it. */
  readonly href: string | null;
}

function Body() {
  const total = usePendingRegistrationTotal();

  if (total.isPending) return <LoadingState what={REGISTRATIONS_LOADING} />;

  // Before the data: a refused re-read keeps the earlier answer beside its error, and that
  // earlier count is not what the API says now.
  if (total.isError) {
    const failure = classifyRegistrationsFailure(total.error);
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void total.refetch(), retryLabel: 'Повторить' }
          : {})}
      />
    );
  }

  if (total.data === 0) {
    return (
      <EmptyState title={NO_PENDING_REGISTRATIONS_TITLE} detail={NO_PENDING_REGISTRATIONS_DETAIL} />
    );
  }

  return (
    <dl className={styles.figures}>
      <dt>Ожидают решения</dt>
      <dd data-pending-total={total.data}>{total.data}</dd>
    </dl>
  );
}

export function PendingRegistrationsTile({ href }: PendingRegistrationsTileProps) {
  return (
    <section className={styles.tile} aria-labelledby="home-registrations" data-home-tile="registrations">
      <h2 id="home-registrations">Заявки на регистрацию</h2>
      <Body />
      {href === null ? null : (
        <p className={styles.more}>
          <Link href={href}>Перейти к заявкам</Link>
        </p>
      )}
    </section>
  );
}
