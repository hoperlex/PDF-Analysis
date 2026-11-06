'use client';

/**
 * The administrator's commands of «График работ» (`UI-PARITY-P0P`, `R-152a`…`R-152h`): the monthly plans, the default
 * plan and time zone, days off and working days, absences, and moving assignments of «Календарь запаса».
 *
 * **One key per intent, kept until it succeeds.** A retry of a failed command sends the key it was first sent with, so
 * a command that did reach the server is answered, not repeated; a success forgets the key, so the same change made
 * again later (a day made a day off, back, and off again) is a new command and not a replay of the first.
 *
 * Every success invalidates `workSchedule.all()`; a move also `assignments.all()`, because a move to another expert is
 * a reassignment in «Диспетчер».
 */

import { useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { WorkCalendarDayChange, WorkScheduleMonth, WorkScheduleSettings } from '@/shared/api';
import {
  newIdempotencyKey,
  queryKeys,
  scheduleAssignments,
  setEngineerAbsences,
  setWorkCalendarDays,
  setWorkSchedulePlans,
  setWorkScheduleSettings,
} from '@/shared/api';

function useIntentKeys() {
  const keys = useRef(new Map<string, string>());
  return {
    take(intent: string): string {
      const key = keys.current.get(intent) ?? newIdempotencyKey();
      keys.current.set(intent, key);
      return key;
    },
    forget(intent: string): void {
      keys.current.delete(intent);
    },
  };
}

function useScheduleCommand<Input, Output>(
  send: (input: Input, idempotencyKey: string) => Promise<Output>,
  { assignments = false }: { readonly assignments?: boolean } = {},
) {
  const client = useQueryClient();
  const keys = useIntentKeys();
  return useMutation<Output, unknown, Input>({
    mutationFn: async (input) => {
      const intent = JSON.stringify(input);
      const output = await send(input, keys.take(intent));
      keys.forget(intent);
      return output;
    },
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.workSchedule.all() });
      if (assignments) void client.invalidateQueries({ queryKey: queryKeys.assignments.all() });
    },
  });
}

export interface PlanChange {
  readonly userUid: string;
  readonly planned: number;
}

export function useSetPlans() {
  return useScheduleCommand<{ readonly month: string; readonly plans: readonly PlanChange[] }, WorkScheduleMonth>(
    async ({ month, plans }, idempotencyKey) =>
      (await setWorkSchedulePlans({
        body: { month, plans: plans.map((plan) => ({ user_uid: plan.userUid, planned: plan.planned })) },
        idempotencyKey,
      })).data,
  );
}

export function useSetScheduleSettings() {
  return useScheduleCommand<WorkScheduleSettings, WorkScheduleSettings>(
    async (body, idempotencyKey) => (await setWorkScheduleSettings({ body, idempotencyKey })).data,
  );
}

export interface CalendarDayChange {
  readonly day: string;
  readonly kind: WorkCalendarDayChange['kind'];
}

export function useSetCalendarDays() {
  return useScheduleCommand<readonly CalendarDayChange[], void>(async (days, idempotencyKey) => {
    await setWorkCalendarDays({ body: { days: days.map(({ day, kind }) => ({ day, kind })) }, idempotencyKey });
  });
}

export interface AbsenceChange {
  readonly userUid: string;
  readonly days: readonly { readonly day: string; readonly absent: boolean }[];
}

export function useSetAbsences() {
  return useScheduleCommand<AbsenceChange, void>(async ({ userUid, days }, idempotencyKey) => {
    await setEngineerAbsences({
      body: { user_uid: userUid, days: days.map(({ day, absent }) => ({ day, absent })) },
      idempotencyKey,
    });
  });
}

export interface AssignmentPlacement {
  readonly assignmentUid: string;
  /** The day, or `null` for «Без даты». */
  readonly plannedOn: string | null;
  /** Another active expert, or absent to keep the assignee. */
  readonly assigneeUserUid?: string;
}

export function useMoveAssignments() {
  return useScheduleCommand<readonly AssignmentPlacement[], void>(
    async (moves, idempotencyKey) => {
      await scheduleAssignments({
        body: {
          moves: moves.map((move) => ({
            assignment_uid: move.assignmentUid,
            ...(move.plannedOn === null ? {} : { planned_on: move.plannedOn }),
            ...(move.assigneeUserUid === undefined ? {} : { assignee_user_uid: move.assigneeUserUid }),
          })),
        },
        idempotencyKey,
      });
    },
    { assignments: true },
  );
}
