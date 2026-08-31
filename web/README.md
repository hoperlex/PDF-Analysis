# Web application

Target: Next.js + React + TypeScript strict + App Router.

`src/app` is a thin framework adapter. Product composition lives in `_pages`; reusable domain behavior follows FSD/vertical slices. Raw HTTP exists only in generated/shared transport. Do not create a global store for the whole domain.

Package/runtime versions and actual Next bootstrap are created in S01 by the single toolchain/web foundation owners.
