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

from typing import BinaryIO, Protocol, Sequence, runtime_checkable

from auditmanager.api.schemas.accounts import AccountView, PersonNamesView
from auditmanager.api.schemas.blocks import (
    PortalBlockIndexView,
    PortalCropContent,
    VersionBlockIndexView,
)
from auditmanager.api.schemas.content import ByteRange, StreamedContent
from auditmanager.api.schemas.dashboard import DashboardSummaryView
from auditmanager.api.schemas.decisions import DecisionEventView, DecisionRecordView
from auditmanager.api.schemas.documents import DocumentVersionView
from auditmanager.api.schemas.findings import FindingDetailView, FindingView
from auditmanager.api.schemas.projects import ProjectView
from auditmanager.api.schemas.registrations import RegistrationListingView, RegistrationView
from auditmanager.api.schemas import models
from auditmanager.api.schemas.models import ProductVersion, ReleaseList
from auditmanager.api.schemas.runs import RunStatusView
from auditmanager.api.security import AccountStanding, IssuedCredential

__all__ = [
    "AccountPort",
    "AppendedDecision",
    "BlockPort",
    "CredentialPort",
    "CsvExportPort",
    "DashboardPort",
    "DecisionPort",
    "DispatchPort",
    "DocumentPort",
    "FindingPort",
    "NormContentPort",
    "NormsSearchPort",
    "ProjectPort",
    "RegistrationPort",
    "ReleasesPort",
    "RunPort",
    "ExecutionPort",
    "SectionPort",
    "ComparisonPort",
    "AnalysisProfilePort",
    "OptimisationPort",
    "SectionSpecificationPort",
    "SpecificationPricesPort",
    "OptimisationProposalPort",
    "UploadedDocument",
    "XlsxExportPort",
]


class ExecutionPort(Protocol):
    """W53 execution reads and commands. Implementation is supplied in Stage B."""

    def list_queue(self, *, cursor: str | None, limit: int) -> models.ExecutionQueuePage: ...
    def list_journal(
        self, *, run_id: str | None, cursor: str | None, limit: int
    ) -> models.ExecutionJournalPage: ...
    def cancel_run(
        self, *, run_id: str, user_uid: str, idempotency_key: str
    ) -> RunStatusView: ...
    def reaudit_run(
        self, *, run_id: str, user_uid: str, idempotency_key: str
    ) -> RunStatusView: ...
    def set_job_priority(
        self, *, job_id: str, priority: int, user_uid: str, idempotency_key: str
    ) -> models.ExecutionQueueItem: ...
    def set_paused(
        self, *, paused: bool, user_uid: str, idempotency_key: str
    ) -> models.ExecutionDispatchStatus: ...
    # `W54-SEAL-01`. The worker registry (plan section 3.7). Sealed as stubs that answer
    # `503 dependency_unavailable`; `W54-WORKER-01` supplies the behaviour.
    def list_workers(
        self, *, cursor: str | None, limit: int
    ) -> models.ExecutionWorkerPage: ...
    def set_worker_intake(
        self, *, worker_id: str, enabled: bool, user_uid: str, idempotency_key: str
    ) -> models.ExecutionWorker: ...


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
    """``uploadDocument``, ``uploadDocumentVersion``, ``getDocumentVersion``,
    ``streamDocumentVersionContent``, ``listDocuments`` and ``listVersions``."""

    def upload_document(
        self,
        *,
        project_uid: str,
        content: BinaryIO,
        source_filename: str,
        display_title: str | None,
        idempotency_key: str,
        section: str | None = None,
    ) -> UploadedDocument:
        """Publish one portal bundle as one immutable version, or explain why not.

        ``content`` is the uploaded ZIP as a **file handle**, positioned at its start and
        readable once: the router hands over the parsed part's own handle and does not read
        it (`W55B-SEAL-01`, plan section B3.2). An implementation that needs the bytes whole
        says so by reading them itself -- `DocumentAdapter` still does until
        `W55B-STREAM-01` and `W55B-INGEST-01` read the archive member by member -- so that
        the cost is visible in the one place that pays it, not hidden in the signature. It
        neither closes the handle nor keeps it after returning.

        ``section`` is one of `R-40`'s fifteen project-section codes, or ``None`` when
        the caller does not supply one -- optional here for the same reason
        ``display_title`` is: the frozen ``UploadDocumentRequest.section`` is not
        required, and this port does not invent a value the caller never gave it.
        """

    def upload_document_version(
        self,
        *,
        project_uid: str,
        document_uid: str,
        content: BinaryIO,
        source_filename: str,
        idempotency_key: str,
    ) -> UploadedDocument:
        """Publish one portal bundle as the next immutable version of an existing document.

        `W59-VERSION-UPLOAD-01`. The same handle contract and envelope as
        :meth:`upload_document`. The document must exist and belong to ``project_uid``
        (``not_found`` naming ``Document`` otherwise, an unknown project naming
        ``Project``); the version takes the document's next ordinal and becomes its current
        version; it takes no title and no section, and starts unclassified.
        """

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

    def stream_content(
        self, *, version_uid: str, byte_range: ByteRange | None
    ) -> StreamedContent:
        """The source bytes of one published version, in chunks. `W55A-SEAL-01` (R-115).

        ``byte_range`` is the parsed ``Range`` header, or ``None`` for the whole object. The
        implementation resolves it against the version's recorded size
        (:meth:`ByteRange.resolve`, ``422`` when unsatisfiable) and **opens the object
        before returning**, so a missing version is ``404`` and a storage failure a typed
        ``500``/``503`` before the status line is sent. It never loads the object whole:
        chunks are at most :data:`~auditmanager.api.schemas.content.CONTENT_CHUNK_BYTES`.

        A full read hashes while streaming and holds back its last chunk until the digest
        matches the manifest; on a mismatch it logs ``storage_integrity_error`` and stops,
        so the client receives fewer bytes than ``Content-Length``. A ranged read relies on
        the recorded verification (publication and ``verify_version``).

        Sealed by `W55A-SEAL-01`; `W55A-CONTENT-01` supplies the streaming implementation and
        moves ``streamDocumentVersionContent`` onto it. Until then the router still calls
        :meth:`read_content`.
        """


@runtime_checkable
class BlockPort(Protocol):
    """``getVersionBlocks``. `W45-BLOCKS`.

    A separate protocol rather than a sixth ``DocumentPort`` method, so that no existing
    implementation of ``DocumentPort`` -- the shipped one or any of the three test-only
    wirings -- is made incomplete by an operation none of them answer yet. ``build_router``
    takes it as ``blocks: BlockPort | None = None``, the same optional-with-a-default shape
    ``credentials`` already has, for the same reason: a caller that never passes it does not
    have to change.
    """

    def get_block_index(self, *, version_uid: str) -> VersionBlockIndexView:
        """The page-by-page block index for one version, or its not-yet-produced status.

        **Keyed by the version, not by a run.** The stage that derives this geometry
        carries no model and no provider reference, so its output is a deterministic
        property of the version -- identical across every run that reaches it -- and this
        reads the most recently produced one rather than asking a caller to already hold a
        ``run_id``.

        **An unknown version is ``not_found``.** A version that exists but has no run whose
        ``page_geometry_extraction`` stage succeeded answers with
        ``status="not_produced"`` and ``blocks=()`` -- *absent*, never silently rendered
        the same as a version whose geometry was produced and genuinely has none
        (``status="produced"``, ``blocks=()``). An implementation that returned the empty
        tuple for both without varying ``status`` would have destroyed exactly the
        distinction this method exists to carry.
        """

    def list_portal_blocks(self, *, version_uid: str) -> PortalBlockIndexView:
        """Every portal block of one version's bundle, or its not-yet-produced status.
        `W55B-SEAL-01`; the behaviour is `W55B-GEOMETRY-01`'s.

        Read from the most recent run of the version whose ``page_geometry_extraction``
        succeeded, for the reason :meth:`get_block_index` gives. ``blocks`` arrive **already
        ordered** by page, ordinal (a null one last) and ``portal_block_id``; the router
        pages them and never re-sorts. An unknown version is ``not_found``; a version no run
        of which produced portal geometry is ``status="not_produced"`` with no blocks --
        never the same answer as a produced geometry that holds none.
        """

    def read_portal_block_crop(
        self, *, version_uid: str, portal_block_id: str
    ) -> PortalCropContent:
        """The PNG this product cut for one IMAGE block. `W55B-SEAL-01`; behaviour
        `W55B-GEOMETRY-01`'s.

        ``not_found`` for an unknown version, for a ``portal_block_id`` the version does
        not hold, and for a block that has no crop (not an IMAGE block, or its page is
        ``geometry_mismatch``): every one is the same fact for the caller -- there is no
        such image. The bytes are verified against the recorded SHA-256 before they are
        returned; a mismatch is ``storage_integrity_error``, never a shorter image.
        """


class DashboardPort(Protocol):
    """``getDashboardSummary``. `R-44`.

    A separate protocol rather than a method on any existing port, for the same reason
    ``BlockPort`` is: no shipped or test-only wiring of another port is made incomplete
    by an operation it never answered. ``build_router`` takes it as
    ``dashboard: DashboardPort | None = None``, the same optional-with-a-default shape
    ``blocks`` already has.

    **One method and no parameter.** This is deliberate and is the whole of what this
    port refuses to become: not a project-scoped read, not a date range, not a category
    filter. See ``docs/program/W46-SEAL.md`` section 3.
    """

    def get_summary(self) -> DashboardSummaryView:
        """The whole deployment's operational shape, right now: all four panels.

        **Absent is not empty.** Every member of ``Verdict`` and ``RunState`` appears in
        its panel even at a count of zero, every one of the fifteen current project
        sections appears in ``section_breakdown`` even with no documents, and the
        documents nobody has classified yet are their own row rather than a rounding
        error folded into one of the fifteen.
        """


@runtime_checkable
class SectionPort(Protocol):
    """``classifyDocumentVersion`` and ``getVersionSectionReview``. `W59-SECTION-SEAL-01`.

    A separate protocol, optional in ``build_router``, for the reason ``BlockPort`` gives.
    Both operations address a version through its document and project: a version that does
    not belong to the named document, or a document outside the named project, is
    ``not_found`` exactly as an unknown identity is.
    """

    def classify_version(
        self,
        *,
        project_uid: str,
        document_uid: str,
        version_uid: str,
        project_stage: str,
        section_code: str,
        user_uid: str,
    ) -> models.VersionClassification:
        """Persist an expert's stage and section for one version, or answer the stored one.

        The actor's role set is read from the account in the same transaction: ``expert``
        is required and ``admin`` alone is refused (``permission_denied``). An exact repeat
        answers the stored row, first confirmer kept; a different stage or section is
        ``conflict`` with ``conflict_reason: version_already_classified`` and changes
        nothing.
        """

    def get_section_review(
        self, *, project_uid: str, document_uid: str, version_uid: str
    ) -> models.SectionReview:
        """All fifteen choices with display evidence and the current classification.

        Display only: no suggestion confirms a section or authorizes a run.
        """


@runtime_checkable
class RunPort(Protocol):
    """Run status and the W57a refusing normative report seam. Produced by ``B5``.

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

    def get_norm_verification(self, *, run_id: str) -> models.NormVerificationReport:
        """Verified v3 report only. Until CITE supplies its reader, typed refusal."""

    def get_run_norm_references(self, *, run_id: str) -> models.RunNormReferences:
        """The norms the run's saved text cites, each against the run's pinned snapshot.

        `NORM-REFS-RUN-01`. Computed per request, read-only, deterministic: no finding, no
        severity, no model. A run that pinned no snapshot, has no saved text layer or cites
        more than one answer carries is a ``state`` in the answer, never an empty list; an
        unknown run is ``not_found``; a stored fact that contradicts its own constraints is
        ``internal_error``.
        """

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
        severity: str | None,
        comment: str | None,
        idempotency_key: str,
        author_label: str,
        author_user_uid: str,
    ) -> AppendedDecision:
        """Append exactly one event, whatever a replay under one key does.

        The database enforces the "exactly one" rather than the handler promising it:
        ``expert_decision_event`` carries at most one event per ``command_id``.

        ``author_label`` is `D-78` as `R-37` amends it, and it is the one parameter here
        that does **not** come from the request. It is the **display label** of the
        reviewer the authorization seam verified -- their chosen name, or their login when
        they have chosen none -- read by the router through
        :data:`~auditmanager.api.security.CurrentSubject`. It is declared on the port
        rather than resolved behind it because the identity is a property of the *request*,
        which only the surface can see -- an adapter reaching for it would be a module
        below the seam asking who the caller is.

        It has no default, here or in the ledger. A decision with no named author is a
        refusal, and every operation that can reach this method is one the seam guards, so
        there is always a subject to name.

        ``author_user_uid`` is `W49-SEAL-01`'s: the verified subject's **identity**, which
        the ledger persists beside the label (`expert_decision_event.author_user_uid`) so
        "no decisions by this account" is a query and not a guess from a display string.
        It has no default either, here or in the ledger.

        ``severity`` is optional in the wire contract and must be passed explicitly.
        Until W56A-DECIDE-01 owns the ledger write, the adapter refuses a non-null
        value instead of silently dropping the expert's decision.
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
    policy. ``P02_SEAMS.md`` section 6 declares the nineteen columns, the byte
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
class XlsxExportPort(Protocol):
    """``exportRunXlsx`` (`W57B-NORMS-CATALOGUE-XLSX-01`).

    The router adds nothing to the bytes: the workbook's layout and every refusal belong to
    ``auditmanager.exports.export_run_xlsx``. The refusals are ``exportRunCsv``'s first --
    ``not_found`` and ``state_transition_not_allowed`` decided on the run row before
    anything else is read -- then ``storage_integrity_error`` (``role:
    source.structured_companion``) for a version without verifiable sheet labels and
    ``required_norm_unavailable`` (``reference_kind: norm_retrieval_set``) for citations
    that do not verify. Nothing is created, so a repeat returns byte-identical bytes.
    """

    def export_run_xlsx(self, *, run_id: str, principal_id: str) -> bytes:
        """The workbook bytes for one run, for the principal the seam admitted."""


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

    :meth:`standing_of` is here rather than on a seventh port because it is the same adapter's
    job: the one object in the tree that holds both the user repository and the signer is
    the only one that can answer it, and a second port over the same two halves would be a
    second thing for the composition root to forget to wire. It is also what
    :class:`auditmanager.api.security.AccountStandings` asks for, structurally -- the seam
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

    def standing_of(self, user_uid: str) -> AccountStanding | None:
        """What the seam re-reads about this account, or ``None`` for no account.

        Read together, in one statement: the generation of credentials this account
        accepts, whether it must change its password (`R-50`), and -- since `W49-SEAL-01`
        -- whether it is archived, whether its profile is complete, its role set, and the
        login and display label its row holds now. Read by the authorization seam on every
        request it guards; see :class:`auditmanager.api.security.AccountStandings` for why
        ``None`` refuses rather than admits, why the facts travel together, and why nothing
        caches the answer.
        """


@runtime_checkable
class AccountPort(Protocol):
    """``getMe``, ``updateMyProfile`` and the account management of `W49-SEAL-01`.

    Every rule is behind this port, in ``auditmanager.access``: that an account cannot
    archive, purge, demote or reset itself, that the last active administrator stays one,
    that a complete profile's login is fixed, that a purge refuses a referenced account.
    A router calls one method and renders what comes back; a refusal arrives as a
    ``DomainError`` the access boundary raised, with the code and the detail it chose.

    **Whose account is being changed is always an identity, never a login.** ``user_uid``
    comes from the path (an administrator's operation) or from the verified subject (the
    account's own), and ``actor_uid`` -- the administrator acting -- always from the
    verified subject, never from a body.
    """

    def get_account(self, *, user_uid: str) -> AccountView:
        """One account with its roles, archived or not; ``not_found`` for no such account."""

    def list_accounts(self, *, include_archived: bool) -> Sequence[AccountView]:
        """Every active account -- or every account -- ordered by ``(login, user_uid)``.

        The order is part of this declaration for the reason ``ProjectPort.list_projects``
        gives: the router pages what this returns and never re-sorts it.
        """

    def update_my_profile(
        self,
        *,
        user_uid: str,
        last_name: str,
        first_name: str,
        middle_name: str | None,
        email: str | None,
    ) -> AccountView:
        """The account's own names, and -- while its profile is incomplete -- its e-mail.

        Completion is one UPDATE of names, login and timestamp (`R-59`); a complete
        profile's login is fixed.
        """

    def update_account(
        self,
        *,
        actor_uid: str,
        user_uid: str,
        names: PersonNamesView | None,
        roles: frozenset[str] | None,
    ) -> AccountView:
        """An administrator's change of names, role set, or both, in one transaction.

        ``None`` leaves that half unchanged. A role change raises the account's
        ``token_epoch``; a name change does not.
        """

    def archive_account(self, *, actor_uid: str, user_uid: str) -> AccountView:
        """Archive the account (`R-61`); every credential it holds stops being accepted."""

    def restore_account(self, *, actor_uid: str, user_uid: str) -> AccountView:
        """Return an archived account to active."""

    def purge_account(self, *, actor_uid: str, user_uid: str) -> None:
        """Delete an archived, unreferenced account irreversibly (`R-61`)."""

    def reset_password(
        self, *, actor_uid: str, user_uid: str, temporary_password: str
    ) -> AccountView:
        """Set a temporary password the account must change at its next sign-in."""


@runtime_checkable
class RegistrationPort(Protocol):
    """The five registration operations of `W49-SEAL-01` (`R-56`).

    Two of them are reached without a credential (``submitRegistration`` and
    ``readRegistrationStatus``), so their methods take nothing a caller could use to name an
    account other than the pair it typed. The other three are an administrator's, and the
    administrator is ``actor_uid``, from the verified subject.
    """

    def submit(
        self,
        *,
        login: str,
        password: str,
        last_name: str,
        first_name: str,
        middle_name: str | None,
    ) -> str:
        """Record a request and answer its status, which is ``pending`` by construction."""

    def read_status(self, *, login: str, password: str) -> str | None:
        """``pending`` for a pair that proves a pending request, else ``None``.

        ``None`` is the same single answer a refused exchange gets -- no such login, a wrong
        password, a decided request whose password was nulled at the decision -- and the
        router turns it into the generic ``authentication_required``. The implementation
        spends the same work on every path, so the timing says nothing either.
        """

    def list_requests(self, *, status: str | None) -> RegistrationListingView:
        """Every request (or those in one status), oldest first, and the pending total."""

    def approve(
        self,
        *,
        actor_uid: str,
        request_id: str,
        roles: frozenset[str],
        idempotency_key: str,
    ) -> RegistrationView:
        """Create the account and decide the request, in one transaction, or replay it.

        The same key with the same payload replays the recorded outcome; with another
        payload it is ``idempotency_key_reuse`` and changes nothing.
        """

    def reject(self, *, actor_uid: str, request_id: str, reason: str) -> RegistrationView:
        """Decide the request as rejected with a reason of 1-256 characters."""


@runtime_checkable
class ReleasesPort(Protocol):
    """Release reads and the signed-in account's own high-water mark.

    Stage B freezes these methods. Stage C supplies storage and version computation.
    """

    def get_product_version(self) -> ProductVersion: ...

    def list_releases(self, *, user_uid: str) -> ReleaseList: ...

    def mark_read(self, *, user_uid: str, read_through: str) -> None: ...


@runtime_checkable
class NormsSearchPort(Protocol):
    """The norms reads and the current-snapshot designation. `W55A-SEAL-01` (R-112, R-113).

    ``searchNorms``, ``getNormDocument``, ``listNormParagraphs``, ``listNormSnapshots``,
    ``listNormSnapshotEvents`` and ``setCurrentNormSnapshot`` (plan section A3.6). Sealed as
    stubs that answer ``503 dependency_unavailable`` (``dependency: norms_search``);
    `W55A-SEARCH-01` supplies the behaviour. A separate protocol, optional in
    ``build_router``, for the reason ``BlockPort`` gives.

    Refusals the implementation owns, all under existing codes (CD-19): no current snapshot,
    or an explicit snapshot that has never been current, is ``required_norm_unavailable``
    (``reference_kind: norms_snapshot``); a designation target that does not qualify is the
    same code with ``reference_kind`` ``norm_embedding_build`` or ``norm_source``; a stale
    ``expected_current`` is ``conflict`` (``conflict_reason: stale_current_snapshot``); a
    search the statement timeout cancels is ``validation_failed``
    (``constraint: norms_search_too_broad``), never an empty or partial page.
    """

    def search(
        self, *, q: str, norms_snapshot_id: str | None, cursor: str | None, limit: int
    ) -> models.NormSearchPage:
        """Reliable paragraphs of the scoped snapshot matching ``q`` (1-200 characters)."""

    def get_document(self, *, norm_document_id: str) -> models.NormDocument:
        """One norm document; ``not_found`` for an identity that names nothing."""

    def list_catalogue(
        self, *, q: str | None, kind: str | None, cursor: str | None, limit: int
    ) -> models.NormCatalogueEntryPage:
        """``listNormDocuments`` (`W57B-NORMS-CATALOGUE-XLSX-01`): the current snapshot's
        documents with display names, filtered by text and kind, in designation order; no
        current snapshot is ``required_norm_unavailable`` (``reference_kind:
        norms_snapshot``); a ``q`` or ``kind`` with nothing to filter by, or a foreign
        cursor, is ``validation_failed``."""

    def list_paragraphs(
        self, *, norm_document_id: str, cursor: str | None, limit: int
    ) -> models.NormParagraphPage:
        """One document's paragraphs by ``ordinal``, unreliable ones marked, never hidden."""

    def list_snapshots(self, *, cursor: str | None, limit: int) -> models.NormSnapshotPage:
        """Every loaded snapshot with its counts, build state, ``qualified`` and ``current``."""

    def list_snapshot_events(
        self, *, cursor: str | None, limit: int
    ) -> models.NormSnapshotEventPage:
        """The append-only history of the current snapshot, newest first."""

    def set_current_snapshot(
        self, *, norms_snapshot_id: str, expected_current: str | None, user_uid: str
    ) -> models.NormCurrentSnapshot:
        """Designate a qualifying snapshot as current, writing one history row.

        An already-current target is a replay: the current designation is answered and no
        history row is written. There is no unset.
        """


@runtime_checkable
class NormContentPort(Protocol):
    """``streamNormDocumentContent``. `W55A-SEAL-01` (plan section A3.5).

    Sealed as a stub answering ``503 dependency_unavailable`` (``dependency:
    norm_content``). The PDF is served only through a **confirmed** custody binding of the
    document (W54 custody); a document without one is ``required_norm_unavailable``
    (``reference_kind: norm_source``). The same streaming and range rules as
    :meth:`DocumentPort.stream_content`.
    """

    def stream_content(
        self, *, norm_document_id: str, byte_range: ByteRange | None
    ) -> StreamedContent:
        """The document's source PDF, whole or one window, opened before returning."""


@runtime_checkable
class ComparisonPort(Protocol):
    """``compareDocumentVersions`` and ``carryOverDecision``. `W59-VERSION-COMPARE-01`,
    `W59-DECISION-CARRYOVER-01`.

    A separate protocol, optional in ``build_router``, for the reason ``BlockPort`` gives.
    The comparison is always a ``VersionComparison``: a pair the comparison rule does not
    admit is ``outcome: refused`` with one closed reason, never an error envelope and never
    a relabelled pair, and the read writes nothing. The one write is the expert-confirmed
    carryover of one source decision to the matched target finding, appended to the
    decision ledger after the comparison is recomputed.
    """

    def compare_versions(
        self,
        *,
        project_uid: str,
        document_uid: str,
        source_version_uid: str,
        target_version_uid: str,
        source_run_id: str | None,
        target_run_id: str | None,
        mode: str,
        diff_offset: int,
        diff_limit: int,
    ) -> models.VersionComparison:
        """The comparison of the two named versions, or why they are not compared."""

    def carry_over_decision(
        self,
        *,
        project_uid: str,
        document_uid: str,
        source_version_uid: str,
        target_version_uid: str,
        mode: str,
        source_finding_uid: str,
        target_finding_uid: str,
        source_decision_id: str,
        source_run_id: str | None,
        target_run_id: str | None,
        idempotency_key: str,
        author_label: str,
        author_user_uid: str,
    ) -> models.CarryOverDecisionResponse:
        """Carry the confirmed source decision to the target finding, or refuse.

        The expert role is read from the account in the confirming transaction; ``admin``
        alone is ``permission_denied``. A pair the recomputed comparison no longer proposes,
        a source decision that is no longer current, a target that already has an event and
        a severity the target cannot hold are each ``conflict`` with a ``conflict_reason``.
        """

@runtime_checkable
class AnalysisProfilePort(Protocol):
    """``listAnalysisProfiles``. `W59-ANALYSIS-SETTINGS-01`.

    A separate protocol, optional in ``build_router``, for the reason ``BlockPort`` gives.
    The answer is the composition root's sealed text-profile registry, the one run start
    routes through: all fifteen sections in the project-structure order, each with its
    registered profile or ``null``. Nothing behind this port writes, and nothing edits a
    profile or its status.
    """

    def list_analysis_profiles(self) -> models.AnalysisProfileList:
        """Every section and its registered text profile, or ``null`` when none is."""


@runtime_checkable
class SpecificationPricesPort(Protocol):
    """``getSpecificationPrices``. `W60-OPT-MATCH-01`.

    A separate protocol, optional in ``build_router``, for the reason ``BlockPort`` gives.
    The answer is always a ``SpecificationPrices``: a precondition that does not hold (an
    unclassified or non-AR version, no price list, no published run, no saved text, too many
    rows) is its explicit ``state``, never an error envelope and never an empty table. An
    unknown project or a set outside it is ``404``. Nothing behind this port writes.
    """

    def get_specification_prices(
        self, *, project_uid: str, document_uid: str, offset: int, limit: int, user_uid: str
    ) -> models.SpecificationPrices:
        """The priced specification of the set's current AR version, or its state."""


@runtime_checkable
class SectionSpecificationPort(Protocol):
    """``getSectionSpecification``. `W63-SECTION-FORM7-01`.

    A separate protocol, optional in ``build_router``, for the reason ``BlockPort`` gives. The
    answer is always a ``SectionSpecification``: a bound that stops it (``section_too_large``)
    and a set without a run or a saved text are states in the answer, never an error envelope
    and never an empty table. An unknown ``project_uid`` filter is ``404``. Nothing behind
    this port writes.
    """

    def get_section_specification(
        self,
        *,
        section_code: str,
        project_uid: str | None,
        query: str | None,
        offset: int,
        limit: int,
        user_uid: str,
    ) -> models.SectionSpecification:
        """The section's combined specification of current versions, priced per project."""


class DispatchPort(Protocol):
    """The four «Диспетчер» operations. `W61-DISPATCHER-01`.

    A separate protocol, optional in ``build_router``, for the reason ``BlockPort`` gives.
    Every method reads the acting account's role set in its own transaction; the seam's role
    register is only the outer door (``admin`` for creation, any one role otherwise).
    """

    def create_assignment(
        self,
        *,
        project_uid: str,
        document_uid: str | None,
        assignee_user_uid: str,
        note: str | None,
        user_uid: str,
    ) -> models.Assignment:
        """Create one assignment, or answer the open one this request repeats exactly.

        ``admin`` only; the assignee must be an active ``expert`` (``validation_failed``,
        ``constraint: active_expert_required``); the document must belong to the project
        (``not_found``); another open assignment on the same scope is ``conflict`` with
        ``conflict_reason: assignment_open``.
        """

    def list_assignments(
        self, *, user_uid: str, mine: bool, status: str | None, project_uid: str | None
    ) -> Sequence[models.Assignment]:
        """Every assignment the caller may read, newest first, narrowed by the filters.

        An administrator reads all (``mine`` narrows to their own); an expert always reads
        only the assignments currently given to them.
        """

    def get_assignment(self, *, assignment_uid: str, user_uid: str) -> models.AssignmentDetail:
        """One assignment and its history; ``not_found`` when absent or not visible."""

    def transition_assignment(
        self,
        *,
        assignment_uid: str,
        kind: str,
        reason: str | None,
        new_assignee_user_uid: str | None,
        user_uid: str,
    ) -> models.Assignment:
        """Append one event, answer an exact repeat unchanged, or refuse.

        ``started``/``completed``/``returned`` by the current assignee holding ``expert``
        (``permission_denied``, ``required_capability: assignment:assignee`` otherwise);
        ``reassigned``/``cancelled`` by ``admin``; a move the table does not allow is
        ``state_transition_not_allowed`` (``machine: work_assignment``).
        """


@runtime_checkable
class OptimisationPort(Protocol):
    """The six «Оптимизация проекта» operations. `W60-PRICE-LIST-01`.

    A separate protocol, optional in ``build_router``, for the reason ``BlockPort`` gives.
    Behind it: ``auditmanager.optimisation``. Every write reads the actor's role set in its
    own transaction (``expert`` uploads a price list and overrides a project's vendor list;
    ``admin`` keeps the global vendor list); every read needs any one role. No method here
    computes a total, a proposal or a price that a price list does not state.
    """

    def upload_price_list(
        self,
        *,
        project_uid: str,
        content: BinaryIO,
        source_filename: str,
        default_currency: str | None,
        idempotency_key: str,
        user_uid: str,
    ) -> models.PriceListRevision:
        """Store one price list as the project's newest revision, or answer the exact repeat."""

    def list_price_list_revisions(
        self, *, project_uid: str, user_uid: str
    ) -> models.PriceListRevisionList:
        """Every revision of the project's price list, newest first."""

    def list_price_list_positions(
        self, *, price_list_id: str, offset: int, limit: int, user_uid: str
    ) -> models.PriceListPositionPage:
        """One page of a revision's positions with the revision and its parse report."""

    def get_effective_vendor_lists(
        self, *, project_uid: str, user_uid: str
    ) -> models.EffectiveVendorLists:
        """All fifteen sections' vendor lists as they apply to the project."""

    def set_global_vendor_list(
        self,
        *,
        section_code: str,
        entries: Sequence[models.VendorListEntry],
        expected_vendor_list_id: str | None,
        expect_current: bool,
        user_uid: str,
    ) -> models.VendorListRevision:
        """Append a global revision, or answer the latest unchanged on an exact repeat."""

    def set_project_vendor_list(
        self,
        *,
        project_uid: str,
        section_code: str,
        mode: str,
        entries: Sequence[models.VendorListEntry],
        expected_vendor_list_id: str | None,
        expect_current: bool,
        user_uid: str,
    ) -> models.SectionVendorList:
        """Append a project revision (or none on a repeat) and answer the section's state."""


@runtime_checkable
class OptimisationProposalPort(Protocol):
    """The six «Предложения» operations. `W60-OPT-PROPOSALS-01`.

    A separate protocol, optional in ``build_router``, for the reason ``BlockPort`` gives.
    Behind it: ``auditmanager.optimisation.proposals``. Every method reads the actor's role
    set in its own transaction (``expert`` starts a pass and decides a proposal -- an account
    holding only ``admin`` does neither; any one role reads and exports). Nothing here is a
    finding, reads a finding or changes one; no money figure exists that a price-list
    position does not state.
    """

    def start_optimisation_pass(
        self,
        *,
        project_uid: str,
        document_uid: str,
        idempotency_key: str,
        user_uid: str,
    ) -> models.OptimisationPass:
        """Start the pass for the document set's current AR version, answer the stored pass
        with exactly these inputs, or refuse with the first unmet precondition."""

    def list_optimisation_passes(
        self, *, project_uid: str, document_uid: str | None, limit: int, user_uid: str
    ) -> models.OptimisationPassList:
        """The project's passes, newest first, each with its counts by decision."""

    def list_optimisation_proposals(
        self,
        *,
        optimisation_pass_id: str,
        decision: str | None,
        offset: int,
        limit: int,
        user_uid: str,
    ) -> models.OptimisationProposalPage:
        """One page of a pass's proposals with each one's current decision."""

    def decide_optimisation_proposal(
        self,
        *,
        optimisation_proposal_id: str,
        verdict: str,
        comment: str | None,
        idempotency_key: str,
        user_uid: str,
    ) -> models.ProposalDecisionResult:
        """Append one decision, or answer the one stored under the key."""

    def list_proposal_decisions(
        self, *, optimisation_proposal_id: str, user_uid: str
    ) -> models.ProposalDecisionList:
        """Every decision of one proposal, oldest first."""

    def export_optimisation_proposals_csv(
        self, *, optimisation_pass_id: str, user_uid: str
    ) -> bytes:
        """The pass's proposals as the formula-escaped CSV bytes."""
