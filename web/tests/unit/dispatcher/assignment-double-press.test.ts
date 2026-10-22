/**
 * `WEB-FOLLOWUPS-02` / `D-195`: a second press of «Назначить» or of an assignment's move while
 * the first is in flight sends no second `POST`.
 *
 * Neither command carries an idempotency key; the server answers a repeat with the open
 * assignment (create) or the unchanged one (move), or refuses it (`assignment_open`,
 * `state_transition_not_allowed`), and the screen showed the LATER answer. A press that finds
 * its intent in flight now joins the request already sent. What makes two presses one intent:
 * for a creation the project, document, expert and trimmed note; for a move the assignment,
 * the kind, the trimmed reason and the new assignee. Another move on the same assignment is
 * another intent and is sent. The gate reopens when the request settles, so a deliberate press
 * afterwards is a new request.
 *
 * Exercised through the hooks' configuration on ONE instance each, as the command suites do.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@tanstack/react-query', () => ({
  useMutation: (configuration: unknown) => configuration,
  useQueryClient: () => ({ invalidateQueries: () => Promise.resolve() }),
}));

vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, useRef: (value: unknown) => ({ current: value }) };
});

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, createAssignment: vi.fn(), transitionAssignment: vi.fn() };
});

import type { Assignment } from '@/shared/api';
import { createAssignment, transitionAssignment } from '@/shared/api';
import type { NewAssignment } from '@/features/create-assignment';
import { assignmentIntent, useCreateAssignment } from '@/features/create-assignment';
import type { AssignmentMove } from '@/features/transition-assignment';
import { moveIntent, useTransitionAssignment } from '@/features/transition-assignment';

type Create = { mutationFn: (input: NewAssignment) => Promise<Assignment> };
type Move = { mutationFn: (input: AssignmentMove) => Promise<Assignment> };

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const NEW: NewAssignment = {
  projectUid: `prj_${ULID}`,
  documentUid: `doc_${ULID}`,
  assigneeUserUid: `usr_${ULID}`,
  note: 'Проверить разделы АР',
};
const MOVE: AssignmentMove = { assignmentUid: `asg_${ULID}`, kind: 'started' };

const create = vi.mocked(createAssignment);
const move = vi.mocked(transitionAssignment);

function holdOpen(mock: typeof create | typeof move) {
  const handle = { settle: (_value: unknown) => {}, fail: (_error: unknown) => {} };
  mock.mockImplementation(
    () =>
      new Promise((resolve, reject) => {
        handle.settle = resolve;
        handle.fail = reject;
      }) as never,
  );
  return handle;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('a double press of «Назначить»', () => {
  it('sends ONE request, and both presses get its answer', async () => {
    const open = holdOpen(create);
    const hook = useCreateAssignment() as unknown as Create;
    const first = hook.mutationFn(NEW);
    const second = hook.mutationFn(NEW);
    expect(create).toHaveBeenCalledTimes(1);
    const stored = { assignment_uid: `asg_${ULID}` };
    open.settle({ data: stored });
    await expect(first).resolves.toBe(stored);
    await expect(second).resolves.toBe(stored);
    expect(create).toHaveBeenCalledTimes(1);
  });

  it('gives both presses the same refusal', async () => {
    const open = holdOpen(create);
    const hook = useCreateAssignment() as unknown as Create;
    const first = hook.mutationFn(NEW);
    const second = hook.mutationFn(NEW);
    expect(create).toHaveBeenCalledTimes(1);
    const refusal = new Error('assignment_open');
    open.fail(refusal);
    await expect(first).rejects.toBe(refusal);
    await expect(second).rejects.toBe(refusal);
    expect(create).toHaveBeenCalledTimes(1);
  });

  it('sends a new request for a press after the first settled', async () => {
    create.mockResolvedValue({ data: {} } as never);
    const hook = useCreateAssignment() as unknown as Create;
    await hook.mutationFn(NEW);
    await hook.mutationFn(NEW);
    expect(create).toHaveBeenCalledTimes(2);
  });

  it('does not join a request for another expert, scope or note', () => {
    holdOpen(create);
    const hook = useCreateAssignment() as unknown as Create;
    void hook.mutationFn(NEW);
    void hook.mutationFn({ ...NEW, assigneeUserUid: `usr_${ULID.slice(0, 25)}C` });
    void hook.mutationFn({ ...NEW, documentUid: null });
    void hook.mutationFn({ ...NEW, note: 'Другое поручение' });
    expect(create).toHaveBeenCalledTimes(4);
  });

  it('counts a note that differs only by surrounding spaces as the same intent', () => {
    holdOpen(create);
    const hook = useCreateAssignment() as unknown as Create;
    void hook.mutationFn(NEW);
    void hook.mutationFn({ ...NEW, note: `  ${NEW.note}  ` });
    expect(create).toHaveBeenCalledTimes(1);
    expect(assignmentIntent({ ...NEW, note: `  ${NEW.note}  ` })).toBe(assignmentIntent(NEW));
  });

  it('tells every field of the intent apart', () => {
    const intents = [
      NEW,
      { ...NEW, projectUid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8D' },
      { ...NEW, documentUid: null },
      { ...NEW, assigneeUserUid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8D' },
      { ...NEW, note: '' },
    ].map(assignmentIntent);
    expect(new Set(intents).size).toBe(intents.length);
  });
});

describe('a double press of an assignment move', () => {
  it('sends ONE request, and both presses get its answer', async () => {
    const open = holdOpen(move);
    const hook = useTransitionAssignment() as unknown as Move;
    const first = hook.mutationFn(MOVE);
    const second = hook.mutationFn(MOVE);
    expect(move).toHaveBeenCalledTimes(1);
    const stored = { assignment_uid: MOVE.assignmentUid, status: 'in_progress' };
    open.settle({ data: stored });
    await expect(first).resolves.toBe(stored);
    await expect(second).resolves.toBe(stored);
    expect(move).toHaveBeenCalledTimes(1);
  });

  it('gives both presses the same refusal', async () => {
    const open = holdOpen(move);
    const hook = useTransitionAssignment() as unknown as Move;
    const first = hook.mutationFn(MOVE);
    const second = hook.mutationFn(MOVE);
    expect(move).toHaveBeenCalledTimes(1);
    const refusal = new Error('state_transition_not_allowed');
    open.fail(refusal);
    await expect(first).rejects.toBe(refusal);
    await expect(second).rejects.toBe(refusal);
    expect(move).toHaveBeenCalledTimes(1);
  });

  it('sends a new request for a press after the first settled', async () => {
    move.mockResolvedValue({ data: {} } as never);
    const hook = useTransitionAssignment() as unknown as Move;
    await hook.mutationFn(MOVE);
    await hook.mutationFn(MOVE);
    expect(move).toHaveBeenCalledTimes(2);
  });

  it('does not join another move on the same assignment, nor the same move on another one', () => {
    holdOpen(move);
    const hook = useTransitionAssignment() as unknown as Move;
    void hook.mutationFn(MOVE);
    void hook.mutationFn({ ...MOVE, kind: 'cancelled' });
    void hook.mutationFn({ ...MOVE, assignmentUid: `asg_${ULID.slice(0, 25)}C` });
    expect(move).toHaveBeenCalledTimes(3);
  });

  it('does not join the same move with another reason or another new assignee', () => {
    holdOpen(move);
    const hook = useTransitionAssignment() as unknown as Move;
    const returned: AssignmentMove = { ...MOVE, kind: 'returned', reason: 'Не хватает документов' };
    void hook.mutationFn(returned);
    void hook.mutationFn({ ...returned, reason: 'Другая причина' });
    void hook.mutationFn({ ...MOVE, kind: 'reassigned', newAssigneeUserUid: `usr_${ULID}` });
    void hook.mutationFn({ ...MOVE, kind: 'reassigned', newAssigneeUserUid: `usr_${ULID.slice(0, 25)}C` });
    expect(move).toHaveBeenCalledTimes(4);
  });

  it('counts a reason that differs only by surrounding spaces as the same intent', () => {
    holdOpen(move);
    const hook = useTransitionAssignment() as unknown as Move;
    const returned: AssignmentMove = { ...MOVE, kind: 'returned', reason: 'Не хватает документов' };
    void hook.mutationFn(returned);
    void hook.mutationFn({ ...returned, reason: '  Не хватает документов ' });
    expect(move).toHaveBeenCalledTimes(1);
    expect(moveIntent({ ...returned, reason: ' Не хватает документов ' })).toBe(moveIntent(returned));
  });

  it('sends no reason when it is blank', async () => {
    move.mockResolvedValue({ data: {} } as never);
    const hook = useTransitionAssignment() as unknown as Move;
    await hook.mutationFn({ ...MOVE, reason: '   ' });
    expect((move.mock.calls[0]?.[0] as { body: object }).body).toEqual({ kind: 'started' });
  });
});
