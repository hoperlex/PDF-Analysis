# Checkpoint registry

| CP | Tag | Entry requirement | Manual runbook | Status |
|---|---|---|---|---|
| CP-00 | `v0.0.0-architecture` | S00 complete | `manual-tests/CP-00_architecture.md` | planned |
| CP-01 | `v0.1.0-foundation` | reproducible toolchain/local services | `manual-tests/CP-01_foundation.md` | planned |
| CP-02 | `v0.2.0-walking-skeleton` | fake E2E route | `manual-tests/CP-02_walking_skeleton.md` | planned |
| CP-03 | `v0.3.0-audit-alpha` | real stage/evidence | `manual-tests/CP-03_audit_alpha.md` | planned |
| CP-04 | `v0.4.0-audit-beta` | core audit pipeline | `manual-tests/CP-04_audit_beta.md` | planned |
| CP-05 | `v0.5.0-expert` | decisions/KB | `manual-tests/CP-05_expert.md` | planned |
| CP-06 | `v0.6.0-comparison-core` | deterministic compare | `manual-tests/CP-06_comparison_core.md` | planned |
| CP-07 | `v0.7.0-comparison-advanced` | AI/graphic layers | `manual-tests/CP-07_comparison_advanced.md` | planned |
| CP-08 | `v0.8.0-distributed` | remote worker recovery | `manual-tests/CP-08_distributed.md` | planned |
| CP-09 | `v0.9.0-hardening` | production gates | `manual-tests/CP-09_hardening.md` | planned |
| CP-10 | `v1.0.0` | release acceptance | `manual-tests/CP-10_release.md` | planned |

## Evidence folder convention (created during development)

```text
artifacts/checkpoints/CP-04/
  checkpoint-report.md
  contract-manifest.yaml
  automated-summary.txt
  manual-test-report.md
  migration-head.txt
  build-info.json
  known-risks.md
  restore-or-rollback-note.md
```

Не коммитить production payloads/screenshots with sensitive data. For committed evidence use synthetic/anonymized artifacts; protected CI/artifact store can hold restricted evidence according to retention policy.
