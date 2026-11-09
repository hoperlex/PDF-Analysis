"""The expert decision memory: the capture core (`ADR-0027`, `DECISION-MEMORY-01`).

A case copies what an expert saw and said when a decision was taken, in the decision's own transaction, and outlives the project and the
document it came from. This package imports ``auditmanager.shared`` and ``auditmanager.storage.public`` only; the assembler that fills
a snapshot from the other contexts is the composition root's. Other contexts import ``auditmanager.decision_memory.public``.
"""
