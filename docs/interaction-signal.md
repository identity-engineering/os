# Minimal Interaction Signal Contract v0

Locked 27.07.2026

This contract defines the absolute minimum that must be exchangeable at the end of an interaction so that:

- Registry entries can be updated
- Relative Mass can emerge (self-Mass is never self-declared)
- Dimensional alloys can grow
- Tension can be re-derived
- Privacy and Refusal-of-Control remain structural

## Core separation

There are always two kinds of information:

1. **What I estimate** (stays in my Registry, my frame)
2. **What I receive / pass** (the signal that actually crosses the boundary)

The signal is only the second kind. Everything else remains local unless explicitly consented.

## Always-passed (minimal, no consent required)

These three fields are the structural minimum. They are enough for the other Identity to know that an interaction occurred and to update its own volume / depth counters.

```yaml
signal:
  from: "local_handle_or_session"      # who is sending (observer-side handle or ephemeral session id)
  to: "target_local_handle"            # who is being addressed (as known in sender's Registry)
  timestamp: "2026-07-27T11:58:00Z"
  existence: true                      # "I registered / re-confirmed you"
  interaction_depth_delta: 0.05        # how much this single interaction added (0.0–1.0 scale)
```

Nothing else is required for the system to stay alive.

## Consent-based (optional enrichment)

Only if the sender's privacy settings and the receiver's consent allow it:

```yaml
  # optional block — default off
  coarse_mass_estimate: 62             # sender's current my_mass_estimate of the receiver (0–100)
  mass_confidence: 0.7

  # optional — even more restricted
  dimensions_delta:                    # only dimensions the sender is willing to share
    - name: "ownership_depth"
      value: 0.8
      confidence: 0.65
    # …

  # optional — rare
  relation_pull: 0.4                   # how strongly the sender currently feels pulled
```

Rich dimensional vectors, full alloy descriptions, tension signals and asymmetry estimates are never part of the minimal contract. They require explicit, higher-level consent.

## How the receiver uses the signal

1. **Existence + depth_delta**  
   → update `last_interaction`, `interaction_count`, `interaction_depth` in the corresponding Registry entry (or create a new entry if first contact).

2. **If coarse_mass_estimate is present**  
   → this is one data point that contributes to the *receiver's emergent self-Mass* (weighted by the sender's own Mass and by interaction depth).  
   The receiver never writes this number directly as "my Mass"; it feeds the aggregation that produces self-Mass.

3. **If dimensions_delta is present**  
   → the receiver may (ownership-controlled) incorporate or propose new dimensions into its own world-view and optionally re-evaluate existing entries against them.

4. **Everything else stays local to the sender**  
   The sender updates its own Registry entry for the receiver with whatever it estimated during the interaction. That estimate never has to leave the sender's frame.

## Volume and emergent self-Mass (consequence of the contract)

- Every Identity that sends me at least the minimal signal is counted toward my volume candidate.
- The weighted collection of all `coarse_mass_estimate` values I receive (weighted by the sender's Mass and by accumulated interaction depth) is the primary input to my emergent self-Mass.
- My own estimates of others remain in my Registry and shape *my* picture of the surrounding densities; they are not required to be sent back.

## Privacy defaults (structural)

```yaml
privacy:
  share_existence: true                # always on for the minimal signal
  share_interaction_depth_delta: true  # always on for the minimal signal
  share_coarse_mass_estimate: false    # default off
  share_dimensions_delta: false        # default off
  share_relation_pull: false           # default off
  share_rich_signals: false            # default off
```

Refusal-of-Control is expressed simply: an Identity can refuse to emit anything beyond the minimal three fields, or can refuse the interaction entirely.

## What this deliberately does not include yet

- Exact aggregation formula for emergent self-Mass (weights, decay, cold-start)
- Automatic dimension-propagation rules
- Cryptographic binding of signals to local_handles
- Multi-party / collective signals

Those come after the minimal contract is stable and dogfooded.

## Relation to Header

The Header (still to be defined in detail) is the always-on entry point that an agent reads at the start of an interaction.  
The Signal is what is written at the end.  
Together they turn static Registry files into a living system.
