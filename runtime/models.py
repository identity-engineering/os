"""Core data models for Surface Runtime v0 (stdlib only)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApplyStatus(str, Enum):
    ACCEPTED = "accepted"
    APPLIED = "applied"
    REJECTED = "rejected"
    PARTIAL = "partial"


class RequestStatus(str, Enum):
    PENDING = "pending"
    IGNORED = "ignored"
    QUARANTINED = "quarantined"
    ANSWERED = "answered"
    EXPIRED = "expired"


@dataclass
class InteractionSignal:
    """Minimal Interaction Signal payload (mirrors schemas/interaction-signal/v0.yaml)."""

    from_handle: str
    to_handle: str
    timestamp: str
    existence: bool = True
    interaction_depth_delta: float = 0.0

    # Consent-based (optional)
    coarse_mass_estimate: Optional[float] = None
    mass_confidence: Optional[float] = None
    dimensions_delta: Optional[list[dict[str, Any]]] = None
    relation_pull: Optional[float] = None

    # Meta
    schema_version: str = "0"
    transport: str = "cli"
    # Optional reply linkage to an inbound estimate request (schemas/estimate-request)
    in_reply_to_request_id: Optional[str] = None

    def validate_required(self) -> list[str]:
        errors: list[str] = []
        if not self.from_handle:
            errors.append("from_handle required")
        if not self.to_handle:
            errors.append("to_handle required")
        if not self.timestamp:
            errors.append("timestamp required")
        if not isinstance(self.existence, bool):
            errors.append("existence must be bool")
        if not (0.0 <= float(self.interaction_depth_delta) <= 1.0):
            errors.append("interaction_depth_delta must be in [0.0, 1.0]")
        return errors


@dataclass
class Receipt:
    receipt_id: str
    status: ApplyStatus
    timestamp: str
    from_handle: str
    to_handle: str
    applied_fields: list[str] = field(default_factory=list)
    rejected_fields: list[dict[str, str]] = field(default_factory=list)
    reason: str = ""
    quarantine: bool = False

    @classmethod
    def create(
        cls,
        status: ApplyStatus,
        from_handle: str,
        to_handle: str,
        *,
        applied: Optional[list[str]] = None,
        rejected: Optional[list[dict[str, str]]] = None,
        reason: str = "",
        quarantine: bool = False,
    ) -> "Receipt":
        return cls(
            receipt_id=str(uuid4()),
            status=status,
            timestamp=_utcnow(),
            from_handle=from_handle,
            to_handle=to_handle,
            applied_fields=applied or [],
            rejected_fields=rejected or [],
            reason=reason,
            quarantine=quarantine,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class ForeignEstimateRecord:
    """One sender's footprint inside the observer's foreign-estimate zone."""

    sender_handle: str
    sender_substrate: Optional[str] = None
    first_signal_at: str = ""
    last_signal_at: str = ""
    signal_count: int = 0
    accumulated_depth: float = 0.0
    last_depth_delta: float = 0.0
    existence_confirmed: bool = False

    coarse_mass_estimate: Optional[float] = None
    mass_confidence: Optional[float] = None
    mass_estimate_at: Optional[str] = None
    dimensions_delta: Optional[list[dict[str, Any]]] = None
    relation_pull: Optional[float] = None
    last_receipt_id: Optional[str] = None
    quarantine: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForeignEstimateRecord":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class EstimateRequest:
    """Inbound estimate request (mirrors schemas/estimate-request/v0.yaml)."""

    request_id: str
    requester_handle: str
    target_handle: str
    timestamp: str
    status: RequestStatus = RequestStatus.PENDING
    requested_fields: list[str] = field(default_factory=list)
    note: Optional[str] = None
    schema_version: str = "0"
    transport: str = "cli"
    answered_at: Optional[str] = None
    reply_receipt_id: Optional[str] = None
    ignored_at: Optional[str] = None
    quarantine: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, RequestStatus) else self.status
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EstimateRequest":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        filtered = {k: v for k, v in data.items() if k in known}
        status = filtered.get("status", "pending")
        if isinstance(status, str):
            try:
                filtered["status"] = RequestStatus(status)
            except ValueError:
                filtered["status"] = RequestStatus.PENDING
        return cls(**filtered)

    @classmethod
    def create(
        cls,
        requester_handle: str,
        target_handle: str,
        *,
        requested_fields: Optional[list[str]] = None,
        note: Optional[str] = None,
        transport: str = "cli",
        request_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> "EstimateRequest":
        return cls(
            request_id=request_id or str(uuid4()),
            requester_handle=requester_handle,
            target_handle=target_handle,
            timestamp=timestamp or _utcnow(),
            status=RequestStatus.PENDING,
            requested_fields=list(requested_fields or []),
            note=note,
            transport=transport,
        )
