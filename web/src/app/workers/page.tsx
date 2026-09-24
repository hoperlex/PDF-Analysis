/**
 * `/workers` — the route file for the executors section.
 *
 * Delegation-only: the route decides nothing.
 */

import { WorkersPage } from '@/_pages/workers';

export default function WorkersRoute() {
  return <WorkersPage />;
}
