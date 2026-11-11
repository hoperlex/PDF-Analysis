"""The night encoder of the precedents' vectors (`EMBED-01`, `ADR-0029` decision 8): the window, the queue and the exchange with the host.

This is the one part of the ``precedents`` context that touches a store. The core beside it (``labels``, ``votes``, ``advice`` ...) stays a pure,
model-free reading; what is here moves the *encoder's* work:

* :mod:`~auditmanager.precedents.vectors.window` -- the window of the night and its states, as pure functions of a clock and a setting;
* :mod:`~auditmanager.precedents.vectors.intents` -- the text an encoder reads for a case, the request and the check of the answer;
* :mod:`~auditmanager.precedents.vectors.exchange` -- the directory the worker and the host's timer meet in (no database and no network on the
  host's side of it, and none for the container);
* :mod:`~auditmanager.precedents.vectors.repository` -- the SQL of the queue, the vectors and the control row;
* :mod:`~auditmanager.precedents.vectors.window_pass` -- the worker's pass that drives the window;
* :mod:`~auditmanager.precedents.vectors.control` -- the pause of the vectors and its read, behind the two routes of the surface.

Other contexts import ``auditmanager.precedents.public`` and nothing deeper.
"""
