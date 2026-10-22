STATUS: secret door and key form done (unit test green); next connection commands and the tabs (12:38 +05)

# EXEC-HTTP-01 web half — report (AGENTS.md §5)

Executor of the UI half of EXEC-HTTP-01 on branch agent/exec-web-01 (base agent/exec-line-01 dfe5795a).
Touches only web/**. Written up piece by piece; the final form is at the end of this file.

## Pieces

1. «Диспетчер»: the word «исполнитель» became «ответственный» in the three rendered strings
   (assignment board column, assignment history line, the reassign field of the actions).

2. The reserved BFF door `POST /bff/v1/executor-secret/<connection_id>` (route.ts) and the key form
   (`features/set-executor-secret`, a server component), with `executor-secret-door.test.ts`.
3. The `executor-connection` entity (reads, words, readiness, 7-day changes, refusal sentences) and the
   three `queryKeys.execution` keys.
