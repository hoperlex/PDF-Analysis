"""Which analysis produced a run, and the one predicate for «the result of a version» (`AR-V3-OPT-IN`, design 4.4).

Two analyses exist. The **standard** analysis is the text profile the sealed section table routes a version to
(`W59-SECTION-SEAL-01`); the **AR v3 beta** analysis is one run of a six-run group pinned to one sealed pair of
``analysis_profile_id`` and ``prompt_bundle_id`` (`AR_V3_BETA_PROFILE_ID`, `AR_V3_BETA_BUNDLE_ID`), in no registry
file. A run holds exactly one of them: the pair is written when the run is created and a database trigger checks the
group's members against the group's pair (migration 0032).

The kind is **derived from that pinned pair and from nothing else** -- never from a file name, a request field or a
profile's status. It is derived here once, for every reader:

* :func:`analysis_kind` -- the word a run carries on the wire (``RunStatus.analysis_kind``) and the Python-side test the
  comparison and optimisation adapters apply;
* :data:`STANDARD_RUN_SQL` -- the same test as a SQL condition for the readers that choose «the result run of a version»
  in the database (the audit state of a document and the schedule's facts). A new reader of «the newest published run»
  takes this condition or the Python test; it does not write a third spelling.

**The result of a version is the newest published or partial run of the standard analysis.** A published AR v3 member
is a run of its version, listed beside the others and readable by its own screens, but it never displaces the standard
run as the version's audit state, as the run a comparison reads by default or as the text an optimisation reads
(`Q3`, owner answer of 2026-11-07, recommended option). Which of the six members a future rule for a group would pick
is a design of its own (`Q-MD-9`, `D-303`) and is not guessed here.
"""

from __future__ import annotations

from typing import Final

from auditmanager.analysis.public import AR_V3_BETA_BUNDLE_ID, AR_V3_BETA_PROFILE_ID

#: ``RunStatus.analysis_kind`` values.
ANALYSIS_STANDARD: Final[str] = "standard"
ANALYSIS_AR_V3_BETA: Final[str] = "ar_v3_beta"
ANALYSIS_KINDS: Final[tuple[str, ...]] = (ANALYSIS_STANDARD, ANALYSIS_AR_V3_BETA)


def analysis_kind(analysis_profile_id: str | None, prompt_bundle_id: str | None) -> str:
    """``ar_v3_beta`` for exactly the sealed pair (as the executor's v3 branch reads it), ``standard`` for any other.

    The pair, not the profile alone: a run that held only one half of it would be neither analysis, and the database
    does not let one exist.
    """
    if (
        analysis_profile_id == str(AR_V3_BETA_PROFILE_ID)
        and prompt_bundle_id == str(AR_V3_BETA_BUNDLE_ID)
    ):
        return ANALYSIS_AR_V3_BETA
    return ANALYSIS_STANDARD


#: The SQL spelling of «this ``audit_run`` (alias ``r``) is of the standard analysis». Both ids are the sealed,
#: validated identifiers (``ap_`` / ``pb_`` followed by a ULID), so inlining them is not an injection surface and
#: lets a reader keep its own bind parameters.
STANDARD_RUN_SQL: Final[str] = (
    f"NOT (r.analysis_profile_id = '{AR_V3_BETA_PROFILE_ID}' AND r.prompt_bundle_id = '{AR_V3_BETA_BUNDLE_ID}')"
)

__all__ = ["ANALYSIS_AR_V3_BETA", "ANALYSIS_KINDS", "ANALYSIS_STANDARD", "STANDARD_RUN_SQL", "analysis_kind"]
