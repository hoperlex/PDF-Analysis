# W55A-FREEZE-01 — the W55a development freeze

**Integrator:** `pdf-analysis-62`, 2026-10-12.
**Base:** `integration/w54` with all W54 lanes and fixes merged, published to `origin/dev` with this commit.
**Plan:** `dispatch/W55-PLAN.md` Part A, as adopted (`R-100`).
**Rulings:** `R-111` … `R-115` (§3.31).

- **Checks** (`R-102`, `R-111`): every lane uses container-free light checks. All DB-backed tests and the single full gate run after W55a, together with W54's (`D-157`). The plan's "(full gate)" lane labels are replaced. Lanes still write their DB tests and list the exact commands.
- **The plan's refusal is waived by `R-111`.** The plan says to refuse the freeze unless W54 is merged and its worker lane is finished. W54 is merged and its worker lane is finished, but not DB-validated.
- **Migration:** `0020_norms_search`, owned by `W55A-SEAL-01`. W55b takes `0021_portal_bundles`.
- **The search timeout default** (`AUDITMANAGER_NORMS_SEARCH_TIMEOUT_MS`) is provisionally 3000 ms. It is re-fixed from the promotion-database measurement in `W55A-D124-MEASURE`.
- **Deferred to windows:**
  - `W55-PROMOTION-PRE-01`, `W55A-D124-MEASURE` and `W55A-REHEARSAL-01` need the promotion database, the build and night windows.
  - The `W55A-WEB-NORMS` live journey runs in the window.
- **Lanes now:**
  - Stage A: `W55A-SEAL-01`.
  - Stage B: `W55A-CONTENT-01`, `W55A-SEARCH-01` and `W55A-PIN-01` run one at a time, because they share `bootstrap/{adapters,composition}.py`.
  - `W55A-WEB-NORMS` runs in parallel with Stage B, after SEAL.
- **Ports (window):** SEAL `57210`/`60810-11`, CONTENT `57220`/`60820-21`, SEARCH `57230`/`60830-31`, PIN `57240`/`60840-41`.
