"""Tests for A2A adapter mapping."""

from __future__ import annotations

import unittest

from runtime.a2a_adapter import agent_card_to_identity_card, identity_card_to_agent_card
from runtime.messaging import MessagingError

ID_A = "018f3a2b-7c9e-7d01-8a2b-000000000001"


def _identity_card() -> dict:
    return {
        "identityId": ID_A,
        "name": "coding-agent-jonas-01",
        "type": "agent",
        "version": "0.1",
        "description": "Personal coding agent",
        "ownerIdentityId": "018f3a2b-7c9e-7d01-8a2b-000000000099",
        "scope": "personal",
        "endpoints": {
            "messaging": "http://127.0.0.1:7420/ie/v0/messaging",
        },
        "recognitionPolicy": {"default": "accept-known"},
        "capabilities": [
            {"name": "code-review", "description": "Review pull requests"},
        ],
    }


class A2AAdapterTests(unittest.TestCase):
    def test_export_agent_card_shape(self) -> None:
        agent = identity_card_to_agent_card(_identity_card())
        self.assertEqual(agent["name"], "coding-agent-jonas-01")
        self.assertEqual(agent["protocolVersion"], "1.0")
        self.assertTrue(agent["supportedInterfaces"])
        self.assertEqual(
            agent["supportedInterfaces"][0]["url"],
            "http://127.0.0.1:7420/ie/v0/messaging",
        )
        self.assertEqual(agent["x-ie"]["identityId"], ID_A)
        self.assertEqual(agent["skills"][0]["id"], "code-review")

    def test_import_agent_card_v1(self) -> None:
        agent = {
            "name": "external-agent",
            "description": "From A2A land",
            "version": "2.0.0",
            "supportedInterfaces": [
                {
                    "url": "https://agents.example.com/a2a/v1",
                    "protocolBinding": "JSONRPC",
                    "protocolVersion": "1.0",
                }
            ],
            "skills": [{"id": "search", "name": "search", "description": "Web search"}],
            "capabilities": {"streaming": True},
        }
        card = agent_card_to_identity_card(agent)
        self.assertEqual(card["name"], "external-agent")
        self.assertEqual(card["type"], "agent")
        self.assertEqual(card["version"], "0.1")
        self.assertEqual(card["endpoints"]["a2a"], "https://agents.example.com/a2a/v1")
        self.assertEqual(
            card["endpoints"]["messaging"], "https://agents.example.com/a2a/v1"
        )
        self.assertEqual(card["capabilities"][0]["name"], "search")

    def test_import_legacy_url(self) -> None:
        agent = {
            "name": "legacy",
            "url": "https://legacy.example.com/agent",
            "protocolVersion": "0.3",
        }
        card = agent_card_to_identity_card(agent)
        self.assertEqual(card["endpoints"]["a2a"], "https://legacy.example.com/agent")

    def test_round_trip_preserves_identity_id(self) -> None:
        original = _identity_card()
        agent = identity_card_to_agent_card(original)
        back = agent_card_to_identity_card(agent)
        self.assertEqual(back["identityId"], ID_A)
        self.assertEqual(back["type"], "agent")
        self.assertEqual(back["scope"], "personal")
        self.assertEqual(
            back["endpoints"]["messaging"],
            "http://127.0.0.1:7420/ie/v0/messaging",
        )

    def test_export_requires_name(self) -> None:
        with self.assertRaises(MessagingError):
            identity_card_to_agent_card({"endpoints": {"messaging": "http://x"}})


if __name__ == "__main__":
    unittest.main()
