"""Tests for the optional local Managed sync queue."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch
from pathlib import Path

from runtime.database import canonical_json, initialize_database, sha256_text
from runtime.managed_sync import (
    ManagedSyncEnvelope,
    ManagedSyncHttpClient,
    ManagedSyncQueue,
    SyncQueueConflict,
    SyncQueueError,
    SyncSendResult,
)
from runtime.models import InteractionSignal


class ManagedSyncQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        initialize_database(self.root, handle="alice", preferred_name="Alice")
        self.queue = ManagedSyncQueue(self.root, base_delay_seconds=5, max_delay_seconds=60)
        self.signal = InteractionSignal(
            from_handle="alice",
            to_handle="peer-alice",
            timestamp="2026-08-08T12:00:00+00:00",
            interaction_depth_delta=0.25,
            transport="managed-queue",
        )
        self.envelope = ManagedSyncEnvelope.from_signal(
            self.signal,
            identity_id="identity-a",
            previous_cursor=None,
            cursor="cursor-1",
            event_id="event-1",
            idempotency_key="delivery-1",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_enqueue_is_durable_and_idempotent(self) -> None:
        first = self.queue.enqueue(self.envelope, now="2026-08-08T12:00:00Z")
        retry = self.queue.enqueue(self.envelope, now="2026-08-08T12:00:01Z")

        self.assertEqual(retry.queue_id, first.queue_id)
        self.assertEqual(len(self.queue.list_events()), 1)
        self.assertEqual(self.queue.list_due(now="2026-08-08T12:00:02Z")[0].status, "pending")

        conflicting = replace(self.envelope, cursor="cursor-other")
        with self.assertRaises(SyncQueueConflict):
            self.queue.enqueue(conflicting, now="2026-08-08T12:00:02Z")

    def test_malformed_payload_is_rejected_before_enqueue(self) -> None:
        payload = dict(self.envelope.payload)
        payload["interaction_depth_delta"] = "0.25"
        with self.assertRaises(ValueError):
            replace(
                self.envelope,
                payload=payload,
                payload_sha256=sha256_text(canonical_json(payload)),
            )

    def test_transient_failure_uses_exponential_backoff_and_ack_updates_state(self) -> None:
        self.queue.enqueue(self.envelope, now="2026-08-08T12:00:00Z")
        sent: list[str] = []

        def sender(envelope: ManagedSyncEnvelope) -> SyncSendResult:
            sent.append(envelope.event_id)
            if len(sent) == 1:
                return SyncSendResult(status=503, error="offline")
            return SyncSendResult(status=201, server_cursor="1")

        first = self.queue.drain(sender, now="2026-08-08T12:00:00Z")
        self.assertEqual(first.attempted, 1)
        self.assertEqual(first.retried, 1)
        delayed = self.queue.list_events()[0]
        self.assertEqual(delayed.status, "retry")
        self.assertEqual(delayed.attempts, 1)
        self.assertEqual(delayed.next_attempt_at, "2026-08-08T12:00:05+00:00")

        before_due = self.queue.drain(sender, now="2026-08-08T12:00:04Z")
        self.assertEqual(before_due.attempted, 0)

        second = self.queue.drain(sender, now="2026-08-08T12:00:05Z")
        self.assertEqual(second.accepted, 1)
        accepted = self.queue.list_events()[0]
        self.assertEqual(accepted.status, "accepted")
        self.assertEqual(accepted.server_cursor, "1")
        self.assertEqual(
            self.queue.stream_state("identity:identity-a:interaction"),
            {"client_cursor": "cursor-1", "server_cursor": "1"},
        )

    def test_conflict_blocks_stream_and_preserves_later_event(self) -> None:
        self.queue.enqueue(self.envelope, now="2026-08-08T12:00:00Z")
        later = ManagedSyncEnvelope.from_signal(
            self.signal,
            identity_id="identity-a",
            previous_cursor="cursor-1",
            cursor="cursor-2",
            event_id="event-2",
            idempotency_key="delivery-2",
        )
        self.queue.enqueue(later, now="2026-08-08T12:00:01Z")

        result = self.queue.drain(
            lambda _: SyncSendResult(status=409, error="cursor conflict"),
            now="2026-08-08T12:00:02Z",
        )
        self.assertEqual(result.blocked, 1)
        self.assertEqual(self.queue.list_due(now="2026-08-08T12:00:03Z"), [])
        self.assertEqual(
            [event.status for event in self.queue.list_events()],
            ["blocked", "pending"],
        )

        self.queue.requeue_blocked(
            self.queue.list_events()[0].queue_id,
            now="2026-08-08T12:00:04Z",
        )
        self.assertEqual(len(self.queue.list_due(now="2026-08-08T12:00:04Z")), 1)

    def test_retry_after_overrides_backoff(self) -> None:
        self.queue.enqueue(self.envelope, now="2026-08-08T12:00:00Z")
        result = self.queue.drain(
            lambda _: SyncSendResult(status=429, retry_after_seconds=17),
            now="2026-08-08T12:00:00Z",
        )

        self.assertEqual(result.retried, 1)
        self.assertEqual(
            self.queue.list_events()[0].next_attempt_at,
            "2026-08-08T12:00:17+00:00",
        )

    def test_reopened_queue_keeps_state(self) -> None:
        self.queue.enqueue(self.envelope, now="2026-08-08T12:00:00Z")
        reopened = ManagedSyncQueue(self.root)

        self.assertEqual(len(reopened.list_events()), 1)
        self.assertEqual(reopened.list_events()[0].envelope.event_id, "event-1")

    def test_active_lease_prevents_duplicate_claim_until_expiry(self) -> None:
        event = self.queue.enqueue(self.envelope, now="2026-08-08T12:00:00Z")
        first = self.queue._begin_attempt(event.queue_id, "2026-08-08T12:00:00+00:00")
        second = self.queue._begin_attempt(event.queue_id, "2026-08-08T12:00:01+00:00")
        recovered = self.queue._begin_attempt(event.queue_id, "2026-08-08T17:00:01+00:00")

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertIsNotNone(recovered)

    def test_http_recovery_acknowledges_server_accepted_event(self) -> None:
        event = self.queue.enqueue(self.envelope, now="2026-08-08T12:00:00Z")
        stream = self.envelope.stream
        pulled_event = {
            "serverSequence": "1",
            "eventId": self.envelope.event_id,
            "stream": stream,
            "entityType": self.envelope.entity_type,
            "entityId": self.envelope.entity_id,
            "idempotencyKey": self.envelope.idempotency_key,
            "payload": self.envelope.payload,
            "payloadSha256": self.envelope.payload_sha256,
            "occurredAt": self.envelope.occurred_at,
            "receivedAt": "2026-08-08T12:00:01+00:00",
        }
        responses = [
            {
                "sync": {
                    "installationId": "installation-1",
                    "stream": stream,
                    "cursor": "cursor-1",
                    "serverCursor": "1",
                }
            },
            {
                "sync": {
                    "installationId": "installation-1",
                    "stream": stream,
                    "cursor": "cursor-1",
                    "serverCursor": "1",
                    "nextCursor": "1",
                    "hasMore": False,
                    "events": [pulled_event],
                }
            },
        ]

        class FakeResponse:
            def __init__(self, body: dict):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                import json

                return json.dumps(self.body).encode("utf-8")

        client = ManagedSyncHttpClient(
            "https://managed.example",
            "installation-1",
            "token",
        )
        with patch(
            "runtime.managed_sync.urlopen",
            side_effect=[FakeResponse(responses[0]), FakeResponse(responses[1])],
        ) as open_url:
            result = client.recover(
                self.queue,
                stream,
                now="2026-08-08T12:00:02Z",
            )

        self.assertEqual(result.next_cursor, "1")
        self.assertEqual(result.events[0].event_id, event.envelope.event_id)
        self.assertEqual(self.queue.list_events()[0].status, "accepted")
        self.assertEqual(
            self.queue.stream_state(stream),
            {"client_cursor": "cursor-1", "server_cursor": "1"},
        )
        self.assertIn("/sync/status?", open_url.call_args_list[0].args[0].full_url)
        self.assertIn("/sync/events?", open_url.call_args_list[1].args[0].full_url)

    def test_server_cursor_can_be_recorded_after_pull(self) -> None:
        self.queue.record_server_cursor(
            "identity:identity-a:interaction",
            "7",
            now="2026-08-08T12:00:00Z",
        )
        self.assertEqual(
            self.queue.stream_state("identity:identity-a:interaction"),
            {"client_cursor": None, "server_cursor": "7"},
        )

    def test_http_pull_rejects_invalid_recomputed_payload(self) -> None:
        payload = dict(self.envelope.payload)
        payload["interaction_depth_delta"] = "0.25"
        pulled_event = {
            "serverSequence": "1",
            "eventId": self.envelope.event_id,
            "stream": self.envelope.stream,
            "entityType": self.envelope.entity_type,
            "entityId": self.envelope.entity_id,
            "idempotencyKey": self.envelope.idempotency_key,
            "payload": payload,
            "payloadSha256": sha256_text(canonical_json(payload)),
            "occurredAt": self.envelope.occurred_at,
            "receivedAt": "2026-08-08T12:00:01+00:00",
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                import json

                return json.dumps(
                    {
                        "sync": {
                            "installationId": "installation-1",
                            "stream": self_stream,
                            "serverCursor": "1",
                            "nextCursor": "1",
                            "hasMore": False,
                            "events": [pulled_event],
                        }
                    }
                ).encode("utf-8")

        self_stream = self.envelope.stream
        client = ManagedSyncHttpClient(
            "https://managed.example",
            "installation-1",
            "token",
        )
        with patch("runtime.managed_sync.urlopen", return_value=FakeResponse()):
            with self.assertRaises(SyncQueueError):
                client.pull(self_stream, after="0")

    def test_http_pull_rejects_backwards_next_cursor(self) -> None:
        stream = self.envelope.stream

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                import json

                return json.dumps(
                    {
                        "sync": {
                            "installationId": "installation-1",
                            "stream": stream,
                            "serverCursor": "5",
                            "nextCursor": "4",
                            "hasMore": False,
                            "events": [],
                        }
                    }
                ).encode("utf-8")

        client = ManagedSyncHttpClient(
            "https://managed.example",
            "installation-1",
            "token",
        )
        with patch("runtime.managed_sync.urlopen", return_value=FakeResponse()):
            with self.assertRaises(SyncQueueError):
                client.pull(stream, after="5")

    def test_recovery_does_not_move_client_cursor_backward(self) -> None:
        first = self.queue.enqueue(self.envelope, now="2026-08-08T12:00:00Z")
        older = ManagedSyncEnvelope.from_signal(
            self.signal,
            identity_id="identity-a",
            previous_cursor=None,
            cursor="cursor-older",
            event_id="event-2",
            idempotency_key="delivery-2",
        )
        second = self.queue.enqueue(older, now="2026-08-08T12:00:01Z")

        self.assertTrue(
            self.queue.acknowledge_server_event(
                first.envelope.event_id,
                "5",
                now="2026-08-08T12:00:02Z",
            )
        )
        self.assertTrue(
            self.queue.acknowledge_server_event(
                second.envelope.event_id,
                "5",
                now="2026-08-08T12:00:03Z",
            )
        )

        self.assertEqual(
            self.queue.stream_state(self.envelope.stream),
            {"client_cursor": "cursor-1", "server_cursor": "5"},
        )


if __name__ == "__main__":
    unittest.main()