# Optional Managed Sync Queue

The SQLite-first Core can persist Managed sync envelopes locally without making
an account or network connection part of the Free path. The queue is an
adapter-owned layer; local Interaction apply and Mature remain usable when it
is disabled.

## Contract

```python
from runtime.managed_sync import ManagedSyncEnvelope, ManagedSyncQueue

queue = ManagedSyncQueue(install_root)
envelope = ManagedSyncEnvelope.from_signal(
    signal,
    identity_id=identity_id,
    previous_cursor=previous_cursor,
    cursor=next_cursor,
)
queue.enqueue(envelope)
```

`ManagedSyncEnvelope` uses the canonical Open Core signal payload and its
lowercase SHA-256. It validates the strict `interaction.signal` fields before
the row is inserted. Mature events are outside this queue contract.

## Local state

`managed_sync_queue` is append-oriented and idempotent by both `event_id` and
`idempotency_key`. Reusing either key with different stream, cursor, timestamp,
or payload content raises a conflict. The queue preserves creation order per
stream, so a later event cannot pass an earlier pending, retry, or blocked
event.

The states are:

- `pending`: ready for its first attempt;
- `retry`: temporarily delayed after a retryable failure;
- `blocked`: stopped after a non-retryable 4xx response; and
- `accepted`: durably acknowledged by Managed.

Drainers claim rows through expiring SQLite leases. A crashed process leaves no
permanent in-flight state: another process may reclaim the row after the lease
expires. A blocked event must be explicitly repaired and requeued with
`requeue_blocked()`.

Network failures, 408, 425, 429, and 5xx responses retry with exponential
backoff starting at five seconds and capped at one hour by default. An integer
`Retry-After` header overrides the calculated delay within that cap. Other 4xx
responses are blocked so a malformed payload or cursor conflict does not spin
forever.

## Durable recovery

The opaque Open Core client cursor and the Managed numeric recovery cursor are
different values. `managed_sync_state` stores both. The stdlib HTTP client can
recover an accepted POST whose response was lost:

```python
from runtime.managed_sync import ManagedSyncHttpClient

client = ManagedSyncHttpClient(managed_url, installation_id, access_token)
client.recover(queue, envelope.stream)
```

Recovery reads `/sync/status`, pulls from the local `server_cursor`, validates
every returned event shape and checksum, acknowledges matching local queue
rows, and advances only the numeric recovery cursor. Unknown events are
retained in the pull result for a higher-level policy; they are never silently
fabricated into the local queue.

The access token is supplied by the caller and is never written by this module.
Free mode does not instantiate the queue or the HTTP client.