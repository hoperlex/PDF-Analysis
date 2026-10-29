"""The MD summary of a version series and the PDF reports built from it (`CMP-VC-REPORT-01`, ADR-0025 decisions 3, 8, 10, 11, 17, 19, 24).

Read ``model.py`` for the vocabulary, ``summary.py`` / ``summary_source.py`` for the deterministic MD summary, ``parse.py`` and
``facts.py`` for the intake of an MD file, ``client.py`` and ``analytic.py`` for the two kinds of report (prompts, program checks,
views), ``pdf/`` for the PDF written by a program under a kernel ceiling, ``service.py`` for the thirteen operations and
``handler.py`` for the worker's side. Other contexts import this package only through ``comparison/public.py``.
"""
