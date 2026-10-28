"""The batch operations of a comparison upload (`CMP-INGEST-02`, ADR-0025 decisions 9, 10 and 16).

Over the upload of `CMP-INGEST-01` (declare, send, complete, propose, confirm) and the comparison queue of
`CMP-WORK-01`: list a project's batches, pause the batch after the set in hand and resume it, cancel it («Отменить
пакет»), leave a set out and queue a failed set again, put the page profiles of every confirmed set on the queue one
set at a time, and abort the store's open multipart uploads of a cancelled or abandoned batch.

The package is reached from outside through :mod:`auditmanager.ingest.comparison_batch.public` only. Its modules:

============== ====================================================================================================
``rules``      the command types, the two work kinds, the poll and grace times, the retryable set reasons
``repository`` the statements the upload's repository does not have: listing, cancel, pause flag, release mark
``lifecycle``  the state machine: release a set, complete, cancel, abandon (stateless, in the caller's transaction)
``handlers``   the two work handlers: ``comparison_batch_drive`` and ``upload_abort_sweep``
``service``    the use cases: list, exclude, retry, pause, resume, cancel, and the two hooks
``views``      what the listing answers with
============== ====================================================================================================
"""
