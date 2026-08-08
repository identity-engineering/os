# Living Tensor (derived from Registry + Metric Stem)

There is no separate persistent full Tensor state file.

The high-dimensional, open, contentful dimensional space that lives inside each Registry entry, read through the observer's Metric Stem, *is* the Tensor.

## Core statements (locked 27.07.2026)

1. All numbers, dimensions and distances reside in the Registry (alloys) + Metric Stem (basis + g_ij).
2. Tension is always dependent on the whole set of registered Identities → it is dynamic and emergent.
3. The list of dimensions is not static. It is Identity-specific and extensible.
4. When a new dimension is discovered for one Identity, the observer can (ownership-controlled) analyse whether it is also relevant for other already known Identities and whether it should enter the Metric Stem.
5. Dimensions are not the abstract framework primitives (Mass, Vision, …). They are richer, contentful vector spaces that describe the actual substance, character and worldly classification of an Identity — the material science of Mass.
6. Basis vectors need not be orthogonal. The Metric Stem holds a sparse g_ij (angles / correlations) from the start.
7. Distance estimation on every dimension always carries its own confidence; the metric itself also carries confidence per pair.
8. This structure gives the Identity a clear, expandable world-view. New Identities can introduce new dimensions that open new perspectives on existing ones. Questions as Probes become the instruments that measure and deliberately extend this experienced curved space.

## Geometry of the space (locked 27.07.2026)

- The Possibility Space on the Identity level is **not 3-dimensional**. It is the infinite-dimensional space whose basis is the open, growing set of all discovered dimensions (the distinct sum across the entire Registry), filtered and weighted by the Metric Stem.
- Each Identity is an **alloy**: a vector (or distribution) over that basis. The degree of expression on each dimension is the corresponding potential mass component along that axis.
- **Mass** is the (relative, confidence- and interaction-depth-weighted) **density of this alloy**. This stays consistent with the framework definition of Mass as density / substance depth, not volume.
- **Volume** candidate: the number (or weighted count) of interacting Identities that estimate / orbit me.
- Self-Mass is never self-declared. It emerges from the Mass estimates that the surrounding Identities return about me, weighted by their own Mass and by interaction depth.
- Non-orthogonal relationships between dimensions are first-class via the Metric Stem (g_ij).
- Full per-dimension dependency tensors remain out of scope for v0.

## How the Tensor is updated (01.08.2026 · clarified 02.08.2026)

The **intended** primary update path is the **Geometry Receipt** produced by the Probe process after every Interaction (Think / Interact / Mature). See `docs/probes-as-bridge.md` and `schemas/geometry-receipt/v0.yaml`.

- Geometry Receipts are local by default and **written today** into the
	`geometry_receipts` table in `.ie/ie.sqlite3`.
- Interact updates Registry continuity separately and explicitly. Mature may
	commit supplied Registry and Metric Stem changes; no Geometry Receipt causes
	an inferred rewrite. Continuous derived Tension/Tensor feed remains the open
	work on **OS #8**.
- Receipts never write self-declared Mass; Self-Mass continues to emerge only from foreign estimates.

## Storage implication

See `docs/storage-tiers.md`. Free = local SQLite. Personal Pro = managed SQL.
Skills are storage-agnostic.

## Implications

- Registry = primary store of alloys
- Metric Stem = observer's current basis + metric
- Tensor = geometric reading of alloys under that metric (live)
- Tension = aggregation over the Registry (live)
- Curvature = later derived quantity
- Geometry Receipt = the continuous Probe bridge that keeps the Tensor alive
