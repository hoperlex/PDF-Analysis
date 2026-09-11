"""The API's view of the composition root.

`B6` reserved this module and `app.py` for the integrator and built ``build_router`` to
take six protocols and construct none of them. The construction lives in
``auditmanager.bootstrap``; this is the thin seam between them, so a router consumer never
imports the bootstrap package and the bootstrap package never imports a router internal.
"""

from __future__ import annotations

from auditmanager.bootstrap.composition import Application, build_application
from auditmanager.bootstrap.settings import AppSettings, ConfigurationError

__all__ = ["Application", "AppSettings", "ConfigurationError", "build_application"]
