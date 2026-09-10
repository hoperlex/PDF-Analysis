# Web application

The PC-01 frontend: Next.js App Router, React, TypeScript under `strict: true`.

**Read `docs/PC01_UI_SEAM.md` before writing a slice.** It is the frozen seam — route
URLs, shared components, the transport surface, query-key namespaces, the polling
contract, and the ownership line between Gate B sessions `B7` and `B8`.

## Quick start

```
nvm use                       # 22.23.1, from .nvmrc
npm --prefix web ci           # install from the committed lockfile
cp web/.env.example web/.env.local
npm --prefix web run dev
```

`NEXT_PUBLIC_API_BASE_URL` is required and has no default. A missing value fails loudly
the first time something asks for it, rather than quietly pointing a build at nothing.

## Commands

Every command is `npm --prefix web run ...`. There is no `Makefile` target and there may
not be one: the nine targets are frozen by FF-01 and `OD-16` forbids a tenth for the
frontend.

| Command | What |
|---|---|
| `npm --prefix web ci` | install from `package-lock.json` |
| `npm --prefix web run dev` | development server |
| `npm --prefix web run build` | production build; a type error fails it |
| `npm --prefix web run typecheck` | `tsc --noEmit` |
| `npm --prefix web run lint` | ESLint, including the FSD boundary rules |
| `npm --prefix web run api:generate` | regenerate the API client from the contract |
| `npm --prefix web run api:verify` | verify the committed client matches; exit 1 on drift |
| `npm --prefix web run test` | guards and contract suites |
| `npm --prefix web run test:guards` | guards only |
| `npm --prefix web run test:contract` | contract suites only |

`test:unit`, `e2e:pc01` and `csv:verify` are reserved names that fail explicitly until
their owner lands. Fill one in; never rename one.

## Layout

```
src/app/          Next routes and the one global stylesheet. Adapters only — a page.tsx
                  delegates to a _pages public API and holds no domain logic.
src/_app/         Composition root: the query client and the application frame.
src/shared/       api/ (generated client + the one transport), config/, ui/, lib/.
src/_pages/       Screen composition.        } owned by Gate B sessions B7 and B8,
src/widgets/      Composite UI.              } one slice per directory, each reached
src/features/     User intentions.           } only through its public API
src/entities/     Domain models and queries. }
openapi/          Byte snapshot of the contract the client was generated from.
scripts/          The client generator and the reserved-script forwarder.
tests/guards/     Toolchain and boundary guards, each shown to fail under mutation.
tests/contract/   Contract drift and seam guards.
docs/             The frozen UI seam.
```

Imports run downward only — `app`/`_app` → `_pages` → `widgets` → `features` →
`entities` → `shared` — and reach a sibling slice only through its public API. ESLint
rejects anything else.

## The API client is generated

`src/shared/api/generated/**` is produced from `contracts/api/v1/openapi.json`, which is
read-only to this tree: it belongs to the seam session, and a client and a contract
reconciled by the same hand prove nothing. Every generated file carries a do-not-edit
header, and two guards enforce it — one comparing the committed bytes to a fresh
generation, one comparing the snapshot in `openapi/` to the contract itself.

Found a defect in the contract? Report it. Do not repair it here.

Raw HTTP exists in exactly one place, `src/shared/api/transport.ts`. There is no global
domain store: PC-01's state lives on the server.

## Pinning

Node, npm and every dependency are pinned to exact versions, with `save-exact=true` and
`engine-strict=true` in `.npmrc` so a later `npm install` cannot reintroduce a range.
`FRONTEND_LOCK.json` records the pins, the generator invocation and the exact OpenAPI
bytes the client was generated from; a guard recomputes every digest in it.
