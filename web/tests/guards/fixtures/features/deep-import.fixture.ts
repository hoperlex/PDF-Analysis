// FIXTURE - deliberately illegal. Ignored by `npm run lint`; linted on purpose by
// tests/guards/eslint-boundary.guard.test.ts, which asserts ESLint goes red here.
//
// Violation: a deep import past a slice's public API.
import { projectStore } from '@/entities/project/model/store';

export const value = projectStore;
