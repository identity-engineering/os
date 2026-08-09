# Local Operations V1

This is the user-facing operating model for a DB-only Identity Engineering OS
installation. It describes what changes, what remains derived, and where a
failure can be recovered.

## What `ie init` creates

A fresh install contains:

```text
<install-root>/
  .ie/
    ie.sqlite3
  README.md
  IE.md
```

`README.md` and `IE.md` are orientation and agent-discovery documents. They are
not mutable Identity state. All state that can change during operation lives in
`.ie/ie.sqlite3`.

The initializer creates the install UUID, local Identity UUID, handle, privacy
defaults, empty policy tables, the initial Stem projection, and the seeded
Metric Stem. It enables SQLite foreign keys and WAL mode and applies all
migrations before the install is remembered as active.

The install directory and database receive restrictive local permissions. A
fresh initialization never copies `HEADER.yaml`, `STEM.yaml`, a registry YAML,
or any other canonical state YAML.

## Everyday user flow

### 1. Inspect

```text
ie status
ie db info
ie registry list
ie mass --detail
```

These commands read the same database that the runtime and HTTP surface use.
`--json` is available on machine-facing commands. `ie mass` is a live derived
readout, not a value that was written into the Identity as a self-claim.

### 2. Interact

An incoming signal follows this path:

```text
payload -> validate -> canonical event -> policy -> projection -> receipts
```

The local runtime:

1. validates the known Interaction Signal fields;
2. stores the canonical validated event and its hash;
3. evaluates consent, quarantine, and rate limits;
4. updates the sender's Foreign Estimate projection for accepted fields;
5. creates an Apply Receipt with accepted and rejected fields;
6. marks an inbound request answered when `in_reply_to_request_id` is valid;
7. runs the best-effort Geometry Hook; and
8. commits the event, projection, receipts, and links atomically.

The raw transport body is not stored. A malformed body receives an error and
does not become a local Interaction Event. A structurally valid but
policy-rejected signal remains auditable as an event plus a rejected receipt.

The next outbound signal should read the current derived emergent Self-Mass at
send time. Mature does not set that number; new foreign estimates and future
signals can change it. The public card and outbound signal also expose the
timestamp `last_mature_at` of the latest committed local Mature step. This is a
freshness marker only: it reveals that the local form changed, not what was
learned.

### 3. Mature

Mature is the directed local learning step. It is not only a note about a
receipt and it is not an automatic neural-style backpropagation pass.

The owner or an authorized agent supplies:

- one or more sources;
- a causal interpretation of what changed;
- Stem or Vision changes when applicable;
- Workspace changes such as observations, hypotheses, decisions, or
  commitments;
- Registry changes, including updated estimates, dimensions, confidence, and
  relation notes for other Identities; and
- optionally, selected peers that should be asked for a fresh estimate.

The command verifies and records each source. Database sources are linked by
stable IDs. External files are stored as root-relative references with a
SHA-256 hash; a content snapshot is optional and explicit.

Then one transaction commits the Mature event, Geometry Receipt, Trajectory
entry, updated Stem, updated Workspace, Registry revisions, and any explicit
reassessment requests. A failed validation leaves all current state unchanged.

Mature therefore changes local substance immediately. It does not publish a
new Self-Mass as a self-assessment. On the next interaction, the public signal
can carry the current emergent Self-Mass calculated from the field of estimates
other Identities have already supplied, plus `last_mature_at`. A receiver stores
that timestamp beside its Registry entry and can compare it with the Mature
timestamp known when its own estimate was made. A new request can then invite
that peer to re-estimate the Identity from its changed form.

### 4. Respond to requests

Inbound estimate requests are visible in SQLite and remain pending until the
owner decides. They are never auto-answered. A reply is a normal Interaction
Signal and may link back to the request.

Outbound reassessment requests are explicit local intents. They may be created
by Mature for selected Registry peers or by a dedicated request command. The
local database records the intent; delivery remains a transport concern.

### 5. Recover and inspect

```text
ie db integrity-check
ie db backup --to <file>
ie db rebuild-projections --yes
ie status --json
```

Integrity checks do not mutate state. Backups use SQLite's online backup API so
the database can be copied while the local surface is running. Restoring is an
explicit operation into a new or empty install path; it never overwrites a
current database implicitly. Run `backup` first before rebuilding. The rebuild
uses Interaction Events and Receipts plus Stem, Registry, and Workspace
revision snapshots; append-only audit and policy history stays untouched.

If the optional Managed adapter is enabled, its queue is drained separately.
Network failures remain local `retry` rows, cursor or payload conflicts become
`blocked`, and a lost append response is recovered with the Managed status/pull
contract. The accountless Free path never requires these tables or endpoints.

## Ownership and visibility rules

| Data | Changes through | Visible to others by default |
|---|---|---|
| Foreign Estimates | accepted incoming signals | only through derived public geometry where the protocol permits |
| Emergent Self-Mass | derived from Foreign Estimates | yes, on public card and outbound signal when known |
| `last_mature_at` | latest committed local Mature timestamp | yes, on public card and outbound signal |
| Stem and Workspace | Mature | no, local by default |
| Registry estimates of peers | Mature and explicit local operations | no, local by default |
| Geometry Receipts | Interact/Mature hooks | no, local by default |
| Estimate requests | owner, Mature, or request command | only when sent through a transport |
| Consent and quarantine | owner/policy operations | no, local by default |

The separation is intentional: local learning can happen before it becomes
observable, while the next interaction can expose its consequences without
turning an owned self-assessment into a public Mass claim.

## Reset semantics

The active pre-beta installation can be replaced only through an explicit local
reset. The reset process must:

1. show the exact install root and database path;
2. require a separate destructive confirmation;
3. make clear that V1 does not migrate legacy YAML state;
4. remove or archive that install's `.ie/ie.sqlite3` and known legacy state only;
5. run the normal DB-only initializer from an empty path.

Back up or manually export a legacy install before reset. The reset command is
not a migration tool.

`--force` means "allow initialization at a prepared target"; it does not by
itself authorize deleting an existing database.