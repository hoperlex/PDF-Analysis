# Event contract area

Events contain event ID, type, version, aggregate/entity IDs, occurred-at/actor/source and minimal payload needed by the consumer. They do not clone full aggregates.

Durable business/security audit events and integration outbox events have explicit schemas/owners; diagnostic log messages are not events.
