"""The comparison durable queue (`CMP-WORK-01`, ADR-0025 decisions 4, 6, 7, 23).

Read ``repository.py`` for the lease and the state edges, ``runner.py`` for what the worker may
claim and when, ``registry.py`` for the one handler per kind, ``model.py`` for the vocabulary a
handler is written in. Other contexts import this package only through ``comparison/public.py``.
"""
