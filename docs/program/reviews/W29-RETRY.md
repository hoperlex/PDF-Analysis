# W29-RETRY — a missing file is not an outage

**Session** `W29-RETRY` · base `origin/dev` = `714da53` · branch `agent/w29-retry` ·
worktree `/root/w29retry` · lane `gate-w29a` (PostgreSQL 56040, MinIO 59640/59641,
database `audit_w29a`, bucket `auditmanager-gate-w29a`). No image built. `df -h /` on
arrival: **12 GB** free. Started 2026-09-21 16:11:33 +05:00.

`W28-LIVE` measured a run on a document with no recording: **16.1 s**, of which **10.0 s**
is the retry ladder, terminal `failed`. Ten of those sixteen seconds are spent waiting for
a file to appear on a local disk.

> **Status: in progress.** This file is opened before the first edit, as the integration
> contract requires. Sections fill as the work is done.

## 1. The question

`dependency_unavailable` is `retryable: true` in the frozen catalog and the retry policy is
right to ladder it: for a provider that is unreachable, a second attempt can answer
differently. The defect is not in the policy. It is in what the adapter **says about
itself** when a recording file is simply not there.

## 2. Where the repair belongs — pending

## 3. The sweep — pending

## 4. Shown to fail — pending

## 5. Characterization records — pending

## 6. The gate — pending
