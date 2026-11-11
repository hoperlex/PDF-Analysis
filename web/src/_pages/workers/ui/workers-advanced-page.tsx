'use client';

/**
 * `/workers/advanced` — «Расширенные исполнители» (`HOSTS-WEB-01`, plan 2026-11-09 §7.5), for an administrator.
 *
 * What «Исполнители» had before it became two tabs, kept whole and folded, one disclosure each, **reused and not rewritten**:
 * «Подключения» (with the key form the address may name), «Группы», «Правила» (with the legacy routes), «Назначения»,
 * «Процессы» with the working switch of intake, the analysis presets (moved here from «Настройки анализа»' place), and
 * «Модели по этапам» with the switch «Модели по этапам: включены», its journal and the revisions, and «Прецеденты и векторы» (`PREC-WEB`: the refusal labels by section).
 *
 * A closed section mounts nothing, so it reads nothing from the API: opening is what reads. The page needs the administrator
 * role; for any other the content is not drawn (the screen registry sends them away before they get here). It is still needed
 * for the comparisons until `HOSTS-CMP-01` and for the SSH connection «kzSonnet».
 *
 * The key form arrives as a prop: it is a server component rendered by the route, so the key never becomes a JavaScript
 * value (`features/set-executor-secret`).
 */

import { useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useState } from 'react';
import type { ReactNode } from 'react';

import { queryKeys } from '@/shared/api';
import { useMe } from '@/entities/account';
import { canExecute, executionFailure } from '@/entities/execution';
import { AnalysisPresets } from '@/widgets/analysis-presets';
import { ExecutorConnections } from '@/widgets/executor-connections';
import { ExecutorGroups } from '@/widgets/executor-groups';
import { ExecutorRoutes } from '@/widgets/executor-routes';
import { ExecutorRules } from '@/widgets/executor-rules';
import { StageLayoutAdvanced } from '@/widgets/executor-stage-models';
import { ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';

import { ADVANCED_SECTIONS, ADVANCED_SECTION_LABELS, BACK_LINK_LABEL } from '../model/advanced';
import type { AdvancedSection } from '../model/advanced';
import { PrecedentSections } from './precedent-sections';
import { ProcessesSection } from './processes-section';

import styles from './workers-page.module.css';

export interface WorkersAdvancedPageProps {
  /** The section the address named, opened at once. */
  readonly initialTab?: AdvancedSection | undefined;
  /** The connection the key form was opened for, from the address. «Подключения» is open when it is named. */
  readonly secretConnectionId?: string | null | undefined;
  /** The server-rendered key form for `secretConnectionId`. */
  readonly secretForm?: ReactNode | undefined;
}

function Section({ id, open, onToggle, children }: {
  readonly id: AdvancedSection;
  readonly open: boolean;
  readonly onToggle: (id: AdvancedSection, open: boolean) => void;
  readonly children: ReactNode;
}) {
  return (
    <details
      className={styles.section}
      open={open}
      data-advanced-section={id}
      onToggle={(event) => onToggle(id, event.currentTarget.open)}
    >
      <summary className={styles.sectionSummary}>{ADVANCED_SECTION_LABELS[id]}</summary>
      {open ? <div className={styles.sectionBody}>{children}</div> : null}
    </details>
  );
}

export function WorkersAdvancedPage({ initialTab, secretConnectionId = null, secretForm }: WorkersAdvancedPageProps = {}) {
  const [opened, setOpened] = useState<ReadonlySet<AdvancedSection>>(
    () => new Set<AdvancedSection>([...(initialTab === undefined ? [] : [initialTab]), ...(secretConnectionId === null ? [] : (['connections'] as const))]),
  );
  const account = useMe();
  const client = useQueryClient();
  const roles = account.data?.roles ?? [];
  const admin = canExecute(roles, 'connections');
  const accountFailure = account.error === null ? null : executionFailure(account.error, false);

  function toggle(id: AdvancedSection, open: boolean) {
    setOpened((was) => {
      if (was.has(id) === open) return was;
      const next = new Set(was);
      if (open) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  const content: Readonly<Record<AdvancedSection, ReactNode>> = {
    connections: <ExecutorConnections roles={roles} secretConnectionId={secretConnectionId} secretForm={secretForm} />,
    groups: <ExecutorGroups roles={roles} />,
    rules: <ExecutorRules roles={roles} legacyRoutes={<ExecutorRoutes roles={roles} history />} />,
    routes: <ExecutorRoutes roles={roles} />,
    processes: <ProcessesSection roles={roles} />,
    presets: <AnalysisPresets roles={roles} />,
    layout: <StageLayoutAdvanced roles={roles} />,
    // `PREC-WEB`: the refusal labels by section; the page is the administrator's, and the server decides again.
    precedents: <PrecedentSections />,
  };

  return (
    <PageShell
      title="Расширенные исполнители"
      subtitle="Подключения, группы, правила, назначения, процессы, пресеты анализа и включение набора моделей. Обычная работа — на экране «Исполнители»."
      actions={(
        <>
          <Link className="am-button am-button--quiet" href="/workers" data-workers-back-link>{BACK_LINK_LABEL}</Link>
          <button className="am-button am-button--quiet" type="button" onClick={() => void client.invalidateQueries({ queryKey: queryKeys.execution.all() })}>Обновить</button>
        </>
      )}
    >
      {account.isPending ? <LoadingState what="права доступа" /> : null}
      {accountFailure !== null ? (
        <div data-workers-account-failure={accountFailure.kind}>
          <ErrorState title="Права доступа не прочитаны" detail={accountFailure.detail} correlationId={accountFailure.correlationId} onRetry={() => void account.refetch()} />
        </div>
      ) : null}
      {account.data !== undefined && !admin ? (
        <UnsupportedState title="Расширенные настройки недоступны" detail="Их показывают только администратору." />
      ) : null}
      {account.data !== undefined && admin ? (
        <div className={styles.sections} data-workers-advanced>
          {ADVANCED_SECTIONS.map((id) => (
            <Section key={id} id={id} open={opened.has(id)} onToggle={toggle}>{content[id]}</Section>
          ))}
        </div>
      ) : null}
    </PageShell>
  );
}
