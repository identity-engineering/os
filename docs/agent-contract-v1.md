# Agent Contract for Local IE V1

This contract describes how CLI users, coding agents, and runtime adapters use
the local database without bypassing Identity Engineering semantics.

## Discovery

An agent should discover an install in this order:

1. explicit `--path`;
2. `IE_ROOT`;
3. the nearest parent containing `.ie/ie.sqlite3`;
4. the remembered active root.

`README.md` and `IE.md` explain the local surface, but they are not authority
for mutable state. The database is authoritative. A legacy `HEADER.yaml` may
be reported as a legacy install, but it is not silently treated as the V1
database.

## Read path

Agents should prefer stable commands and JSON output:

```text
ie status --json
ie registry list --json
ie mass --json
ie request list --json
ie db info --json
```

Every JSON result should identify the relevant schema version and stable IDs.
Agents should use receipt IDs, event IDs, Mature IDs, and revision numbers when
referring to state rather than relying on display text or file paths.

The public card's `emergent_self_mass` and `last_mature_at` are different
signals. The former is a derived field readout from other Identities' estimates;
the latter is only a public freshness timestamp for the local owned learning
state. A Registry should retain both the peer's latest public Mature timestamp
and the peer Mature timestamp that was current when its local estimate was last
updated.

## Write path

Agents do not write SQLite directly and do not edit database files. They use
the CLI, runtime API, HTTP surface, or a future MCP adapter. A write operation
must return a structured result containing:

- status;
- stable ID(s);
- changed fields or revision markers;
- rejected fields and reasons, when applicable; and
- the next recoverable action, when the operation failed.

The runtime owns transaction boundaries. A caller must not emulate a multi-step
write by updating projections in separate commands when the operation has a
single transactional command.

## Interact rules

- Validate the signal contract before transport-specific handling.
- Never use `coarse_mass_estimate` as the sender's own Mass.
- Treat `sender_emergent_mass` as public sender geometry, not as a rating of the
  receiver.
- Do not infer consent from a signal merely because a field is present.
- Do not suppress a partial or rejected receipt; it is part of the audit path.
- Do not retry an accepted event without preserving idempotency or recording a
  new deliberate event.

## Mature rules

Mature is an owned learning operation. An agent may propose a change set, but
the owner or the configured ownership policy decides whether it is committed.

A Mature request should include:

- source references and the intended evidence mode;
- a short causal explanation;
- requested Stem, Workspace, and Registry changes;
- confidence where an estimate or dimension value changes; and
- explicit reassessment targets if peers should be asked for a fresh estimate.

The agent must be able to explain the resulting Mature event by its source IDs,
before/after revisions, and Trajectory entry. It must not:

- write a self-declared emergent Self-Mass;
- silently overwrite an existing Registry estimate without a revision;
- rewrite policy as a side effect of learning;
- claim that an external path is immutable without a hash; or
- turn a local Geometry Receipt into a public payload without consent.

## Privacy and evidence

Canonical Interaction Events contain validated contract fields only. Raw HTTP
bodies, arbitrary tool envelopes, and secrets are not persisted by default.
External evidence uses root-relative paths and SHA-256. Content snapshots are
opt-in and should be avoided for secrets or large files.

Agents should report when a source is missing, changed since hashing, outside
the install root, or unavailable for snapshotting. They should not silently
replace missing evidence with a newly invented summary.

## Failure and recovery

An agent should treat these outcomes differently:

- `rejected`: no domain projection was accepted; inspect the reason;
- `partial`: some fields were accepted and the receipt is authoritative;
- `applied` or `accepted`: use the returned receipt/event IDs for follow-up;
- integrity failure: stop writes and request backup/repair handling.

After a process restart, the agent should query the database by stable ID before
retrying a command. `ie db integrity-check` is the first diagnostic for a
database-level failure.