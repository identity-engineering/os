"""Estimate request + inbox path for the bidirectional gravitational sensor."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .models import EstimateRequest, RequestStatus, _utcnow
from .storage import InboundRequestStore

# Soft local guard (not a time window). Symmetric spirit to signal rate limits.
DEFAULT_MAX_PENDING_PER_REQUESTER = 20


class RequestError(ValueError):
    """Raised for invalid request operations."""


def create_inbound_request(
    *,
    registry_root: Union[str, Path],
    requester_handle: str,
    target_handle: str,
    requested_fields: Optional[list[str]] = None,
    note: Optional[str] = None,
    transport: str = "cli",
    request_id: Optional[str] = None,
    max_pending_per_requester: int = DEFAULT_MAX_PENDING_PER_REQUESTER,
) -> EstimateRequest:
    """Land an estimate request in *this* install's inbound inbox.

    Never auto-answers. Does not touch Stem / Vision / access policy.
    """
    if not requester_handle:
        raise RequestError("requester_handle required")
    if not target_handle:
        raise RequestError("target_handle required")

    store = InboundRequestStore(Path(registry_root))
    pending = store.count_pending_from(requester_handle)
    if pending >= max_pending_per_requester:
        raise RequestError(
            f"too many pending requests from {requester_handle!r} "
            f"(limit {max_pending_per_requester})"
        )

    req = EstimateRequest.create(
        requester_handle=requester_handle,
        target_handle=target_handle,
        requested_fields=requested_fields,
        note=note,
        transport=transport,
        request_id=request_id,
    )
    store.save(req)
    return req


def list_inbound_requests(
    registry_root: Union[str, Path],
    *,
    status: Optional[RequestStatus] = None,
) -> list[EstimateRequest]:
    store = InboundRequestStore(Path(registry_root))
    if status is None:
        return store.list_all()
    return store.list_by_status(status)


def get_inbound_request(
    registry_root: Union[str, Path],
    request_id: str,
) -> Optional[EstimateRequest]:
    return InboundRequestStore(Path(registry_root)).load(request_id)


def set_request_status(
    registry_root: Union[str, Path],
    request_id: str,
    status: RequestStatus,
) -> EstimateRequest:
    """Owner-side status change: ignore / quarantine (or re-open to pending)."""
    store = InboundRequestStore(Path(registry_root))
    req = store.load(request_id)
    if req is None:
        raise RequestError(f"no request {request_id!r}")

    if status == RequestStatus.ANSWERED:
        raise RequestError("use mark_request_answered after a reply signal apply")

    req.status = status
    if status == RequestStatus.IGNORED:
        req.ignored_at = _utcnow()
        req.quarantine = False
    elif status == RequestStatus.QUARANTINED:
        req.quarantine = True
    elif status == RequestStatus.PENDING:
        req.ignored_at = None
        req.quarantine = False
        req.answered_at = None
        req.reply_receipt_id = None

    store.save(req)
    return req


def mark_request_answered(
    registry_root: Union[str, Path],
    request_id: str,
    reply_receipt_id: str,
) -> Optional[EstimateRequest]:
    """Link a successful reply signal to a pending/ignored request.

    Returns None if the request_id is unknown (signal still applies;
    linkage is best-effort audit).
    """
    store = InboundRequestStore(Path(registry_root))
    req = store.load(request_id)
    if req is None:
        return None

    req.status = RequestStatus.ANSWERED
    req.answered_at = _utcnow()
    req.reply_receipt_id = reply_receipt_id
    req.quarantine = False
    store.save(req)
    return req


def create_request_from_dict(
    payload: dict,
    *,
    registry_root: Union[str, Path],
    expected_target_handle: Optional[str] = None,
) -> EstimateRequest:
    """Dict → create_inbound_request (HTTP/CLI convenience)."""
    requester = str(payload.get("requester") or payload.get("from") or payload.get("requester_handle") or "")
    target = str(payload.get("target") or payload.get("to") or payload.get("target_handle") or "")
    if expected_target_handle and target and target != expected_target_handle:
        raise RequestError(
            f"target_handle mismatch: expected {expected_target_handle}, got {target}"
        )
    if expected_target_handle and not target:
        target = expected_target_handle

    fields = payload.get("requested_fields") or payload.get("scope") or []
    if isinstance(fields, str):
        fields = [f.strip() for f in fields.split(",") if f.strip()]

    return create_inbound_request(
        registry_root=registry_root,
        requester_handle=requester,
        target_handle=target,
        requested_fields=list(fields),
        note=payload.get("note"),
        transport=str(payload.get("transport", "cli")),
        request_id=payload.get("request_id"),
    )
