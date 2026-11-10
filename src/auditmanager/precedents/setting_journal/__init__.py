"""The write side of the programme's switches and settings (`PREC-SETTINGS-01`, contract 1.51.0): the journal ``precedent_setting_event`` behind
``listPrecedentSettings`` and ``appendPrecedentSetting``.

A subpackage of its own, beside ``vectors``, for the reason ``vectors`` gives: the core of this context (the modules at its root) imports no other
bounded context and touches no ledger, and this part needs the command ledger (``ingest.public``), the roles (``access.public``) and the typed errors.
The reads of the journal and the guard on the switch a run's start reads stay in the core, ``precedents/settings.py``.

Other contexts import ``auditmanager.precedents.public`` and nothing deeper.
"""
