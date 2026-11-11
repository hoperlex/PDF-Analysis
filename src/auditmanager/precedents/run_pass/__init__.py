"""The «Прецеденты» pass over a run's findings and the two reads behind it (`PREC-PASS`, `ADR-0029` decisions 4 to 6).

The part of the precedents context that touches the stores, kept in a subpackage of its own so that the core above it stays pure (as ``vectors`` and
``setting_journal`` are): the reads of the run, its probes and the memory (``reads``), the writes of the pass (``store``), the critic's records mapped to
the core's inputs (``critic_input``, pure), the assembly of an evaluation and what a reader is shown of it (``evaluation``), the pass itself (``runner``)
and the two reads of the surface (``service``). Other contexts reach it through ``auditmanager.precedents.public``.
"""
