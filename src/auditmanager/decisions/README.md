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
