"""The precedent core: a pure, model-free reading of the expert decision memory for one finding (`plan-v5`, «Прецеденты»).

Inputs and outputs are plain data. Nothing here touches a database, a file or the network, and nothing here imports another bounded context:
the consumers (the precedent pass, the executor-context handler, the history replay tool) read their own stores, build the values of
:mod:`auditmanager.precedents.models` and call the functions of :mod:`auditmanager.precedents.public`. Similarity is a precomputed cosine
given as input; without a vector the answer is «unavailable», never a guess from words.
"""
