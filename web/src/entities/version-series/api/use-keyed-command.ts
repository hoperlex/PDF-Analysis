'use client';

/**
 * A comparison command that is one intent with one key (`Idempotency-Key`, ADR-0025 decision 19).
 *
 * The rule of the pairing and carry-over commands, once more, for the comparison's writes: the key is
 * minted when the reader expresses the intent and **reused on every retry of it**; a changed signature is
 * a new intent and a new key; a press that arrives while the same intent is in flight joins the request
 * already sent. Whatever happens, the comparison namespace is read again: a refusal means the screen was
 * showing something that is no longer true (`409 comparison_matrix_stale`), and a success moved the
 * overview, the matrix and the series together.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import { newIdempotencyKey } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

import { COMPARISON_KEYS } from './keys';

interface InFlight<Result> {
  readonly signature: string;
  readonly promise: Promise<Result>;
}

export interface KeyedCommandOptions<Command, Result> {
  /** What makes two presses the same intent. */
  readonly signatureOf: (command: Command) => string;
  readonly send: (command: Command, idempotencyKey: string) => Promise<Result>;
}

export function useKeyedCommand<Command, Result>({ signatureOf, send }: KeyedCommandOptions<Command, Result>) {
  const client = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  const flightRef = useRef<InFlight<Result> | null>(null);
  const tell = () => {
    void client.invalidateQueries({ queryKey: COMPARISON_KEYS.all });
  };

  return useMutation<Result, unknown, Command>({
    mutationFn: (command) => {
      const signature = signatureOf(command);
      const held = flightRef.current;
      if (held !== null && held.signature === signature) return held.promise;
      const intent = resolveIntentKey(intentRef.current, signature, newIdempotencyKey);
      intentRef.current = intent;
      const promise: Promise<Result> = send(command, intent.idempotencyKey).finally(() => {
        if (flightRef.current?.promise === promise) flightRef.current = null;
      });
      flightRef.current = { signature, promise };
      return promise;
    },
    retry: false,
    onSuccess: () => {
      // The intent completed: the next press is a new command and mints a new key.
      intentRef.current = null;
      tell();
    },
    onError: tell,
  });
}
