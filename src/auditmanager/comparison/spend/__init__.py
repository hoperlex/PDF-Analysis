"""The comparison spend journal and the one way a comparison lane calls a model (`CMP-SPEND-01`).

Read ``caller.py`` for the protocol of a call, ``repository.py`` for the journal and its reads,
``ceilings.py`` for the USD rules, ``settler.py`` for what the queue's reclaim does with an attempt that
died mid-call, ``model.py`` for the vocabulary and ``errors.py`` for the typed refusals. Other contexts
import this package only through ``comparison/public.py``.
"""
