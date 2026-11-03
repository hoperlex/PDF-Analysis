'use client';

/**
 * «Create the connection if there is none» (`EXEC2-WEB-WIZARD-01`).
 *
 * A connection is a name and a kind; its settings are its first revision (`EXEC-HTTP-01`). The wizard
 * asks for both at once and sends them in that order, each under its own idempotency key, for an
 * agent (a `pull` connection) and for the OpenRouter preset (an `http_api` one) alike. This hook is
 * the one place that does it, and it keeps what has already happened:
 *
 * - if the connection was created and the settings were then refused, the next call saves the
 *   settings onto **the same connection** instead of creating a second one;
 * - if both were saved and a later step failed (the install was refused, the command could not be
 *   issued), the next call returns the same connection: a retry never makes a duplicate;
 * - a different name makes a different connection, and different settings under the same name make a
 *   new revision of the same one.
 *
 * It sends nothing itself: it calls the commands `features/manage-executor-connection` owns, and it
 * does not call `useMutation` (the dashboard-invalidation guard maps that file, not this one).
 */

import { useRef } from 'react';

import type { ExecutorConnectionId, ExecutorKind, ReviseExecutorConnectionRequest } from '@/shared/api';
import {
  useCommandKey,
  useCreateExecutorConnection,
  useReviseExecutorConnection,
} from '@/features/manage-executor-connection';

import { agentFailure } from './failure';

export interface ConnectionSpec {
  readonly kind: ExecutorKind;
  readonly displayName: string;
  readonly body: ReviseExecutorConnectionRequest;
}

interface Made {
  readonly id: ExecutorConnectionId;
  readonly kind: ExecutorKind;
  readonly name: string;
  /** The signature of the revision already saved, or `null` while the settings are not saved. */
  readonly revised: string | null;
}

interface Keys {
  keyFor: (signature: string) => string;
  release: () => void;
}

/** A definite refusal ends the intent; an unknown outcome keeps the key, so a repeat is the same command. */
function settle(keys: Keys, error: unknown): void {
  if (agentFailure(error, true).kind !== 'unknown_outcome') keys.release();
}

export function useEnsureConnection() {
  const create = useCreateExecutorConnection();
  const revise = useReviseExecutorConnection();
  const createKeys = useCommandKey();
  const reviseKeys = useCommandKey();
  const made = useRef<Made | null>(null);

  async function ensure(spec: ConnectionSpec): Promise<ExecutorConnectionId> {
    let current = made.current;
    if (current === null || current.kind !== spec.kind || current.name !== spec.displayName) {
      try {
        const connection = await create.mutateAsync({
          kind: spec.kind,
          displayName: spec.displayName,
          idempotencyKey: createKeys.keyFor(JSON.stringify([spec.kind, spec.displayName])),
        });
        createKeys.release();
        current = { id: connection.connection_id, kind: spec.kind, name: spec.displayName, revised: null };
        made.current = current;
      } catch (error) {
        settle(createKeys, error);
        throw error;
      }
    }
    const signature = JSON.stringify([current.id, spec.body]);
    if (current.revised !== signature) {
      try {
        await revise.mutateAsync({
          connectionId: current.id,
          body: spec.body,
          idempotencyKey: reviseKeys.keyFor(signature),
        });
        reviseKeys.release();
        current = { ...current, revised: signature };
        made.current = current;
      } catch (error) {
        settle(reviseKeys, error);
        throw error;
      }
    }
    return current.id;
  }

  return {
    ensure,
    pending: create.isPending || revise.isPending,
    /** The connection made so far, if any: what a screen names when the next step fails. */
    madeId: (): ExecutorConnectionId | null => made.current?.id ?? null,
  };
}
