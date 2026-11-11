"""Opaque, prefixed identifier value types.

Source of truth: ``contracts/domain/v1/identifiers.json``. Every entity
declared there gets exactly one type here, carrying exactly
the contract prefix. ``tests/contract/domain_p02/test_identifier_catalog.py``
asserts the two sets are equal in both directions, so a catalog entry that gains a
type here without a contract entry, or the reverse, is a test failure rather than a
review question.

Three properties are enforced by construction rather than by convention:

* **Opacity.** The type exposes the identifier as a string and nothing else. There
  is no ``timestamp`` property, no ``created_at`` derivation and no ordering
  operator, because the contract forbids decoding the ULID body for business
  meaning. ``ulid.py`` ships no decoder either, so there is nothing to call.
* **Type separation.** ``ProjectUid.parse("doc_...")`` raises. A well-formed
  identifier of the wrong entity is rejected at construction, so a mis-wired
  foreign key is a ``ValueError`` at the boundary rather than a row that points at
  the wrong table.
* **Non-identity exclusion.** No type is defined for a filesystem path, an object
  key, an uploaded file name, a display ordinal, a checksum or an idempotency key.
  The contract lists those as non-identities; they are ordinary attributes and are
  never modelled as one of these types.

Identifiers carry no secret. They are safe to log, to place in error-envelope
details and to return to an authorized caller.
"""

from __future__ import annotations

import re
from typing import ClassVar, Final, Self

from auditmanager.shared.identity.errors import (
    IdentifierFormatError,
    IdentifierPrefixError,
)
from auditmanager.shared.identity.ulid import ULID_LENGTH, is_valid_ulid, new_ulid

#: ``format`` and ``id_pattern`` from the contract, restated so the code can be read
#: without the catalog open. The contract test pins both against the catalog.
IDENTIFIER_FORMAT: Final[str] = "<prefix>_<ULID>"
IDENTIFIER_PATTERN: Final[str] = r"^[a-z][a-z0-9]{1,7}_[0-9A-HJKMNP-TV-Z]{26}$"
PREFIX_PATTERN: Final[str] = r"^[a-z][a-z0-9]{1,7}$"

_PREFIX_RE: Final[re.Pattern[str]] = re.compile(PREFIX_PATTERN)

_REGISTRY: Final[dict[str, type["OpaqueId"]]] = {}


def pattern_for(prefix: str) -> str:
    """The contract's ``pattern_template`` instantiated for one prefix.

    This is the single source of the regular expression used by the value types
    *and* by the CHECK constraints in the migration, so the database and the
    application cannot drift apart on what a well-formed identifier is.
    """
    if not _PREFIX_RE.fullmatch(prefix):
        raise ValueError(f"prefix {prefix!r} does not match {PREFIX_PATTERN}")
    return rf"^{prefix}_[0-9A-HJKMNP-TV-Z]{{{ULID_LENGTH}}}$"


class OpaqueId:
    """Base class for every entity identity in the domain catalog.

    Instances are immutable and compare by exact string equality. Two instances of
    *different* subclasses never compare equal, even if their prefixes were somehow
    made to coincide: identity is (type, value), never value alone.
    """

    __slots__ = ("_value",)

    #: Contract prefix. Set on every concrete subclass; empty on the base.
    prefix: ClassVar[str] = ""
    #: The entity name this identity belongs to, as spelled in the contract.
    entity: ClassVar[str] = ""

    def __init_subclass__(cls, /, prefix: str = "", entity: str = "", **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not prefix:
            raise TypeError(f"{cls.__name__} must declare a contract prefix")
        if not entity:
            raise TypeError(f"{cls.__name__} must declare its contract entity name")
        existing = _REGISTRY.get(prefix)
        if existing is not None:
            raise TypeError(
                f"prefix {prefix!r} is already bound to {existing.__name__}; "
                "the contract requires prefixes to be globally unique"
            )
        cls.prefix = prefix
        cls.entity = entity
        cls._pattern = re.compile(pattern_for(prefix))  # type: ignore[attr-defined]
        _REGISTRY[prefix] = cls

    def __init__(self, value: str) -> None:
        cls = type(self)
        if not cls.prefix:
            raise TypeError("OpaqueId is abstract; construct a concrete identity type")
        if not isinstance(value, str):
            raise IdentifierFormatError(
                f"{cls.entity} identity must be a string, got {type(value).__name__}"
            )
        # `fullmatch`, not `match`: the pattern's `$` also accepts one trailing newline.
        if not cls._pattern.fullmatch(value):  # type: ignore[attr-defined]
            head, separator, body = value.partition("_")
            if separator and head != cls.prefix and _PREFIX_RE.fullmatch(head) and is_valid_ulid(body):
                raise IdentifierPrefixError(
                    f"expected a {cls.entity} identity with prefix {cls.prefix!r}, "
                    f"got prefix {head!r}"
                )
            raise IdentifierFormatError(
                f"{value!r} does not match the contract pattern for {cls.entity} "
                f"({pattern_for(cls.prefix)})"
            )
        object.__setattr__(self, "_value", value)

    # -- construction ---------------------------------------------------------
    @classmethod
    def new(cls) -> Self:
        """Allocate a fresh identity. Generated once; never reused, never re-issued."""
        return cls(f"{cls.prefix}_{new_ulid()}")

    @classmethod
    def parse(cls, value: str) -> Self:
        """Validate an externally supplied string as this entity's identity."""
        return cls(value)

    @classmethod
    def parse_optional(cls, value: str | None) -> Self | None:
        """``None`` passes through; anything else is validated."""
        return None if value is None else cls(value)

    # -- value semantics ------------------------------------------------------
    @property
    def value(self) -> str:
        """The identifier as stored, transported and logged."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._value == other._value  # type: ignore[attr-defined]

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._value))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")


# ---------------------------------------------------------------------------
# The 29 declared entity identities, in catalog order.
# ---------------------------------------------------------------------------


class ObjectUid(OpaqueId, prefix="obj", entity="Object"):
    """Identity of a construction object."""


class DisciplineUid(OpaqueId, prefix="dsc", entity="Discipline"):
    """Identity of a design discipline."""


class ProjectUid(OpaqueId, prefix="prj", entity="Project"):
    """Identity of a project."""


class DocumentUid(OpaqueId, prefix="doc", entity="Document"):
    """Identity of a document, independent of any one of its versions."""


class VersionUid(OpaqueId, prefix="ver", entity="DocumentVersion"):
    """Identity of one immutable published input state."""


class ImportId(OpaqueId, prefix="imp", entity="Import"):
    """Identity of an ingest operation. Not allocated anywhere in PC-01."""


class BlobId(OpaqueId, prefix="blob", entity="Blob"):
    """Identity of durable content bytes. The object key is never the identity."""


class RunId(OpaqueId, prefix="run", entity="AuditRun"):
    """Identity of one audit execution request and its result history."""


class JobId(OpaqueId, prefix="job", entity="Job"):
    """Identity of the durable schedulable work item for one local run."""


class AttemptId(OpaqueId, prefix="att", entity="Attempt"):
    """Identity of one fenced execution of a Job."""


class LeaseId(OpaqueId, prefix="lse", entity="Lease"):
    """Identity of the execution lease held by the current Attempt."""


class CommandId(OpaqueId, prefix="cmd", entity="CommandRecord"):
    """Identity of the durable record that makes a command safe to repeat."""


class FindingUid(OpaqueId, prefix="fnd", entity="Finding"):
    """Durable semantic issue identity that carries expert history across reruns."""


class FindingObservationId(OpaqueId, prefix="fobs", entity="FindingObservation"):
    """Immutable evidence emitted by exactly one run."""


class DecisionId(OpaqueId, prefix="dec", entity="ExpertDecision"):
    """Identity of one appended expert decision event. Never reused or updated."""


class AnalysisProfileId(OpaqueId, prefix="ap", entity="AnalysisProfile"):
    """Identity of an immutable analysis profile."""


class PromptBundleId(OpaqueId, prefix="pb", entity="PromptBundle"):
    """Identity of an immutable prompt bundle."""


class NormsSnapshotId(OpaqueId, prefix="ns", entity="NormsSnapshot"):
    """Identity of an immutable norms snapshot."""


class NormDocumentId(OpaqueId, prefix="ndoc", entity="NormDocument"):
    """Identity of one immutable normative document inside a snapshot."""


class NormParagraphId(OpaqueId, prefix="npar", entity="NormParagraph"):
    """Identity of one immutable canonical normative paragraph."""


class NormRetrievalSetId(OpaqueId, prefix="nrs", entity="NormRetrievalSet"):
    """Identity of one snapshot-bound normative retrieval set and catalogue."""


class PriceListId(OpaqueId, prefix="prl", entity="PriceList"):
    """Identity of one uploaded price-list revision of a project (`W60-PRICE-LIST-01`).

    Minted by ``auditmanager.optimisation`` since migration ``0026_price_lists``. Never
    derived from the project, the revision number, the file name or its checksum.
    """


class PriceListPositionId(OpaqueId, prefix="prp", entity="PriceListPosition"):
    """Identity of one parsed position of one price-list revision; never its row number."""


class VendorListId(OpaqueId, prefix="vnl", entity="VendorList"):
    """Identity of one immutable vendor-list revision of a section, global or of a project."""


class OptimisationPassId(OpaqueId, prefix="opp", entity="OptimisationPass"):
    """Identity of one optimisation pass over a document set's AR version (`W60-OPT-PROPOSALS-01`).

    Minted by ``auditmanager.optimisation.proposals`` since migration
    ``0027_optimisation_proposals``. Never derived from the version, the run or the time it
    started.
    """


class OptimisationProposalId(OpaqueId, prefix="opr", entity="OptimisationProposal"):
    """Identity of one proposal of one pass; never its ordinal or its specification row."""


class ProposalDecisionId(OpaqueId, prefix="opd", entity="ProposalDecision"):
    """Identity of one appended expert decision on a proposal; never its ``seq``."""


class NormCustodyAdmissionId(OpaqueId, prefix="nad", entity="NormCustodyAdmission"):
    """Identity of one custody intent and its outbox row (`R-76`, migration ``0018``).

    `W54-SEAL-01` declares it; `W54-CUSTODY-01` allocates it. Never derived from the blob,
    the declared SHA-256, the anchor or the target.
    """


class NormCustodyBindingId(OpaqueId, prefix="nbd", entity="NormCustodyBinding"):
    """Identity of one published custody binding of a confirmed admission (`R-76`)."""


class NormRepairCallId(OpaqueId, prefix="nrc", entity="NormRepairCall"):
    """Identity of one paid repair-call try (`R-106`); also its own idempotency scope."""


class ModelCallId(OpaqueId, prefix="mc", entity="ModelCallRecord"):
    """Identity of one provider call record."""


class ComparisonId(OpaqueId, prefix="cmp", entity="Comparison"):
    """Identity of a comparison. Not allocated in PC-01."""


class SheetLinkId(OpaqueId, prefix="sln", entity="SheetLink"):
    """Identity of a sheet link. Not allocated in PC-01."""


class ExportId(OpaqueId, prefix="exp", entity="ExportRequest"):
    """Identity of an export request. Not allocated in PC-01: the CSV is computed."""


class WorkerId(OpaqueId, prefix="wrk", entity="Worker"):
    """Identity of one registered worker process (migration ``0019``).

    `W54-SEAL-01` instantiates the ``worker`` registry; `W54-WORKER-01` allocates the
    identity when a worker process starts.
    """


class AuditEventId(OpaqueId, prefix="evt", entity="AuditEvent"):
    """Identity of one appended audit event."""


class ErasureRequestId(OpaqueId, prefix="era", entity="ErasureRequest"):
    """Identity of an erasure request. Not allocated in PC-01."""


class UserUid(OpaqueId, prefix="usr", entity="User"):
    """Identity of one account (``app_user``). `W49-SEAL-01` moved ``usr`` here.

    Minted in this shape by ``auditmanager.access`` since migration ``0006``, outside this
    registry until the account crossed the wire; the access boundary now delegates to this
    type, so the prefix and its pattern have one owner.
    """


class RegistrationRequestId(OpaqueId, prefix="reg", entity="RegistrationRequest"):
    """Identity of one registration request (``request_id``). `W49-SEAL-01` moved ``reg`` here.

    Minted by ``auditmanager.access.registrations`` since migration ``0015``.
    """


class AssignmentUid(OpaqueId, prefix="asg", entity="WorkAssignment"):
    """Identity of one work assignment of the dispatcher (`W61-DISPATCHER-01`).

    Minted by ``auditmanager.dispatch``; never derived from the project, the document, the
    assignee or a position in a list. Its history events are ``AuditEventId`` (``evt_``).
    """


class ExecutorConnectionId(OpaqueId, prefix="exc", entity="ExecutorConnection"):
    """Identity of one executor connection (`EXEC-SEAL-01`, migration ``0030``).

    Minted by ``auditmanager.executors``; never derived from the address, the display name or
    the model, all of which can change in a new revision while the connection stays.
    """


class ExecutorConnectionRevisionId(
    OpaqueId, prefix="excr", entity="ExecutorConnectionRevision"
):
    """Identity of one immutable revision of a connection's non-secret settings."""


class ExecutorSecretId(OpaqueId, prefix="exs", entity="ExecutorSecret"):
    """Identity of one sealed secret. It is part of the associated data of its ciphertext."""


class ExecutorProbeId(OpaqueId, prefix="epb", entity="ExecutorProbe"):
    """Identity of one probe of a connection revision."""


class ExecutorRouteEventId(OpaqueId, prefix="ert", entity="ExecutorRouteEvent"):
    """Identity of one appended change of the route for a kind of model work."""


class ExecutorRunnerTokenId(OpaqueId, prefix="ern", entity="ExecutorRunnerToken"):
    """Identity of one runner token of a ``pull`` connection (`EXEC-PULL-01`, migration ``0031``).

    The token's secret value is never an identity: only the hash of it is stored, and this
    identity addresses the row for the administrator who revokes it.
    """


class ExecutorTaskId(OpaqueId, prefix="ext", entity="ExecutorTask"):
    """Identity of one task a ``pull`` connection hands to a runner (`EXEC-PULL-01`)."""


class ExecutorEnrollmentId(OpaqueId, prefix="exen", entity="ExecutorEnrollment"):
    """Identity of one enrollment grant of the universal agent (`EXEC2-SEAL-1`, migration ``0046``).

    Minted by ``auditmanager.executors``. The grant's secret, its shown prefix and its hash are
    attributes and never identities: the value is shown once and only its one-way hash is stored.
    """


class ExecutorAgentInstallId(OpaqueId, prefix="exai", entity="ExecutorAgentInstall"):
    """Identity of one install session of the universal agent over SSH (`EXEC2-SEAL-1`, migration ``0046``).

    Minted by ``auditmanager.executors``; never derived from the host, the user or the host-key
    fingerprint, all of which are attributes of the session.
    """


class ExecutorGroupId(OpaqueId, prefix="exg", entity="ExecutorGroup"):
    """Identity of one executor group (`EXEC2-SEAL-2`, migration ``0047``, ADR-0026 decision 10).

    Minted by ``auditmanager.executors``. The display name is an attribute and never an identity.
    """


class ExecutorGroupRevisionId(OpaqueId, prefix="exgr", entity="ExecutorGroupRevision"):
    """Identity of one immutable revision of an executor group (`EXEC2-SEAL-2`, migration ``0047``).

    Minted by ``auditmanager.executors``. A Run or a comparison job admitted by a rule or a group freezes this
    identity, and never the group's current revision at the time of dispatch.
    """


class ExecutorRoutingRuleRevisionId(OpaqueId, prefix="exrr", entity="ExecutorRoutingRuleRevision"):
    """Identity of one revision of the routing rule of a work kind (`EXEC2-SEAL-2`, migration ``0047``).

    Minted by ``auditmanager.executors``. The work kind and the rule number are attributes of the row.
    """


class ExecutorRoutingModeEventId(OpaqueId, prefix="exrm", entity="ExecutorRoutingModeEvent"):
    """Identity of one change of the routing mode (`EXEC2-SEAL-2`, migration ``0047``, ADR-0026 decision 17).

    Minted by ``auditmanager.executors``; the mode in force is the latest event, never a flag.
    """


class ExecutorHostId(OpaqueId, prefix="exh", entity="ExecutorHost"):
    """Identity of one executor host -- a server with its one agent process and one host token (`HOSTS-SEAL-1`, migration ``0062``, ADR-0028).

    Minted by ``auditmanager.executors``. The host name, its address and the providers found on it are attributes and never an identity;
    a call journal row names the host by this identity without a foreign key, and a host is archived, never deleted.
    """


class ExecutorHostUseEventId(OpaqueId, prefix="exhu", entity="ExecutorHostUseEvent"):
    """Identity of one change of a host's «Использовать» switch (`HOSTS-SEAL-1`, migration ``0062``).

    Minted by ``auditmanager.executors``; the switch in force is the latest event of the host, never a flag.
    """


class ExecutorHostSlotEventId(OpaqueId, prefix="exhs", entity="ExecutorHostSlotEvent"):
    """Identity of one change of the slots of a provider on a host (`HOSTS-SEAL-1`, migration ``0062``).

    Minted by ``auditmanager.executors``; the slots in force are the latest event of the host and provider.
    """


class StageLayoutRevisionId(OpaqueId, prefix="slr", entity="StageLayoutRevision"):
    """Identity of one immutable revision of the stage layout -- the models of the analysis stages (`HOSTS-SEAL-1`, migration ``0062``).

    Minted by the stage-plan service. A run freezes the plan it was started with; this identity is what that plan records, never the
    layout's current revision at the time of reading.
    """


class StageLayoutSwitchEventId(OpaqueId, prefix="sls", entity="StageLayoutSwitchEvent"):
    """Identity of one change of the switch that puts the stage layout in force (`HOSTS-SEAL-1`, migration ``0062``).

    Minted by the stage-plan service; the switch in force is the latest event, and an empty journal means off.
    """


class ComparisonUploadId(OpaqueId, prefix="cbt", entity="ComparisonUpload"):
    """Identity of one upload batch of plain PDFs for comparison (`CMP-SEAL-C0`, migration ``0038``, ADR-0025 decision 10)."""


class ComparisonUploadSetId(OpaqueId, prefix="cus", entity="ComparisonUploadSet"):
    """Identity of one proposed document set of an upload batch -- the original's batch item (`CMP-SEAL-C0`, migration ``0038``). The «шифр» is metadata of a set, never its identity."""


class ComparisonUploadFileId(OpaqueId, prefix="cuf", entity="ComparisonUploadFile"):
    """Identity of one declared file of an upload batch (`CMP-SEAL-C0`, migration ``0038``). The display name is a hint and never an identity; the declared SHA-256 and size are verification values."""


class ComparisonVersionOrderId(OpaqueId, prefix="cvo", entity="ComparisonVersionOrder"):
    """Identity of one revision of the order in which the versions of a document set are compared (`CMP-SEAL-C0`, migration ``0038``, ADR-0025 decision 16)."""


class ComparisonPageProfileId(OpaqueId, prefix="cpr", entity="ComparisonPageProfile"):
    """Identity of the profile of one page of one version (`CMP-SEAL-C0`, migration ``0038``). Content-keyed: a ULID id and a unique digest; the digest is never a foreign key (ADR-0025 decision 2)."""


class ComparisonWorkId(OpaqueId, prefix="cq", entity="ComparisonWork"):
    """Identity of one item of the comparison-local durable queue (`CMP-SEAL-C0`, migration ``0038``, ADR-0025 decision 4)."""


class ComparisonWorkAttemptId(OpaqueId, prefix="cqa", entity="ComparisonWorkAttempt"):
    """Identity of one leased execution of a comparison work item (`CMP-SEAL-C0`, migration ``0038``). Not ``att_``: a Job is a Run in the schema, a comparison item is not."""


class ComparisonModelCallId(OpaqueId, prefix="cmc", entity="ComparisonModelCall"):
    """Identity of one row of the comparison spend journal (`CMP-SEAL-C0`, migration ``0038``, ADR-0025 decision 5). Not ``mc_``: that journal is a Run's."""


class ComparisonMatrixId(OpaqueId, prefix="cmx", entity="ComparisonMatrix"):
    """Identity of one algorithmic build of the effective matrix of a document set (`CMP-SEAL-C1`, migration ``0039``, ADR-0025 decisions 3 and 14). The effective matrix is a read model over a build, accepted AI links and manual edits."""


class ComparisonMatrixEditId(OpaqueId, prefix="cme", entity="ComparisonMatrixEdit"):
    """Identity of one event of the append-only manual edit history of a document set (`CMP-SEAL-C1`, migration ``0039``). A migrated ``0035`` approval carries its ``cmp_`` and ``sln_`` ids in the row's provenance, not as its identity."""


class ComparisonAiLinkId(OpaqueId, prefix="cak", entity="ComparisonAiLink"):
    """Identity of one accepted AI link (`CMP-SEAL-C1`, migration ``0039``, ADR-0025 decision 14). Labelled «ИИ», never an expert act; written in wave C2."""


class ComparisonSeriesId(OpaqueId, prefix="cser", entity="ComparisonSeries"):
    """Identity of one series of adjacent transitions of a document set for one version order (`CMP-SEAL-C1`, migration ``0039``, ADR-0025 decision 21)."""


class ComparisonTransitionId(OpaqueId, prefix="ctn", entity="ComparisonTransition"):
    """Identity of one adjacent transition of a series (`CMP-SEAL-C1`, migration ``0039``). Not a version number or an ordinal: the pair is two version identities."""


class ComparisonSheetPairId(OpaqueId, prefix="ctp", entity="ComparisonSheetPair"):
    """Identity of one sheet pair of a transition, the row that points at a content-keyed result (`CMP-SEAL-C1`, migration ``0039``). Two pairs of equal content share a result and keep their own identity."""


class ComparisonSheetPairResultId(OpaqueId, prefix="csp", entity="ComparisonSheetPairResult"):
    """Identity of the content-keyed result of comparing two pages (`CMP-SEAL-C1`, migration ``0039``, ADR-0025 decision 15): a ULID id and a unique digest column that includes the project; the digest is never a foreign key."""


class ComparisonAiJobId(OpaqueId, prefix="cai", entity="ComparisonAiJob"):
    """Identity of one consented AI job of the version comparison: a pair check, a sheet description, a specification comparison or a report (`CMP-SEAL-C2`, migration ``0040``, ADR-0025 decision 19). The estimate it consented to is frozen with it."""


class ComparisonAiPairAnswerId(OpaqueId, prefix="cpa", entity="ComparisonAiPairAnswer"):
    """Identity of the content-keyed answer of the model to one question of the pair check (`CMP-SEAL-C2`, migration ``0040``, ADR-0025 decision 15): a ULID id and a unique digest column that includes the project, so an answered question is never sent again."""


class ComparisonAiPairQuestionId(OpaqueId, prefix="cpq", entity="ComparisonAiPairQuestion"):
    """Identity of one question of an AI pair-check job and the decision made of its answers (`CMP-SEAL-C2`, migration ``0040``)."""


class ComparisonAiSheetItemId(OpaqueId, prefix="csi", entity="ComparisonAiSheetItem"):
    """Identity of one sheet pair of an AI description job (`CMP-SEAL-C2`, migration ``0040``), with its outcome."""


class ComparisonSheetDescriptionId(OpaqueId, prefix="csd", entity="ComparisonSheetDescription"):
    """Identity of the content-keyed AI description of one result or one single page (`CMP-SEAL-C2`, migration ``0040``): keyed by content, prompt version and model, with a unique digest that includes the project."""


class ComparisonSpecExtractionId(OpaqueId, prefix="cse", entity="ComparisonSpecExtraction"):
    """Identity of the content-keyed reading of the whole specification of one version (`CMP-SEAL-C2`, migration ``0040``)."""


class ComparisonSpecComparisonId(OpaqueId, prefix="cscp", entity="ComparisonSpecComparison"):
    """Identity of the comparison of the specifications of one transition (`CMP-SEAL-C2`, migration ``0040``)."""


class ComparisonReportId(OpaqueId, prefix="crt", entity="ComparisonReport"):
    """Identity of one PDF report of a series (`CMP-SEAL-C2`, migration ``0040``, ADR-0025 decision 2)."""


class ComparisonReportPartId(OpaqueId, prefix="crpt", entity="ComparisonReportPart"):
    """Identity of the progress of one transition of a report (`CMP-SEAL-C2`, migration ``0040``)."""


class ComparisonReportArtifactId(OpaqueId, prefix="cra", entity="ComparisonReportArtifact"):
    """Identity of one stored file of a report (`CMP-SEAL-C2`, migration ``0040``)."""


class ComparisonLaunchEntryId(OpaqueId, prefix="cle", entity="ComparisonLaunchEntry"):
    """Identity of one selected step of one document set in the launch queue of a project (`CMP-SEAL-C2`, migration ``0040``)."""


class StageUploadId(OpaqueId, prefix="stu", entity="StageUpload"):
    """Identity of one resumable stage-comparison upload batch."""


class StageUploadFileId(OpaqueId, prefix="suf", entity="StageUploadFile"):
    """Identity of one declared PDF or ZIP file; its name is only a hint."""


class StageUploadCandidateId(OpaqueId, prefix="suc", entity="StageUploadCandidate"):
    """Identity of one proposed document from a stage upload."""


class StagePairId(OpaqueId, prefix="stp", entity="StagePair"):
    """Identity of a confirmed П-to-Р document comparison."""


class StageAssemblyId(OpaqueId, prefix="sas", entity="StageAssembly"):
    """Identity of a Р-side assembly of several documents."""


class StageAssemblyMemberId(OpaqueId, prefix="sam", entity="StageAssemblyMember"):
    """Identity of one document's membership in an assembly."""


class StageLinkRevisionId(OpaqueId, prefix="slk", entity="StageLinkRevision"):
    """Identity of an append-only expert sheet-link revision."""


class StageLinkItemId(OpaqueId, prefix="sli", entity="StageLinkItem"):
    """Identity of one linked or explicitly unpaired sheet row in a revision."""


class StageTextFragmentId(OpaqueId, prefix="stf", entity="StageTextFragment"):
    """Identity of a deterministic, content-keyed text fragment."""


class StageTextExclusionId(OpaqueId, prefix="ste", entity="StageTextExclusion"):
    """Identity of one immutable same-text exclusion proof."""


class StageTextDifferenceId(OpaqueId, prefix="std", entity="StageTextDifference"):
    """Identity of one raw deterministic text difference."""


class StageTextHintId(OpaqueId, prefix="sth", entity="StageTextHint"):
    """Identity of a recommendation to inspect a cross-sheet text link."""


class StageChainRunId(OpaqueId, prefix="crn", entity="StageChainRun"):
    """Identity of one pinned seven-step comparison of a stage pair."""


class StageChainStepId(OpaqueId, prefix="cst", entity="StageChainStep"):
    """Identity of one step of a stage chain run."""



class StageAiUnitId(OpaqueId, prefix="saunit", entity="StageAiUnit"):
    """Opaque C4 StageAiUnit identity."""


class StageAiReviewId(OpaqueId, prefix="sarev", entity="StageAiReview"):
    """Opaque C4 StageAiReview identity."""


class StageAiClassificationId(OpaqueId, prefix="sacls", entity="StageAiClassification"):
    """Opaque C4 StageAiClassification identity."""


class StageAiSynthesisId(OpaqueId, prefix="sasyn", entity="StageAiSynthesis"):
    """Opaque C4 StageAiSynthesis identity."""


class StageGraphicEvidenceId(OpaqueId, prefix="sge", entity="StageGraphicEvidence"):
    """Opaque C4 StageGraphicEvidence identity."""


class StageLinkRepairId(OpaqueId, prefix="crp", entity="StageLinkRepair"):
    """Opaque C4 StageLinkRepair identity."""


class StageLinkRepairEventId(OpaqueId, prefix="crpe", entity="StageLinkRepairEvent"):
    """Opaque C4 StageLinkRepairEvent identity."""


class StageChangeCardId(OpaqueId, prefix="ccd", entity="StageChangeCard"):
    """Opaque C4 StageChangeCard identity."""


class StageCardEvidenceId(OpaqueId, prefix="sce", entity="StageCardEvidence"):
    """Opaque C4 StageCardEvidence identity."""


class StageCardVerdictId(OpaqueId, prefix="cdv", entity="StageCardVerdict"):
    """Opaque C4 StageCardVerdict identity."""


class StageChainBatchId(OpaqueId, prefix="scb", entity="StageChainBatch"):
    """Opaque C4 StageChainBatch identity."""


class StageChainBatchItemId(OpaqueId, prefix="scbi", entity="StageChainBatchItem"):
    """Opaque C4 StageChainBatchItem identity."""


class DecisionMemoryCaseId(OpaqueId, prefix="dmc", entity="DecisionMemoryCase"):
    """Opaque decision-memory case identity (ADR-0027): one reviewed observation, captured once."""


class DecisionMemoryDecisionId(OpaqueId, prefix="dmd", entity="DecisionMemoryDecision"):
    """Opaque decision-memory decision identity: one ledger event's copy inside a case."""


class DecisionMemoryStatusEventId(OpaqueId, prefix="dmw", entity="DecisionMemoryStatusEvent"):
    """Opaque decision-memory status event identity (withdraw, restore, forget; written from M2 on)."""


class DecisionMemoryCropId(OpaqueId, prefix="dmx", entity="DecisionMemoryCrop"):
    """Opaque decision-memory crop identity: a reference to one crop image a case keeps."""


class DecisionMemoryCommentId(OpaqueId, prefix="dmk", entity="DecisionMemoryComment"):
    """Identity of one expert comment kept with a decision-memory case (`CRIT-SEAL-50`, migration ``0063``, plan-v5 section 3.1)."""


class DecisionMemoryEmbeddingIntentId(OpaqueId, prefix="dmi", entity="DecisionMemoryEmbeddingIntent"):
    """Identity of one queued encoder job for a case view (`CRIT-SEAL-50`, migration ``0063``). The vector itself is keyed by case, revision, view and profile."""


class DecisionMemoryPatternId(OpaqueId, prefix="dmp", entity="DecisionMemoryPattern"):
    """Identity of one failure pattern: the refusing comment of the representative case of a group of refusals (`CRIT-SEAL-53`, migration ``0066``, plan-v5 section 3.7)."""


class DecisionMemoryPatternStatusEventId(OpaqueId, prefix="dps", entity="DecisionMemoryPatternStatusEvent"):
    """Identity of one event of a failure pattern's status journal: proposed, approved, rejected or suspended (`CRIT-SEAL-53`, migration ``0066``)."""


class VectorControlEventId(OpaqueId, prefix="vce", entity="VectorControlEvent"):
    """Identity of one change of the vectors' pause or of the night window's state (`CRIT-SEAL-50`, migration ``0063``)."""


class ExecutorTaskContextDeliveryId(OpaqueId, prefix="etd", entity="ExecutorTaskContextDelivery"):
    """Identity of one record of reference data handed to an agent with a task (`CRIT-SEAL-50`, migration ``0063``); the task, run and call it names are bare identities."""

#: Every concrete identity type, keyed by contract entity name.
IDENTITY_TYPES_BY_ENTITY: Final[dict[str, type[OpaqueId]]] = {
    identity.entity: identity for identity in _REGISTRY.values()
}

#: Every concrete identity type, keyed by contract prefix.
IDENTITY_TYPES_BY_PREFIX: Final[dict[str, type[OpaqueId]]] = dict(_REGISTRY)

#: Identifiers the alpha runner deliberately allocates nowhere. Recorded here, and in
#: ``docs/program/P02_SEAMS.md`` section 9, so the catalog does not silently promise
#: an aggregate nobody builds. The type exists; no active code path calls ``new()``.
UNALLOCATED_IN_PC01: Final[tuple[str, ...]] = (
    "import_id",
    "export_id",
    "comparison_id",
    "sheet_link_id",
    "norms_snapshot_id",
    "erasure_request_id",
    "object_uid",
    "discipline_uid",
)


def identity_type_for_prefix(prefix: str) -> type[OpaqueId]:
    """Look up the identity type bound to a contract prefix."""
    try:
        return _REGISTRY[prefix]
    except KeyError:
        raise IdentifierFormatError(f"no declared identity type for prefix {prefix!r}") from None
