/**
 * `/logs` — the execution journal, prepared and not built.
 *
 * `R-23`'s addendum rules logs wanted and the preparation allowed now.
 *
 * Two things this screen is careful about, both from `docs/program/W43-PREP.md` note 3:
 *
 *   - **it is not the decision journal.** The contract says *journal* six times and every
 *     one of them is `listDecisions`, the expert's ledger, which is already a working
 *     screen at `/knowledge-base`. This section is the record of what the SERVER did, so
 *     the title says `Журнал выполнения` and never bare `Журнал`;
 *   - **the promise does not claim a table that is empty.** `audit_event` exists in the
 *     schema and nothing under `src/` ever writes it — its only writers in this
 *     repository are integration tests. So the promise says the server keeps its own
 *     records, which is true of stage results, model calls, state transitions and the
 *     process's own output, and stops there.
 *
 * What is in the way is stated plainly: no operation on the surface reads a log, so this
 * section costs a reseal and a decision about what is safe to publish — the contract's
 * standing rule is that no response ever carries a bucket name, object key, path, URL,
 * credential, prompt or model payload, and raw log lines are where those leak.
 */

import { RoutePlaceholder } from '@/shared/ui';

export function LogsPage() {
  return (
    <RoutePlaceholder
      screen="Журнал выполнения"
      route="/logs"
      promise="Здесь будет журнал выполнения прогона: что делал сервер, когда и чем это закончилось. Сервер ведёт свои записи, но операции, которая отдала бы их приложению, в договоре нет, поэтому сейчас этот журнал виден только тому, у кого есть доступ к самому серверу."
    />
  );
}
