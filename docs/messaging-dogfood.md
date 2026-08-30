# Messaging product dogfood

Status: **External Dogfood owned by Jonas; local test evidence is separate**

For this product, Dogfood means Jonas using the current code on `main` through
the Grok MCP connector. That is the only real Dogfood path currently in use.
CLI calls, local MCP calls, source overrides, worktree runs, automated scripts,
and assistant-run flows are testing only and never count as Dogfood evidence.

The productive surface is therefore outside this repository. This document
records the boundary and keeps local test evidence from being mistaken for
real-world product use.

## B4 boundary

Any workday requirement applies only to genuine Grok MCP use against `main`.
There is no requirement to keep this chat open for seven days, and local
assistant-run actions cannot satisfy it. D1, D2, and E are not blocked by local
test evidence; any release claim that requires sustained real-world Dogfood
must still wait for the corresponding Grok MCP evidence.

## Local test record

The following records were created by assistant-run local testing on
2026-08-30. They are retained for traceability but count as **zero** genuine
Dogfood workdays.

Paths are relative to the local test install root unless noted otherwise.

| Workday | Delivered at (UTC) | Message ID | Delivery receipt | Receiver state | Metabolization | Trajectory |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-08-30 | 05:03:48Z | `0198f3a3-7c9e-7d01-8a2b-0000000000cb` | `01a0510d-67fd-756a-bf47-b2aa93442d39` | `inbox -> metabolized` | `01a0510d-6cb5-7662-bfb1-8fd0920b086b`; `metabolized` | `trajectory/messaging/0198f3a3-7c9e-7d01-8a2b-0000000000cb.json` |
| 2026-08-30 | 06:12:38Z | `01a0514c-6eaa-76ea-ab6a-a2127cdf27ab` | `01a0514c-6eac-75f6-b476-db4c765e817b` | `inbox -> metabolized` | `01a0514c-965b-75f6-90f0-ab3dc6c656f2`; `metabolized` | `trajectory/messaging/01a0514c-6eaa-76ea-ab6a-a2127cdf27ab.json` |

The two rows are deliberately recorded under the same test date. Neither row
is evidence of Jonas's Grok MCP Dogfood.

## Recording genuine Dogfood

1. Use the Grok MCP connector against the version currently on `main`.
2. Record only evidence produced by that real use, including the relevant
   message result and any receiver state that is observable through MCP.
3. Keep local CLI, local MCP, source-override, fixture, and assistant-run
   artifacts in the test record, never in the Dogfood count.

This document is an audit aid, not a second Messaging store. The actual
Grok/MCP session and the code on `main` are authoritative for Dogfood.