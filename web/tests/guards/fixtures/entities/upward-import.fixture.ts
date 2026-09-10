// FIXTURE - deliberately illegal. See deep-import.fixture.ts for why this exists.
//
// Violation: an upward import. `entities` may import `shared` and nothing above it.
import { FindingList } from '@/widgets/finding-list';

export const value = FindingList;
