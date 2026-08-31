# Architecture exceptions

No active exceptions at bootstrap.

Every temporary exception must record:

| Field | Required |
|---|---|
| principle/ADR violated | yes |
| exact code/data scope | yes |
| reason + alternatives | yes |
| risk | yes |
| compensating control | yes |
| owner | yes |
| expiry date/checkpoint | yes |
| removal task | yes |

An exception without expiry is a new architectural decision and requires ADR.
