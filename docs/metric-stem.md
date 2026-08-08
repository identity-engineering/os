# Dimension Catalogue / Metric Stem

Locked 27.07.2026

## Purpose

The Metric Stem is the observer's current definition of the basis and the geometry of the classification space.

It answers:
- Which dimensions do I currently treat as relevant?
- How strongly does each dimension count (weight)?
- What are the angles / dependencies between dimensions in my frame?

It does **not** store the alloys of individual Identities (those live in the Registry). It only defines the metric with which those alloys are read.

## Non-orthogonal dimensions

In ordinary Euclidean space basis vectors are orthogonal (90°). In the experienced Identity space they need not be.

We therefore keep a (sparse) metric on the dimension space itself:

\[
g_{ij} = \langle e_i, e_j \rangle
\]

- Diagonal terms relate to scaling / weight.
- Off-diagonal terms encode angles or correlations between dimensions.

Analogies that justify this from the start:
- Oblique coordinate systems
- Riemannian metric tensor
- Mahalanobis distance (covariance as metric)
- Non-orthogonal lattice vectors in crystals
- Information geometry (Fisher metric)

Default when no entry exists: dimensions are treated as orthogonal. Non-orthogonal relationships are added only when the observer judges them relevant (ownership-managed, with confidence).

Full per-dimension dependency tensors (a tensor for every dimension) stay out of scope for v0. The sparse pairwise metric is sufficient and keeps the system asymptotic and legible.

## Relation to Registry and living Tensor

- Registry entry = alloy of one Identity (open dimensions[] with value + confidence)
- Metric Stem = which dimensions matter and how they stand to each other
- Distance and tension = live computation using alloys + this metric
- Curvature (later) = derived from the distribution of mass-densities under this metric

## File / table

- Schema: `schemas/dimension-catalogue/v0.yaml`
- Personal template: `templates/personal/dimension-catalogue.yaml`
- Canonical V1 state: `metric_dimensions` and `metric_pairs` in `.ie/ie.sqlite3`
- New dimensions are discovered through source-backed `ie mature` changes; the
	initial install seeds only `ownership_depth` and `clarity_of_vision`.
