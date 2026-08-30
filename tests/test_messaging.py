"""Tests for Identity-Native Messaging local skeleton."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from ie.cli import app
from runtime.database import initialize_database
from runtime.messaging import (
    MessagingError,
    collect_messaging_status,
    get_card,
    grant_consent,
    has_consent,
    list_consent_audit,
    list_cards,
    list_consents,
    list_inbox,
    register_card,
    send_envelope,
)
from runtime.messaging_metabolize import metabolize_message

# Fixed UUID-v7-shaped ids for deterministic tests
ID_A = "018f3a2b-7c9e-7d01-8a2b-000000000001"
ID_B = "018f3a2b-7c9e-7d01-8a2b-000000000002"
ID_C = "018f3a2b-7c9e-7d01-8a2b-000000000003"


def _card(
    identity_id: str,
    name: str = "test",
    *,
    default: str = "accept-all",
    allowlist: list[str] | None = None,
) -> dict:
    return {
        "identityId": identity_id,
        "name": name,
        "type": "agent",
        "version": "0.1",
        "endpoints": {"messaging": "http://127.0.0.1:7420/messaging"},
        "recognitionPolicy": {
            "default": default,
            "allowlist": allowlist or [],
        },
    }


def _envelope(
    from_id: str,
    to_id: str,
    *,
    signal_type: str = "message",
    impact_hints: list[str] | None = None,
    inline: str = "hello",
) -> dict:
    env: dict = {
        "from": from_id,
        "to": to_id,
        "signal": {"type": signal_type},
        "payload": {"contentType": "text/plain", "inline": inline},
    }
    if impact_hints is not None:
        env["impactHints"] = impact_hints
    return env


class MessagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".ie").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_register_and_list_card(self) -> None:
        card = register_card(self.root, _card(ID_A, "alice"))
        self.assertEqual(card["identityId"], ID_A)
        self.assertEqual(get_card(self.root, ID_A)["name"], "alice")
        self.assertEqual(len(list_cards(self.root)), 1)

    def test_register_allows_existing_local_identity_id(self) -> None:
        metadata = initialize_database(self.root, handle="jonas", preferred_name="Jonas")
        card = register_card(self.root, _card(metadata["identity_id"], "Jonas"))
        self.assertEqual(card["identityId"], metadata["identity_id"])

    def test_register_rejects_bad_uuid(self) -> None:
        bad = _card("not-a-uuid")
        with self.assertRaises(MessagingError):
            register_card(self.root, bad)

    def test_send_delivered_accept_all(self) -> None:
        register_card(self.root, _card(ID_B, "bob", default="accept-all"))
        result = send_envelope(self.root, _envelope(ID_A, ID_B))
        self.assertEqual(result.status, "delivered")
        self.assertEqual(result.receipt["receiptType"], "delivered")
        self.assertEqual(len(list_inbox(self.root)), 1)

    def test_send_rejected_unknown_target(self) -> None:
        result = send_envelope(self.root, _envelope(ID_A, ID_B))
        self.assertEqual(result.status, "rejected")
        self.assertIn("not found", result.receipt["reason"])

    def test_send_rejected_recognition(self) -> None:
        register_card(
            self.root,
            _card(ID_B, "bob", default="accept-known", allowlist=[ID_C]),
        )
        result = send_envelope(self.root, _envelope(ID_A, ID_B))
        self.assertEqual(result.status, "rejected")
        self.assertIn("recognition", result.receipt["reason"])

    def test_send_allowlist_ok(self) -> None:
        register_card(
            self.root,
            _card(ID_B, "bob", default="accept-known", allowlist=[ID_A]),
        )
        result = send_envelope(self.root, _envelope(ID_A, ID_B))
        self.assertEqual(result.status, "delivered")

    def test_mass_altering_rejected_without_consent(self) -> None:
        register_card(self.root, _card(ID_B, "bob", default="accept-all"))
        result = send_envelope(
            self.root,
            _envelope(ID_A, ID_B, impact_hints=["mass-altering"]),
        )
        self.assertEqual(result.status, "rejected")
        self.assertIn("consent", result.receipt["reason"])

    def test_mass_altering_delivered_with_prior_grant(self) -> None:
        register_card(self.root, _card(ID_B, "bob", default="accept-all"))
        grant_consent(
            self.root,
            target_id=ID_B,
            sender_id=ID_A,
            impact_classes=["mass-altering"],
        )
        self.assertTrue(
            has_consent(
                self.root,
                target_id=ID_B,
                sender_id=ID_A,
                impact_classes=["mass-altering"],
            )
        )
        result = send_envelope(
            self.root,
            _envelope(ID_A, ID_B, impact_hints=["mass-altering"]),
        )
        self.assertEqual(result.status, "delivered")

    def test_consent_grant_signal_persists_grant(self) -> None:
        # B (granter) sends consent-grant TO A (grantee).
        # After that, A may send stem-altering messages TO B.
        register_card(self.root, _card(ID_A, "alice", default="accept-all"))
        register_card(self.root, _card(ID_B, "bob", default="accept-all"))

        result = send_envelope(
            self.root,
            _envelope(
                ID_B,  # granter
                ID_A,  # grantee
                signal_type="consent-grant",
                inline=json.dumps({"impactClasses": ["stem-altering"]}),
            ),
        )
        self.assertEqual(result.status, "delivered")
        self.assertTrue(
            has_consent(
                self.root,
                target_id=ID_B,
                sender_id=ID_A,
                impact_classes=["stem-altering"],
            )
        )
        self.assertFalse(
            has_consent(
                self.root,
                target_id=ID_B,
                sender_id=ID_A,
                impact_classes=["mass-altering"],
            )
        )

        # A can now deliver stem-altering to B
        follow = send_envelope(
            self.root,
            _envelope(ID_A, ID_B, impact_hints=["stem-altering"]),
        )
        self.assertEqual(follow.status, "delivered")

    def test_status_exposes_consent_audit_metabolization_and_rejection_reason(self) -> None:
        register_card(self.root, _card(ID_B, "bob", default="accept-known", allowlist=[ID_A]))
        grant_consent(
            self.root,
            target_id=ID_B,
            sender_id=ID_A,
            impact_classes=["mass-altering"],
        )
        delivered = send_envelope(
            self.root,
            _envelope(ID_A, ID_B, impact_hints=["mass-altering"]),
        )
        self.assertEqual(delivered.status, "delivered")
        metabolize_message(self.root, delivered.envelope["messageId"])

        rejected = send_envelope(self.root, _envelope(ID_C, ID_B))
        self.assertEqual(rejected.status, "rejected")

        status = collect_messaging_status(self.root)
        self.assertEqual(status["consents"]["count"], 1)
        self.assertEqual(len(list_consents(self.root)), 1)
        self.assertEqual(status["consent_audit"]["count"], 1)
        self.assertEqual(len(list_consent_audit(self.root)), 1)
        self.assertEqual(status["metabolizations"]["count"], 1)
        self.assertEqual(status["receipts"]["by_type"]["metabolized"], 1)
        self.assertEqual(status["rejections"][0]["reason"], rejected.receipt["reason"])

    def test_cli_status_lists_messaging_loop(self) -> None:
        initialize_database(self.root, handle="me", preferred_name="Me")
        register_card(self.root, _card(ID_B, "bob", default="accept-all"))
        send_envelope(self.root, _envelope(ID_A, ID_B))

        result = CliRunner().invoke(
            app,
            ["messaging", "status", "--path", str(self.root), "--json"],
        )
        self.assertEqual(result.exit_code, 0, result.output)
        status = json.loads(result.output)
        self.assertEqual(status["outbox"]["count"], 1)
        self.assertEqual(status["receipts"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
