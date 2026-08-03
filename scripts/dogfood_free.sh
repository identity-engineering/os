#!/usr/bin/env bash

set -euo pipefail

IE_BIN="${IE_BIN:-ie}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
sandbox="$(mktemp -d "${TMPDIR:-/tmp}/ie-free-dogfood.XXXXXX")"
root="$sandbox/ie"
config="$sandbox/config"
workdir="$sandbox/workdir"
payload="$sandbox/signal.json"

trap 'rm -rf "$sandbox"' EXIT
mkdir -p "$sandbox/home" "$workdir"

run_ie() {
  (
    cd "$workdir"
    HOME="$sandbox/home" \
      XDG_CONFIG_HOME="$config" \
      IE_ROOT="" \
      "$IE_BIN" "$@"
  )
}

printf '%s\n' "Free dogfood using $IE_BIN"
printf 'version: %s\n' "$(run_ie --version)"

run_ie init \
  --path "$root" \
  --account no_account \
  --name "Free Dogfood" \
  --handle free-dogfood \
  --yes >/dev/null

test -f "$root/HEADER.yaml"
test -f "$root/STEM.yaml"
test -f "$root/dimension-catalogue.yaml"
test -d "$root/registry/_foreign_estimates"
test -d "$root/registry/_inbound_requests"

status_before="$(run_ie status)"
grep -F "handle:     free-dogfood" <<<"$status_before" >/dev/null
grep -F "foreign estimates: 0 sender(s)" <<<"$status_before" >/dev/null
run_ie catalogue >/dev/null
run_ie registry list | grep -F "(empty registry)" >/dev/null
run_ie mass --json > "$sandbox/mass-empty.json"
run_ie reindex >/dev/null

"$PYTHON_BIN" - "$sandbox/mass-empty.json" <<'PY'
import json
import sys

mass = json.load(open(sys.argv[1]))
assert mass["emergent_self_mass"] is None, mass
assert mass["volume_count"] == 0, mass
assert mass["estimator_count"] == 0, mass
PY

printf '%s\n' '{"from":"alice","to":"free-dogfood","timestamp":"2026-08-03T06:00:00+00:00","existence":true,"interaction_depth_delta":0.4,"sender_emergent_mass":70,"coarse_mass_estimate":55,"mass_confidence":0.8}' > "$payload"

run_ie signal apply --payload "$payload" > "$sandbox/partial.json"
"$PYTHON_BIN" - "$sandbox/partial.json" <<'PY'
import json
import sys

receipt = json.load(open(sys.argv[1]))
assert receipt["status"] == "partial", receipt
assert "coarse_mass_estimate" in {item["field"] for item in receipt["rejected_fields"]}, receipt
assert "geometry_receipt=" in receipt["reason"], receipt
PY

run_ie mass --json > "$sandbox/mass-partial.json"
"$PYTHON_BIN" - "$sandbox/mass-partial.json" <<'PY'
import json
import sys

mass = json.load(open(sys.argv[1]))
assert mass["emergent_self_mass"] is None, mass
assert mass["volume_count"] == 1, mass
assert mass["estimator_count"] == 0, mass
PY

run_ie signal apply --payload "$payload" --open-consent > "$sandbox/applied.json"
"$PYTHON_BIN" - "$sandbox/applied.json" <<'PY'
import json
import sys

receipt = json.load(open(sys.argv[1]))
assert receipt["status"] == "applied", receipt
assert "coarse_mass_estimate" in receipt["applied_fields"], receipt
assert "geometry_receipt=" in receipt["reason"], receipt
PY

run_ie mass --json > "$sandbox/mass-applied.json"
"$PYTHON_BIN" - "$sandbox/mass-applied.json" "$root/registry/_geometry_receipts" <<'PY'
import json
import sys
from pathlib import Path

mass = json.load(open(sys.argv[1]))
assert abs(mass["emergent_self_mass"] - 55.0) < 0.001, mass
assert mass["volume_count"] == 1, mass
assert mass["estimator_count"] == 1, mass
assert len(list(Path(sys.argv[2]).glob("*.yaml"))) == 2
PY

request_json="$(run_ie request create --from alice --scope coarse_mass_estimate,mass_confidence --note "free dogfood")"
request_id="$(printf '%s' "$request_json" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["request_id"])')"
run_ie request list --status pending | grep -F "$request_id" >/dev/null
run_ie request show "$request_id" >/dev/null
run_ie request ignore "$request_id" >/dev/null

request_json_2="$(run_ie request create --from bob --scope coarse_mass_estimate)"
request_id_2="$(printf '%s' "$request_json_2" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["request_id"])')"
run_ie request quarantine "$request_id_2" >/dev/null
run_ie request list --status ignored | grep -F "$request_id" >/dev/null
run_ie request list --status quarantined | grep -F "$request_id_2" >/dev/null

if run_ie registry get alice >/dev/null 2>&1; then
  echo "registry get unexpectedly succeeded" >&2
  exit 1
fi
if run_ie signal apply --payload "$payload" --to someone-else >/dev/null 2>&1; then
  echo "signal mismatch unexpectedly succeeded" >&2
  exit 1
fi
if run_ie request list --status invalid-status >/dev/null 2>&1; then
  echo "invalid request status unexpectedly succeeded" >&2
  exit 1
fi

printf '%s\n' "Free dogfood: PASS"