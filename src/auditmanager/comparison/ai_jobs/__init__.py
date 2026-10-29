"""The shared core of the consented AI jobs of the version comparison (`CMP-AI-JOBS-01`).

Read ``service.py`` for the commands, the state edges and the worker's side; ``estimate.py`` for the estimate protocol and its
digest; ``model.py`` for the vocabulary a method is written in (``AiMethod``, ``AiCounts``, ``WorkItemSpec``); ``repository.py`` for
the only writer of ``comparison_ai_job``; ``recorded.py`` for recorded mode. The API section of
``docs/program/CMP-AI-JOBS-01.md`` is what the four method lanes follow. Other contexts import this package only through
``comparison/public.py``.
"""
