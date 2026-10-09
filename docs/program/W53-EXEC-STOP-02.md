# W53-EXEC-01 narrow stop: cancel during `validating`

Captured 2026-10-09 on the frozen SEAL contract. The W53 plan §3.1 and
Stage-B test list call for cancel from each state, but the sealed
`audit_run` state machine does not permit `validating → cancelled`.

Command:

```bash
python3 - <<'PY'
import json
m=json.load(open('contracts/domain/v1/state-machines.json'))['machines']['audit_run']
print(m['transitions'])
PY
```

Output:

```text
{'created': ['queued', 'cancelled'], 'queued': ['running', 'cancelled', 'failed'], 'running': ['validating', 'failed', 'cancelled'], 'validating': ['published', 'partial', 'failed']}
```

The Stage-B lane currently refuses cancel while validating with the
catalog's `state_transition_not_allowed`; the transaction must leave Run,
Job and Attempt unchanged. No Stage-B agent may add an undeclared edge or
partially cancel durable authority. The integrator asked the owner whether
to keep this refusal or open a separately reviewed contract reseal. The
other execution operations and cancellation from `created`, `queued` and
`running` continue. Full W53 acceptance cannot claim cancellation from
every state until the owner resolves this scope conflict and the chosen
behavior is tested.
