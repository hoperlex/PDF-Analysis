'use client';

/**
 * The «Запустить проход» command (`W60-OPT-PROPOSALS-01`): `startOptimisationPass` for one
 * document set of one project.
 *
 * **One key per intent, dropped when the intent completes.** The same set pressed again after
 * a transport failure carries the same `Idempotency-Key`, so a lost answer never starts two
 * passes. Once a pass is stored the intent is over: the next press mints a new key, because
 * the inputs the server pins (the newest run, price list and vendor list) may have changed
 * since, and a replayed key would answer the old pass. The server also finds a stored pass
 * with exactly the same inputs under a new key and answers it instead of writing a second.
 *
 * A refusal (`conflict` with its `conflict_reason`) wrote nothing, not even the key, so the
 * next press after the inputs were fixed starts cleanly.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type { DocumentUid, OptimisationPass, ProjectUid } from '@/shared/api';
import { newIdempotencyKey, queryKeys, startOptimisationPass } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

export interface StartOptimisationPassCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
}

export function useStartOptimisationPass() {
  const client = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  return useMutation<OptimisationPass, unknown, StartOptimisationPassCommand>({
    mutationFn: async ({ projectUid, documentUid }) => {
      const intent = resolveIntentKey(
        intentRef.current,
        JSON.stringify([projectUid, documentUid]),
        newIdempotencyKey,
      );
      intentRef.current = intent;
      const response = await startOptimisationPass({
        path: { project_uid: projectUid, document_uid: documentUid },
        idempotencyKey: intent.idempotencyKey,
      });
      return response.data;
    },
    retry: false,
    onSuccess: (pass) => {
      intentRef.current = null;
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.allPasses() });
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.proposalsOf(pass.optimisation_pass_id) });
    },
  });
}
