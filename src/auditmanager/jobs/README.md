# `jobs` boundary

AuditRun remains owned by ``auditmanager.runs``. This package owns the durable local
``Job``/``Attempt``/``Lease`` authority and the provider/artifact effect journals introduced by
``W48-DURABLE-01``. The current Attempt's opaque ``execution_token`` is checked under a database
lock inside every publishing transaction. Progress remains a projection, never a status source.

This is not a distributed scheduler: there is one local carrier, no remote worker protocol and no
automatic resume. A process crash leaves explicit lost/unresolved evidence for reconciliation.

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.
