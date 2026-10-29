# CMP-NOTE-265 — exact notes for comparison-only choices

Task: [`CMP-NOTE-265`](tasks/CMP-NOTE-265.md). Base: C2 publication candidate `8f23322df1ced8aaa253b2b495e76993104e41af`. This branch is separate from that candidate and has no publication authority.

The specification chooser now says why **«Спецификация и цены»** are unavailable for a comparison-only current version. The optimisation chooser names the unavailable **proposal pass**. The blocks picker names the unavailable **blocks read**. None of these three notes says a Run was started or that the server would reject this action by `comparison_only_version`; that existing refusal applies to actual Run starts. The shared Run-start note and its Run-list caller remain unchanged.

The three choices still show the comparison-only mark, stay disabled, and retain the visible reason in `aria-describedby`. The existing rendered picker suite now checks each screen's exact note and the absence of the Run-start note. It also keeps the ordinary, absent and unknown upload kinds unchanged.

Checks: targeted Vitest **48 passed**; web ESLint and TypeScript typecheck passed; `git diff --check` passed. No API/domain contract, migration, server handler, root dependency/lockfile, composition root, global style or other screen changed. Merge after the exact C2 candidate is published to `origin/dev`, then close D-265 in the integrated debt register. No `origin/main` action is authorized.
