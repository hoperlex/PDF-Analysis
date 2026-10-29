'use client';

/**
 * The state of one estimate dialog: the estimate read for a scope, the agreement given to it, and the start that carries its
 * digest (`Q-CMP-7`, ADR-0025 decision 19).
 *
 * The agreement is **the digest it was given to**, not a flag: when the estimate on screen changes (a refused start re-read it, the
 * route moved), the stored digest no longer equals the shown one and `agreementStands` is false, so the reader is asked again.
 * A start refused as `409 comparison_estimate_stale` clears the agreement outright and re-reads the estimate; it never retries by
 * itself. The command that goes out is built from the estimate the reader was looking at.
 */

import { useState } from 'react';

import type { ComparisonAiEstimate, ComparisonAiJob, ComparisonAiJobId, ComparisonReport, ComparisonReportId } from '@/shared/api';

import { comparisonFailure } from '../model/failure';
import type { ComparisonFailure } from '../model/failure';

import type { EstimateScope } from './use-ai';
import { useAiEstimate } from './use-ai';
import type { AiJobMethod } from './use-ai-commands';
import { useAiJobAct, useAiStart, useReportCommand } from './use-ai-commands';

export interface ConsentFlowOptions {
  readonly restart?: boolean;
  readonly retryJobId?: ComparisonAiJobId;
  /** The consent is for the **resume** of a paused job (after `overrun` or `route_changed`), not for a start. */
  readonly resumeJob?: { readonly method: AiJobMethod; readonly jobId: ComparisonAiJobId };
  /** The consent is for the **continuation** of a report. */
  readonly continueReportId?: ComparisonReportId;
  readonly onStarted?: (result: ComparisonAiJob | ComparisonReport) => void;
}

export interface ConsentFlow {
  readonly estimate: ComparisonAiEstimate | undefined;
  readonly loading: boolean;
  /** The read failed, or the start was refused. */
  readonly failure: ComparisonFailure | null;
  readonly agreedDigest: string | null;
  readonly busy: boolean;
  readonly agree: (on: boolean) => void;
  readonly confirm: () => void;
}

export function useConsentFlow(scope: EstimateScope | null, options: ConsentFlowOptions = {}): ConsentFlow {
  const read = useAiEstimate(scope);
  const start = useAiStart();
  const resume = useAiJobAct();
  const proceed = useReportCommand();
  const [agreedDigest, setAgreedDigest] = useState<string | null>(null);
  const estimate = read.data;
  const error = start.error ?? resume.error ?? proceed.error ?? read.error ?? null;
  return {
    estimate,
    loading: scope !== null && read.isPending,
    failure: error === null ? null : comparisonFailure(error),
    agreedDigest,
    busy: start.isPending || resume.isPending || proceed.isPending,
    agree: (on) => {
      start.reset();
      resume.reset();
      proceed.reset();
      setAgreedDigest(on && estimate !== undefined ? estimate.estimate_digest : null);
    },
    confirm: () => {
      if (scope === null || estimate === undefined || agreedDigest !== estimate.estimate_digest) return;
      const done = {
        onSuccess: (result: ComparisonAiJob | ComparisonReport): void => {
          setAgreedDigest(null);
          options.onStarted?.(result);
        },
        onError: (failure: unknown): void => {
          // The digest the reader agreed to is no longer the one the server computes: ask again, never resend on their behalf.
          if (comparisonFailure(failure).estimateStale) {
            setAgreedDigest(null);
            void read.refetch();
          }
        },
      };
      if (options.resumeJob !== undefined) {
        resume.mutate({ method: options.resumeJob.method, act: 'resume', jobId: options.resumeJob.jobId, shown: estimate }, done);
        return;
      }
      if (options.continueReportId !== undefined) {
        proceed.mutate({ act: 'continue', reportId: options.continueReportId, shown: estimate }, done);
        return;
      }
      start.mutate(
        {
          scope,
          shown: estimate,
          ...(options.restart === true ? { restart: true } : {}),
          ...(options.retryJobId === undefined ? {} : { retryJobId: options.retryJobId }),
        },
        done,
      );
    },
  };
}
