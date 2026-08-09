# SQLite-first V1 Schema

Status: design contract for the first DB-only local runtime.

This document is the storage contract for a fresh local installation. It is
intentionally more precise than the v0 YAML schemas because the database is the
canonical source of mutable state in V1.

## Decisions

- The canonical database is `.ie/ie.sqlite3` below the install root.
- UUID strings are used for entities and events. SQLite integer rowids are not
  part of the public contract.
- Timestamps are normalized UTC RFC3339 text values.
- Booleans use SQLite integers (`0` or `1`).
- JSON columns contain canonical UTF-8 JSON with stable key ordering. JSON is
  used for open-ended geometry and content; it is not used to hide fields that
  are queried or constrained regularly.
- SHA-256 values are lowercase hexadecimal strings.
- Foreign keys, WAL mode, a busy timeout, and integrity checks are enabled for
  every database connection.
- Current tables are projections for fast operation. Event and revision tables
  preserve the local history needed to explain and rebuild those projections.
  Revision tables do not cascade from current projection rows: repairing or
  deleting a projection must never delete the history needed to rebuild it.
- No canonical mutable state is stored in YAML. YAML contract files in the
  repository are documentation only and are not read by the local runtime.

## Identity-space export

The runtime can export one local identity space with `ie db export`. The
format is `identity-engineering.identity-space` version `1` and contains the
installation and identity metadata, all current projections, and the
append-only event, revision, and evidence tables needed for a later rebuild.

The envelope has a `payload`, `payload_sha256`, and `export_id`. Both checksum
values are the lowercase SHA-256 of the payload's canonical UTF-8 JSON. The
payload uses sorted object keys and compact separators; integral numeric values
are normalized so Python and Managed Node consumers hash the same document.
Pretty-printing the outer JSON file does not change the checksum.

The export intentionally does not contain a computed `emergent_self_mass`.
The `foreign_estimates` inputs and their published `sender_emergent_mass`
values are preserved, because the receiving runtime can recompute Self-Mass
from the foreign-estimate zone. The export is checksummed, not encrypted or
key-signed; transport authentication and future signing-key management belong
to the Managed boundary.

## Semantic boundaries

There are three different kinds of state:

1. **Field observation**: what other Identities have sent about the observer.
   This is the input to emergent Self-Mass.
2. **Owned learning state**: what the observer has integrated into its Stem,
   Workspace, Trajectory, Metric Stem, and Registry.
3. **Audit evidence**: what happened, what was accepted, and which source
   supported a learning step.

Mature changes owned learning state. It never writes a self-declared or
Mature-derived value into emergent Self-Mass. Emergent Self-Mass remains a
derived readout from `foreign_estimates`, and is published only when the owner
later emits a signal or serves its public card.

## Account vs Identity (product model)

Product direction: **Account ≠ Identity**. An IE Account may contain many
Identities across substrates. See `docs/account-identity-model.md`.

SQLite-first **V1** still ships **one local Identity per installation** (table
`identity`, unique on `install_id`). That is a deliberate Free starting shape,
not a claim that Identity equals Account. Schema evolution toward multiple
local Identities per install, and managed multi-Identity under one account,
must reuse the same Identity meaning and must record `actor_identity_id` on
mutations. V1 does not need N local Identities before the product model is
locked.

## Table groups

### Installation and local identity

#### `schema_migrations`

One row per applied migration.

| Column | Meaning |
|---|---|
| `version` | Integer primary key, internal migration order |
| `name` | Stable migration name |
| `checksum` | SHA-256 of the migration definition |
| `applied_at` | UTC timestamp |

#### `install`

One row for the database installation.

| Column | Meaning |
|---|---|
| `install_id` | UUID primary key |
| `created_at` | Installation creation time |
| `updated_at` | Last metadata update |
| `account_mode` | `no_account`, `login`, or `create_account` |
| `account_id` | Nullable managed-account reference |
| `tier` | Local tier marker, normally `free` in V1 |
| `app_version` | Runtime version that last wrote metadata |

#### `identity`

One local owner identity per installation in V1. The handle is the operational
address; the UUID prevents a handle rename from changing event ownership.

| Column | Meaning |
|---|---|
| `identity_id` | UUID primary key |
| `install_id` | Unique foreign key to `install` |
| `local_handle` | Unique handle used at the surface boundary |
| `preferred_name` | Optional display name |
| `substrate` | `human`, `runtime`, `idea`, `org`, `collective`, or `other` |
| `accepts_ie_signals` | Whether the local surface accepts signals |
| `created_at`, `updated_at` | Lifecycle timestamps |
| `last_signal_at` | Nullable last accepted or observed signal time |
| `last_mature_at` | Nullable timestamp of the latest committed local Mature step; public freshness metadata |
| `creator_identity_id` | Nullable factual lineage (null for V1 genesis / bootstrap). See `docs/identity-creation-jurisdiction.md` |

### Jurisdiction grants (creation package + residual)

#### `identity_grants`

Current and historical jurisdiction grants over an Identity. Issued at creation
as the default package; ordinary scopes are transferable and Child-revocable;
`residual_emergency` is the narrow audited red-button lever.

| Column | Meaning |
|---|---|
| `grant_id` | UUID primary key |
| `actor_identity_id` | Grantee (who may exercise the scope) |
| `object_identity_id` | The Identity whose policy / surface / visibility is affected |
| `scope` | `policy_admin` \| `visibility_control` \| `surface_admin` \| `grant_admin` \| `residual_emergency` |
| `residual` | 1 for the residual emergency lever |
| `transferable` | 1 if ordinary transfer is allowed |
| `space_id` | Optional membrane scope (later) |
| `granted_at` / `revoked_at` | Lifecycle |
| `granted_by_identity_id` | Who issued the grant |
| `note` | Audit note |

On `ie init` the runtime issues the full default package to the new Identity
(self for V1 genesis). Multi-Identity creation will issue the package to the
creator as actor over the new object Identity. Full semantics:
`docs/identity-creation-jurisdiction.md`. Operational probes and transfer/revoke
CLI remain under issue #40.

### Policy and privacy

#### `privacy_defaults`

One current row per local identity. It contains the defaults from the signal
contract, including the distinction between public sender geometry and
consent-gated estimates about the observer.

The table has one boolean column per stable policy field, such as
`share_existence`, `share_interaction_depth_delta`,
`share_sender_emergent_mass`, `share_coarse_mass_estimate`,
`share_dimensions_delta`, `share_relation_pull`, and `share_rich_signals`.

#### `consent_grants`

Current consent grants, keyed by `(identity_id, sender_handle, field_name)`.
Each row has `granted_at`, nullable `revoked_at`, `source`, and an optional
`note`. A revoked grant remains as history instead of being deleted.

#### `quarantines`

Current and historical sender quarantines, keyed by
`(identity_id, sender_handle)`. Each row has `active`, `reason`, `created_at`,
`revoked_at`, and `source`. Quarantine excludes a sender from aggregation but
does not delete events or receipts.

#### `policy_events`

Append-only audit of policy changes and explicit overrides. It stores the
event type, subject handle, field, previous value, new value, actor, reason,
and a canonical `details_json` object. The `--open-consent` CLI option is an
explicit runtime override and is never silently persisted as a permanent
grant.

### Registry and Metric Stem

#### `registry_entries`

The observer's current alloy for each known peer. External peers are addressed
by the handle known in this Registry; V1 does not require a global peer UUID.

| Column | Meaning |
|---|---|
| `entry_id` | UUID primary key |
| `identity_id` | Local observer foreign key |
| `peer_handle` | Unique per observer |
| `preferred_name`, `substrate` | Known peer metadata |
| `description` | Observer-owned perception |
| `first_noticed`, `last_interaction` | Relation lifecycle |
| `interaction_count`, `interaction_depth` | Local interaction projection |
| `my_mass_estimate`, `mass_confidence` | Observer's estimate of the peer |
| `estimate_updated_at` | When the observer last changed its estimate of this peer |
| `estimate_as_of_peer_mature_at` | Peer Mature timestamp known when that estimate was made |
| `peer_last_mature_at` | Latest public Mature timestamp declared by the peer |
| `peer_last_mature_seen_at` | When this observer last saw that public timestamp |
| `recognition_json` | Re-identification information |
| `relation_json` | Pull, resonance, distance, asymmetry, and related data |
| `effect_on_me_json` | Observer-owned effect description |
| `perceived_ownership_json` | Observer's ownership/jurisdiction perception |
| `privacy_json`, `tags_json`, `notes`, `source` | Additional owned metadata |
| `revision`, `created_at`, `updated_at` | Projection versioning |

Mature may update this projection and its dimension assessments. A signal may
update interaction continuity, but it may not silently replace an owned
estimate unless the policy for that operation explicitly allows it.

#### `registry_entry_revisions`

Append-only snapshots of `registry_entries`. Each row stores the entry revision,
the change actor (`mature`, `signal`, `cli`, or `agent`), an optional
`mature_id` or `event_id`, and canonical `snapshot_json`.

#### `metric_dimensions`

The observer's active dimension catalogue and Metric Stem basis. A row contains
`dimension_id`, `identity_id`, `name`, `weight`, `active`, `discovered_via`,
`first_seen`, `note`, `revision`, and timestamps. Dimension names are open and
contentful; they are not a closed framework ontology.

#### `metric_pairs`

Sparse non-orthogonal relationships between two Metric Stem dimensions. The
ordered pair `(dim_a_id, dim_b_id)` is canonicalized so that each relationship
has one row. Columns include `g`, `confidence`, `source`, `note`, `revision`,
and timestamps. Missing pairs mean the default orthogonal relationship.

#### `registry_dimension_values`

Current per-peer alloy components, keyed by `(entry_id, dimension_id)`. It
stores `value`, `confidence`, `source`, `note`, `observed_at`, and `revision`.
Mature can introduce a dimension, assess it for a peer, or deliberately leave
it only in the catalogue.

#### `registry_dimension_revisions`

Append-only history for dimension values. It stores the previous/current value
shape as canonical JSON, the change actor, the related event, and the timestamp.

### Interaction, projection, and receipts

#### `interaction_events`

Append-only record for each structurally valid received Interaction Signal,
including policy-rejected signals. It stores:

- `event_id`, `install_id`, sender and target handles;
- signal timestamp, receive timestamp, schema version, and transport;
- `canonical_payload_json`, containing only validated contract fields;
- `payload_sha256`; and
- optional `in_reply_to_request_id`; and
- optional public `sender_last_mature_at`.

The raw HTTP, CLI, or tool body is not stored. Malformed transport input is
rejected before it becomes an Interaction Event.

#### `apply_receipts`

Append-only result of applying an Interaction Event. It stores `receipt_id`,
status (`accepted`, `applied`, `partial`, or `rejected`), applied fields,
rejected fields with reasons, quarantine state, reason text, and timestamp.
The receipt points to its event and is the stable reference used by geometry
and later Mature evidence.

#### `foreign_estimates`

Current projection keyed by `(identity_id, sender_handle)`. It contains the v0
foreign-estimate fields: first/last signal, signal count, accumulated depth,
existence, latest coarse estimate and confidence, dimensions delta, relation
pull, last published sender emergent Mass, last published sender Mature time,
quarantine, and last receipt.

This table is the sole input projection for the emergent Self-Mass formula.
The formula is not stored as an owned number. `ie mass` recomputes it from this
projection and can include the contributing rows in JSON output.

#### `geometry_receipts`

Append-only local geometry interpretations. It stores the receipt identity,
mode (`interact` or `mature`), observer, target, source apply receipt or Mature
event, and the structured geometry JSON: mass proxy, tension components,
degrees of freedom, jurisdiction observation, stem differential, ownership
move, optionality delta, and notes.

Geometry extraction remains best-effort for Interact. A failed extractor is
recorded in the receipt and does not roll back a valid signal apply.

#### `geometry_receipt_sources`

Many-to-many links from a geometry receipt to source objects. A source can be
an interaction event, apply receipt, Mature event, workspace item, trajectory
entry, registry revision, or external evidence record.

### Requests and evidence

#### `estimate_requests`

Requests are local records and never auto-answer. V1 supports both directions:

- `inbound`: a peer asks this Identity for an estimate;
- `outbound`: this Identity explicitly asks a peer for a fresh estimate.

The row stores requester, target, status, requested fields, note, transport,
timestamps, quarantine, `reply_receipt_id`, and an optional `mature_id` that
created an outbound reassessment request.

Mature can update Registry estimates and create bounded outbound reassessment
requests in the same learning step. The peer's `last_mature_at` is public
freshness metadata on its card and signal, so a receiver can identify stale
estimates without receiving the private Mature content. Automatic request
creation remains a bounded operational setting, not a hidden side effect.

#### `evidence_sources`

Evidence references used by Mature. Internal database sources use a typed
`source_kind` and `source_id`. External files store a root-relative path,
file size, modification observation, SHA-256, and optional captured snapshot.

The default is reference plus hash. A snapshot is captured only when requested
by the owner or when the source is small and the command explicitly enables
it. The database never claims that a path alone is immutable evidence.

### Owned learning state

#### `stem_state`

The current owned Stem projection, one row per local identity. Stable fields
include state differential, vision gradient, coherence, and an open
`substance_json` object for the qualitative local learning state. It also stores
the current revision and the last Mature event.

There is deliberately no `owned_mass` number. Mature changes the substance
that may later become legible through interaction; it does not create a second
self-rating.

#### `stem_revisions`

Append-only Stem snapshots. A revision stores the previous revision, the source
Mature event, and the complete canonical snapshot. The current `stem_state` can
therefore be inspected quickly while the learning path remains explainable.

#### `workspace_items`

Current structured local Workspace items. Supported V1 kinds are `observation`,
`hypothesis`, `decision`, `commitment`, `question`, `goal`, and `note`.
Items have a UUID, title, content, status, priority, optional due time, tags,
source reference, and timestamps. Text is stored in SQLite as owned local
content; project files remain external evidence unless explicitly captured.

#### `workspace_item_revisions`

Append-only item versions with operation (`create`, `update`, `complete`, or
`archive`), canonical snapshot, actor, related Mature event, and timestamp.

#### `mature_events`

The append-only transaction record for a directed learning step. It stores:

- the operator/agent, notes, and canonical requested change set;
- source and evidence links;
- before/after Stem, Registry, and Workspace revision markers;
- counts and hashes of changed projections;
- the linked Mature geometry receipt; and
- optional reassessment-request details.

One committed Mature event is the unit of explanation: it says what was
learned, which state changed, and which evidence justified the change.

#### `trajectory_entries`

Append-only chronological learning records. Each entry links to a Mature event
or an interaction geometry receipt and summarizes the transition from prior
state to current state. It references the relevant Stem, Registry, and
Workspace revisions instead of duplicating their full content.

## Transaction rules

### Optional Managed sync transaction

When a Managed adapter is enabled, the queue tables add durable transport
state without changing local Free semantics:

- `managed_sync_queue` stores the canonical envelope, retry status, attempts,
  and the opaque client cursor;
- `managed_sync_leases` prevents two drainers from sending the same row at the
  same time and expires after a bounded interval; and
- `managed_sync_state` stores the client cursor and the independent numeric
  Managed recovery cursor per stream.

The queue is not part of identity export/import and does not contain Mature
state. Accepted server responses update the queue and stream state in one local
transaction; a lost response is repaired through the Managed pull contract.

### Interaction transaction

For a structurally valid signal, one SQLite transaction writes:

1. `interaction_events`;
2. policy decision and `apply_receipts`;
3. the `foreign_estimates` projection when fields are accepted;
4. request status update when the signal answers a request; and
5. the `geometry_receipts` row and source links.

The geometry hook is best-effort. If it fails, the signal projection and apply
receipt still commit, and the receipt reason records the failure marker.

### Mature transaction

One Mature command writes atomically:

1. validated `evidence_sources` and source links;
2. a `mature_events` row;
3. the current `stem_state` and `stem_revisions`;
4. Registry entries, dimension values, and their revision rows;
5. Workspace items and item revisions;
6. a `trajectory_entries` row;
7. the Mature `geometry_receipts` row; and
8. explicit or configured outbound reassessment requests.

If any requested change is invalid, none of these current projections is
partially updated. The event is either committed as a complete learning step or
not committed.

## Rebuild and deletion rules

- Current projections may be rebuilt from append-only events and snapshots.
- Audit events and receipts are append-only; correction is represented by a
  later event, never by rewriting history.
- Quarantine and revoked consent exclude data from current calculations without
  deleting the underlying audit trail.
- `ie db backup` copies the SQLite database using SQLite's backup API.
- `ie db rebuild-projections --yes` restores current Foreign Estimate, Stem,
  Registry, and Workspace projections from canonical events and revision
  snapshots. It does not rewrite append-only audit or policy history; create a
  backup first.
- A local reset is explicit and destructive. `--force` alone must never delete
  an existing database; reset requires a separate confirmation/flag.
