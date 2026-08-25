"""A2A adapter: map between IE Identity Cards and A2A Agent Cards.

Does not reimplement A2A task execution. Only discovery metadata mapping
so existing A2A agents can be registered into IE messaging and IE Identities
can advertise a compatible Agent Card.

Target: A2A v1.0-style Agent Card (supportedInterfaces preferred;
falls back to legacy top-level url for v0.3 imports).
"""

from __future__ import annotations

from typing import Any, Optional

from .messaging import MessagingError, _new_uuid_v7, _utc_now

A2A_PROTOCOL_VERSION = "1.0"
IE_CARD_VERSION = "0.1"


def identity_card_to_agent_card(
    identity_card: dict,
    *,
    messaging_base_url: Optional[str] = None,
) -> dict:
    """Project an IE Identity Card into an A2A-compatible Agent Card.

    IE-specific fields are kept under `x-ie` so pure A2A clients can ignore them.
    """
    if not isinstance(identity_card, dict):
        raise MessagingError("identity_card must be an object")
    name = identity_card.get("name")
    if not name:
        raise MessagingError("identity_card.name is required")

    endpoints = identity_card.get("endpoints") or {}
    messaging_url = endpoints.get("messaging") or messaging_base_url
    a2a_url = endpoints.get("a2a") or messaging_url
    if not a2a_url:
        raise MessagingError("need endpoints.messaging or endpoints.a2a for Agent Card")

    skills: list[dict] = []
    for cap in identity_card.get("capabilities") or []:
        if not isinstance(cap, dict) or not cap.get("name"):
            continue
        skills.append(
            {
                "id": cap.get("name"),
                "name": cap.get("name"),
                "description": cap.get("description") or "",
                "tags": [],
                "examples": [],
            }
        )

    agent_card: dict[str, Any] = {
        "name": name,
        "description": identity_card.get("description") or f"IE Identity ({identity_card.get('type', 'unknown')})",
        "version": identity_card.get("version") or IE_CARD_VERSION,
        "protocolVersion": A2A_PROTOCOL_VERSION,
        "supportedInterfaces": [
            {
                "url": a2a_url,
                "protocolBinding": "HTTP+JSON",
                "protocolVersion": A2A_PROTOCOL_VERSION,
            }
        ],
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "extendedAgentCard": False,
        },
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": skills,
        "x-ie": {
            "identityId": identity_card.get("identityId"),
            "type": identity_card.get("type"),
            "scope": identity_card.get("scope"),
            "ownerIdentityId": identity_card.get("ownerIdentityId"),
            "endpoints": endpoints,
            "recognitionPolicy": identity_card.get("recognitionPolicy"),
            "frequencySignature": identity_card.get("frequencySignature"),
            "causalEntropyConstraints": identity_card.get("causalEntropyConstraints"),
            "updatedAt": identity_card.get("updatedAt"),
        },
    }
    # Drop None values inside x-ie for cleaner export
    agent_card["x-ie"] = {k: v for k, v in agent_card["x-ie"].items() if v is not None}
    return agent_card


def agent_card_to_identity_card(
    agent_card: dict,
    *,
    identity_id: Optional[str] = None,
    identity_type: str = "agent",
    messaging_url: Optional[str] = None,
) -> dict:
    """Import an A2A Agent Card into a minimal IE Identity Card.

    Prefer `x-ie` block when present (round-trip). Otherwise synthesize.
    """
    if not isinstance(agent_card, dict):
        raise MessagingError("agent_card must be an object")
    name = agent_card.get("name")
    if not name:
        raise MessagingError("agent_card.name is required")

    x_ie = agent_card.get("x-ie") or {}
    if not isinstance(x_ie, dict):
        x_ie = {}

    resolved_id = identity_id or x_ie.get("identityId") or _new_uuid_v7()
    endpoints = dict(x_ie.get("endpoints") or {})

    # Resolve A2A endpoint from v1.0 supportedInterfaces or legacy url
    a2a_url = endpoints.get("a2a")
    if not a2a_url:
        interfaces = agent_card.get("supportedInterfaces") or []
        if interfaces and isinstance(interfaces[0], dict):
            a2a_url = interfaces[0].get("url")
        if not a2a_url:
            a2a_url = agent_card.get("url")
    if a2a_url:
        endpoints["a2a"] = a2a_url

    msg = messaging_url or endpoints.get("messaging") or a2a_url
    if not msg:
        raise MessagingError("cannot derive endpoints.messaging from Agent Card")
    endpoints["messaging"] = msg

    capabilities: list[dict] = []
    for skill in agent_card.get("skills") or []:
        if not isinstance(skill, dict):
            continue
        skill_name = skill.get("name") or skill.get("id")
        if not skill_name:
            continue
        capabilities.append(
            {
                "name": skill_name,
                "description": skill.get("description") or "",
            }
        )

    card: dict[str, Any] = {
        "identityId": resolved_id,
        "name": name,
        "type": x_ie.get("type") or identity_type,
        "version": IE_CARD_VERSION,
        "description": agent_card.get("description") or "",
        "endpoints": endpoints,
        "updatedAt": x_ie.get("updatedAt") or _utc_now(),
    }
    if x_ie.get("ownerIdentityId"):
        card["ownerIdentityId"] = x_ie["ownerIdentityId"]
    if x_ie.get("scope"):
        card["scope"] = x_ie["scope"]
    if x_ie.get("recognitionPolicy"):
        card["recognitionPolicy"] = x_ie["recognitionPolicy"]
    if x_ie.get("frequencySignature"):
        card["frequencySignature"] = x_ie["frequencySignature"]
    if x_ie.get("causalEntropyConstraints"):
        card["causalEntropyConstraints"] = x_ie["causalEntropyConstraints"]
    if capabilities:
        card["capabilities"] = capabilities
    return card
