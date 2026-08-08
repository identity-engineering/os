# Estimate Request + Inbox (SQLite-first V1)

Implementation of the **inbound** half of the bidirectional gravitational sensor
(issue #31). Design lock: `docs/bidirectional-gravitational-sensor.md`.

## What is shipped

| Piece | Location |
|-------|----------|
| Schema | `schemas/estimate-request/v0.yaml` |
| Models | `EstimateRequest`, `RequestStatus` in `runtime/models.py` |
| Store | SQLite table `estimate_requests` in `.ie/ie.sqlite3` |
| Ops | `runtime/request.py` |
| CLI | `ie request create\|list\|show\|ignore\|quarantine` |
| Reply link | optional `in_reply_to_request_id` on Interaction Signal → marks request answered |

## Flow

1. **Requester** wants volume / emergent self-Mass feedback from a peer already
   in (or about to enter) the gravitational field.
2. A **request** record is created and lands in the **target's inbox**
   (`create_inbound_request` / `ie request create`).
3. Target **owner** may:
   - ignore (`ie request ignore`)
   - quarantine (`ie request quarantine`)
   - answer later by emitting a normal Interaction Signal toward the requester,
     optionally with `in_reply_to_request_id` set to this request's id
4. When a reply signal is applied and carries `in_reply_to_request_id`, the
   linked request (if present in this store) is marked `answered` with
   `reply_receipt_id`.

## Policy defaults

- Requests **never** auto-answer.
- Soft limit: max pending requests per requester handle (default 20).
- Mature may create explicit outbound reassessment requests; it does not answer
   inbound requests automatically.
- No request path silently changes Stem, Vision, Metric Stem weights, or policy.
- Quarantine is first-class and symmetric in spirit to signal quarantine.

## CLI examples

```bash
# Land a request in *this* install's inbox (local receive / dogfood)
ie request create --from alice --to me --scope coarse_mass_estimate,mass_confidence

ie request list
ie request list --status pending
ie request show <request_id>
ie request ignore <request_id>
ie request quarantine <request_id>

# Reply is a normal signal (applied on the requester's surface in production).
# Optional linkage field for audit:
#   "in_reply_to_request_id": "<request_id>"
ie signal apply --open-consent --payload reply.json
```

## Explicit non-goals (v0)

- No global social graph
- No forced mutual estimation
- No automatic outbound request on every interaction (hooks are opt-in later)
- No network delivery of requests between separate installs yet (local receive + HTTP binding can follow)
- No managed Pro inbox sync

## Related

- `docs/bidirectional-gravitational-sensor.md`
- `docs/interaction-signal.md`
- `docs/foreign-estimate-zone.md`
- `docs/identity-surface.md`
- Issue #15 Emergent self-Mass aggregation
- Issue #29 Surface Runtime v0
