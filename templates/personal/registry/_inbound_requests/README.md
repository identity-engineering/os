# Inbound estimate requests (local inbox)

This directory holds **pending and historical estimate requests** received by this Identity.

- One file per request: `{request_id}.yaml` (or `.json`)
- Created by `ie request create` / Surface Runtime request path
- Owner may `ie request ignore` or `ie request quarantine` — **never auto-answered**
- A reply is a normal Interaction Signal; optional `in_reply_to_request_id` marks the request answered

See:

- `schemas/estimate-request/v0.yaml`
- `docs/estimate-request.md`
- `docs/bidirectional-gravitational-sensor.md`

Do not hand-edit production records unless you know the invariants.
