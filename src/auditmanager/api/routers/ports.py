"""The narrow ports the routers depend on.

A router in this package holds **no business logic and no transaction**. It parses a
request, calls one port method, renders the frozen shape, and lets the error middleware
classify anything that goes wrong. Everything behind these protocols is chosen by the
composition root (``api/composition.py``, owned by the integrator in Gate C), which is
why this module declares protocols and constructs nothing.

Why ports at all, rather than importing the modules directly:

* **``auditmanager.runs`` and ``auditmanager.exports`` do not exist in this tree.**
  Session ``B5`` is building them in parallel with this one. :class:`RunPort` and
  :class:`CsvExportPort` are written against ``contracts/api/v1/openapi.json`` and
  ``docs/program/P02_SEAMS.md`` section 6 -- the same frozen declarations ``B5``'s
  public surface is being built against -- so if both sides hold to them the wiring is
  a Gate C formality.
* **Some shapes the frozen document required had no producer when this was written.**
  They were listed in ``src/auditmanager/api/README.md`` and reported to the integrator
  rather than patched into another module; that table now records all eight as closed.
  Declaring a required shape on a port states the requirement precisely without widening
  another module's projection, and it is what let the requirement be met later without
  the routers changing at all.

Every method takes and returns plain values or the view types of
:mod:`auditmanager.api.schemas`. A port never takes a ``Session``: whether a call is
one transaction or several is the implementation's business, and a router that opened
one would have taken that decision away from it.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from auditmanager.api.schemas.decisions import DecisionEventView, DecisionRecordView
from auditmanager.api.schemas.documents import DocumentVersionView
from auditmanager.api.schemas.findings import FindingDetailView, FindingView
from auditmanager.api.schemas.projects import ProjectView
from auditmanager.api.schemas.runs import RunStatusView
from auditmanager.api.security import IssuedCredential

__all__ = [
    "AppendedDecision",
    "CredentialPort",
    "CsvExportPort",
    "DecisionPort",
    "DocumentPort",
    "FindingPort",
    "ProjectPort",
    "RunPort",
    "UploadedDocument",
]


class UploadedDocument(Protocol):
    """What an upload produced, and whether it created anything.

    ``replayed`` lets the router tell "created" from "already done" without comparing
    timestamps. Both answers are ``201`` -- the frozen document says the status covers
    "the project was created, **or** the recorded outcome of an identical earlier
    request was replayed" -- so this exists for diagnostics, not for the status line.
    """

    @property
    def version(self) -> DocumentVersionView: ...

    @property
    def replayed(self) -> bool: ...


class AppendedDecision(Protocol):
    """One appended event and the projection that now follows from the stream."""

    @property
    def event(self) -> DecisionEventView: ...

    @property
    def current_verdict(self) -> str: ...


@runtime_checkable
class ProjectPort(Protocol):
    """``createProject`` and ``listProjects``."""

    def create_project(self, *, name: str, idempotency_key: str) -> ProjectView:
        """Create a project, or replay the recorded outcome of an identical request."""

    def list_projects(self) -> Sequence[ProjectView]:
        """Every project, **newest first**.

        The order is part of this declaration, not a detail of the implementation: the
        router pages the sequence and never re-sorts it, so a port that returned oldest
        first would page correctly through the wrong listing. `listProjects` says newest
        first and `tests/integration/api/test_query_surface.py` asserts it over
        timestamps whose order is deliberately not the identity order.

        The edge cuts pages out of what this returns. No query surface in this tree
        accepts a cursor, and for PC-01 that is the right trade: see the query-surface
        section of ``src/auditmanager/api/README.md``. The signature does not change on
        the day it stops being the right trade.
        """


@runtime_checkable
class DocumentPort(Protocol):
    """``uploadDocument``, ``getDocumentVersion``, ``streamDocumentVersionContent``,
    ``listDocuments`` and ``listVersions``."""

    def upload_document(
        self,
        *,
        project_uid: str,
        content: bytes,
        source_filename: str,
        display_title: str | None,
        idempotency_key: str,
    ) -> UploadedDocument:
        """Publish one PDF as one immutable version, or explain why not."""

    def get_version(self, *, version_uid: str) -> DocumentVersionView:
        """One published version and its input manifest."""

    def list_documents(self, *, project_uid: str) -> Sequence[DocumentVersionView]:
        """The current version of every document in one project, **newest first**.

        The order is part of this declaration for the reason ``list_projects`` gives: the
        router pages what this returns and never re-sorts it.

        **An unknown project is ``not_found``, never an empty page.** The two are
        different facts -- "this project has nothing in it yet" is a reassuring and wrong
        thing to say about a project that does not exist -- and an implementation that
        returned ``()`` for an unknown identity would make the distinction unobservable
        at the wire.

        Items are ``DocumentVersion`` because that is what ``upload_document`` publishes
        into this same collection. There is no ``Document`` shape in the frozen contract
        and this declaration does not invent one.
        """

    def list_versions(self, *, document_uid: str) -> Sequence[DocumentVersionView]:
        """Every published version of one document, **newest first**.

        An unknown document is ``not_found``, for the reason above. A document with a
        published version always has at least one item, so an empty page here means the
        document exists and has published nothing -- which through this surface
        cannot happen, because ``uploadDocument`` creates the document and its first
        version in one transaction.
        """

    def read_content(self, *, version_uid: str) -> bytes:
        """The source bytes of one published version.

        Returns **bytes**, never a URL. The frozen document is explicit: the server
        streams the bytes itself, because a presigned link is the internal address the
        contract forbids in a response and would outlive the request that authorised
        it. A ranged request is served by slicing what this returns, so the object key
        stays inside ``auditmanager.storage``'s adapter where ``A3`` put it.
        """


@runtime_checkable
class RunPort(Protocol):
    """``startRun``, ``getRunStatus`` and ``listRuns``. Produced by ``B5``.

    The success terminal is ``published``; an implementation that reported
    ``succeeded`` would be reporting a ``StageResult`` status on the wrong aggregate.
    """

    def start_run(
        self,
        *,
        version_uid: str,
        provider_mode: str | None,
        idempotency_key: str,
    ) -> RunStatusView:
        """Start a run, or return the existing one for this key and payload.

        A new key over a terminal run creates a new run and leaves the terminal one
        exactly as it was: a terminal run is never reopened. The same key with a
        different payload is ``idempotency_key_reuse`` and creates nothing.
        """

    def get_run_status(self, *, run_id: str) -> RunStatusView:
        """Current run state and per-stage state."""

    def run_exists(self, *, run_id: str) -> bool:
        """Is there such a run? `D-74`.

        ``listRunFindings`` has to prove its parent exists before it renders an empty page
        -- `D-67` -- and until this method existed it proved it by calling
        :meth:`get_run_status`, which assembles the run row, **every stage result** and the
        run's **cost** to answer a yes/no.

        **A bool, not a refusal.** Whether an absent parent is a ``404`` is the frozen
        contract's statement about a particular operation, so it belongs in the router that
        declares it -- which is where `D-67` put it and where it stays. A port method that
        raised would take that decision away from the operation and make the two answers
        indistinguishable from an implementation that happened to fail.

        **Every implementation must have it.** A router calling a method an implementation
        lacks is an ``AttributeError`` and a ``500``, visible only on the wiring that is
        missing it; ``tests/integration/composition/test_every_port_implementation_is_whole.py``
        is the guard, and it derives the set of implementations from the tree.
        """

    def list_runs(self, *, version_uid: str) -> Sequence[RunStatusView]:
        """Every run of one published version, **newest first**.

        The version is the parent because ``start_run`` takes a ``version_uid`` and
        nothing else that identifies anything: the project is derived from it. So this is
        the inverse of the create direction rather than a second way of addressing runs.

        **An unknown version is ``not_found``, never an empty page** -- an empty page
        would say "this document has never been analysed" about a document that does not
        exist.

        Each item is the **whole** ``RunStatus``, identical to what ``get_run_status``
        returns for that run. A list item that were a subset would be a second shape of
        the same resource, and the first thing a second shape does is drift.
        """


@runtime_checkable
class FindingPort(Protocol):
    """``listRunFindings`` and ``getFinding``.

    Every finding these return is grounded. An ungrounded model item is not a finding,
    carries no ``finding_uid`` and must not appear here.
    """

    def list_run_findings(
        self,
        *,
        run_id: str,
        category: str | None,
        verdict: str | None,
    ) -> Sequence[FindingView]:
        """The published findings of one run, in a stable total order.

        ``category`` and ``verdict`` are ``None`` when the caller supplied no filter, and
        otherwise a value the router has already checked against the frozen enum -- an
        implementation never re-validates them and never widens them.

        **An implementation that accepts these and ignores them is the defect this
        signature exists to prevent**, and it is not hypothetical: the shipped adapter
        once took ``**_`` and dropped both, so `?category=explicit_placeholder` returned
        every finding and looked like it had worked. A filter accepted and ignored is
        worse than one refused, because the refusal is visible.
        """

    def get_finding(self, *, finding_uid: str) -> FindingDetailView:
        """One finding with its observation, evidence, provenance and projection."""

    def finding_exists(self, *, finding_uid: str) -> bool:
        """Is this a published finding? `D-74`.

        ``listDecisionHistory`` proves the finding in its path exists before rendering its
        ledger, and proved it by calling :meth:`get_finding` -- which reads the finding's
        evidence, its current verdict and **its whole decision history**, the very rows the
        handler's next line then reads a second time.

        A bool for the reason :meth:`RunPort.run_exists` gives, and an ungrounded
        observation is ``False``: it carries no ``finding_uid``, so there is nothing to
        decide on and nothing to render a history for.
        """


@runtime_checkable
class DecisionPort(Protocol):
    """``appendDecision``, ``listDecisionHistory`` and ``listDecisions``."""

    def append_decision(
        self,
        *,
        finding_uid: str,
        finding_observation_id: str,
        event_type: str,
        comment: str | None,
        idempotency_key: str,
    ) -> AppendedDecision:
        """Append exactly one event, whatever a replay under one key does.

        The database enforces the "exactly one" rather than the handler promising it:
        ``expert_decision_event`` carries at most one event per ``command_id``.
        """

    def decision_history(self, *, finding_uid: str) -> Sequence[DecisionEventView]:
        """The whole ledger for one finding, oldest first.

        Ordered by ``(recorded_at, decision_id)`` -- a total order, stable across
        pages. The server's ``sequence_no`` is never exposed, in a field or in a cursor.
        """

    def decision_journal(
        self,
        *,
        category: str | None,
        verdict: str | None,
    ) -> Sequence[DecisionRecordView]:
        """Every recorded decision, across findings, **newest first**.

        The order is part of this declaration and not a detail of the implementation, for
        the reason ``list_projects`` states: the router pages what this returns and never
        re-sorts it, so a port that returned oldest first would page correctly through the
        wrong listing.

        ``category`` and ``verdict`` are ``None`` when the caller supplied no filter, and
        otherwise a value the router has already checked against the frozen enum. They
        narrow the **finding** -- its category, and the verdict that now stands for it --
        exactly as the identically named parameters do on ``list_run_findings``, and
        neither narrows the event. **An implementation that accepts these and ignores them
        is the defect this signature exists to prevent**, and it is not hypothetical: the
        shipped finding adapter once took ``**_`` and dropped both.

        There is no parent identity, so there is no ``not_found``: a deployment that has
        decided nothing returns an empty sequence, and that is a true answer rather than a
        missing one.
        """


@runtime_checkable
class CsvExportPort(Protocol):
    """``exportRunCsv``. Produced by ``B5``.

    The router adds nothing to what this returns: no rendering, no column list, no
    policy. ``P02_SEAMS.md`` section 6 freezes the seventeen columns, the byte
    conventions and the export policy, and the discriminator is the frozen
    ``terminal_semantics.publishes_result`` flag rather than a hand-written state list.
    """

    def export_run_csv(self, *, run_id: str) -> bytes:
        """The CSV bytes for one run.

        Raises ``state_transition_not_allowed`` when the run's terminal does not
        publish a result -- a non-terminal run, or the terminal ``failed``. A
        ``partial`` run **is** exported, with the degraded state carried explicitly in
        the ``run_state`` column. ``partial_result_not_publishable`` is never emitted.
        Nothing is created, so a repeat returns byte-identical bytes.
        """


@runtime_checkable
class CredentialPort(Protocol):
    """``issueToken`` and ``changePassword``, and the epoch read the seam performs.

    Three methods. The port still cannot read a password digest, cannot write one and
    cannot list users: everything it offers is "here is a login and a password, mint a
    credential or do not", "here is a proven subject and two passwords, replace one",
    and "here is an identity, what generation of credentials does it accept". Registration
    is still the next piece of work and this port still does not guess at its shape.

    The token is minted **behind** this port rather than in the router, because minting
    needs the deployment's signing key and a router that held one would be a router that
    reads configuration -- which is the composition root's job and nobody else's.

    :meth:`epoch_of` is here rather than on a seventh port because it is the same adapter's
    job: the one object in the tree that holds both the user repository and the signer is
    the only one that can answer it, and a second port over the same two halves would be a
    second thing for the composition root to forget to wire. It is also what
    :class:`auditmanager.api.security.CredentialEpochs` asks for, structurally -- the seam
    declares the single method it needs and this port satisfies it, so the seam does not
    import the router's vocabulary to be handed one value.
    """

    def issue(self, *, login: str, password: str) -> IssuedCredential | None:
        """A credential for the subject these credentials name, or ``None``.

        ``None`` covers an unknown login, a wrong password, and a login this deployment
        would never have stored. The three are one answer on purpose: two answers would let
        anyone with the exchange form enumerate which accounts exist. The implementation is
        expected to spend comparable work on all three, because a timing difference is the
        same oracle with extra steps.

        A ``DomainError`` is for the cases that are *not* a refused credential -- a database
        that cannot be reached, a stored credential this deployment cannot parse. Reporting
        one of those as "wrong password" would hide a defect behind the most plausible
        explanation available, which is the silent fallback `AGENTS.md` section 4 forbids.
        """

    def change_password(
        self, *, user_uid: str, current_password: str, new_password: str
    ) -> IssuedCredential | None:
        """Replace a proven subject's password and hand back a credential that still works.

        ``None`` when the current password is not theirs -- the same single answer the
        exchange gives, and for the same reason.

        **The subject is an identity, never a login and never a body field.** It comes from
        the credential the seam verified, so this operation can only ever change the
        password of the caller who proved themselves. A login in the body would be an
        operation one reviewer could aim at another.

        The returned credential is minted **after** the change and under the new epoch, so
        it is the only credential in the world that this account now accepts: the one the
        caller presented to make this request is revoked by the same statement that wrote
        the new digest. A ``DomainError`` with ``VALIDATION_FAILED`` is the answer when the
        new password is the current one or fails the mechanical bounds.
        """

    def epoch_of(self, user_uid: str) -> int | None:
        """The generation of credentials this account accepts, or ``None`` for no account.

        Read by the authorization seam on every request it guards; see
        :class:`auditmanager.api.security.CredentialEpochs` for why ``None`` refuses rather
        than admits, and why nothing caches the answer.
        """
