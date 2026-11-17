# `decisions` boundary

Append-only ExpertDecision/discussion events and projection ports. Knowledge views rebuild from events.

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.

## Authorship

Every event stores two things about who took it:

- `author_label` -- the display name other reviewers read (`R-37`); a string, not an identity;
- `author_user_uid` -- the account (`W49-DECISIONS-01`, column from migration `0015`, `RESTRICT`
  foreign key to `app_user`). Written as given, never coerced; a malformed or unknown identity
  is a refused append.

A NULL `author_user_uid` is history -- "author account unknown" -- and is listed by
`decision_history` and `decision_journal` like any other event, never as a fault. The account
is not on the wire (`DecisionEvent` is unchanged). The router supplies it from `W49-SEAL-01` on;
until then the ledger accepts `None`.

## Restart carry (`RUN-RESTART-01`, `R-155b`)

`restart_carry.py` carries the decisions of a restarted run's lineage to the findings of the run that replaced it, automatically and without an
expert's confirmation (the one departure from the confirm-only carryover of `carryover.py`). `carry_restart_decisions` is idempotent, one command
per carried event, and writes a `command_record` marker when the carry is complete; `pending_restart_carries` lists the published restart runs
that have no marker. The matching rules, what is a source and what is left alone are in the module docstring.
