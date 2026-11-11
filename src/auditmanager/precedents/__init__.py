"""The precedent core: a pure, model-free reading of the expert decision memory for one finding (`plan-v5`, «Прецеденты»).

Inputs and outputs are plain data. Nothing here touches a database, a file or the network, and nothing here imports another bounded context:
the consumers (the precedent pass, the executor-context handler, the history replay tool) read their own stores, build the values of
:mod:`auditmanager.precedents.models` and call the functions of :mod:`auditmanager.precedents.public`. Similarity is a precomputed cosine
given as input; without a vector the answer is «unavailable», never a guess from words.

The one part of this context that does touch a store is :mod:`auditmanager.precedents.vectors` (`EMBED-01`, `ADR-0029` decision 8): the night encoder's
window, its queue of intents and the vectors it produces. It is a subpackage of its own so that the core above stays pure; nothing in the core imports it.

The other is :mod:`auditmanager.precedents.setting_journal` (`PREC-SETTINGS-01`): the administrator's write of the switches and settings, which needs the
command ledger and the roles. The core keeps the reads of that journal and the one guard on the switch a run's start reads (``settings.py``).
"""
