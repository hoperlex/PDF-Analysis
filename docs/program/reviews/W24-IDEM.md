# `W24-IDEM` — running `deploy.sh` twice changes nothing

**Session `W24-IDEM`, branch `agent/w24-idem`, from `origin/dev` at `16d3503`.**

This file is opened before the first edit and filled as the work is measured, per the
session's integration contract. Nothing below is written before it is driven.

## 0. The question

`D-36`: a second `infra/deploy/deploy.sh` against an unchanged tree recreates `api`, `web`
and `migrate`, because a fully cached `compose build` still yields a new image ID. This is
the one part of `PA-01` criterion 1's row that `R-1` does not block — it is a claim about
image identity under an identical build, not about a server with a previous version on it.

## 1. Baseline

*(filled in section by section as each is measured)*
