"""The process entry point.

Importing this module builds the application, so an import that succeeds is a process that
can serve. That is the deliberate shape of the Gate C contract - a missing dependency fails
at construction - and it is why there is no lazy accessor here: a module-level ``get_app()``
that built on first call would move the failure back to the first request.
"""

from __future__ import annotations

import sys

from auditmanager.api.composition import Application, ConfigurationError, build_application


def create_app(environ: dict[str, str] | None = None) -> Application:
    """Build the application or raise. Never returns a half-wired one."""
    return build_application(environ=environ)


def main(argv: list[str] | None = None) -> int:
    """Construct everything and report what was wired, without serving.

    PC-01 needs no HTTP server to prove composition: the acceptance runbook drives the
    router directly. This entry point exists so an operator can ask "would this process
    start?" and get an answer that costs nothing and touches no request.
    """
    del argv
    try:
        app = create_app()
    except ConfigurationError as failure:
        print(f"auditmanager: refusing to start: {failure}", file=sys.stderr)
        return 2
    print(f"auditmanager: wired, provider_mode={app.settings.provider_mode}")
    print(f"auditmanager: operations={len(app.router.routes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
