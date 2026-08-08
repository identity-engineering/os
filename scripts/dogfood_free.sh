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

test -f "$root/.ie/ie.sqlite3"
test -f "$root/README.md"
test -f "$root/IE.md"
test ! -e "$root/HEADER.yaml"
test ! -d "$root/registry"

status_before="$(run_ie status)"
grep -F "handle:    free-dogfood" <<<"$status_before" >/dev/null
grep -F "foreign estimates: 0 sender(s)" <<<"$status_before" >/dev/null
run_ie db info --path "$root" >/dev/null
run_ie db integrity-check --path "$root" >/dev/null
run_ie registry list | grep -F "(empty registry)" >/dev/null
run_ie mass --json > "$sandbox/mass-empty.json"

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

run_ie policy grant --path "$root" --from alice --field coarse_mass_estimate >/dev/null
run_ie policy grant --path "$root" --from alice --field mass_confidence >/dev/null
run_ie signal apply --payload "$payload" > "$sandbox/applied.json"
"$PYTHON_BIN" - "$sandbox/applied.json" <<'PY'
import json
import sys

receipt = json.load(open(sys.argv[1]))
assert receipt["status"] == "applied", receipt
assert "coarse_mass_estimate" in receipt["applied_fields"], receipt
assert "geometry_receipt=" in receipt["reason"], receipt
PY

run_ie mass --json > "$sandbox/mass-applied.json"
"$PYTHON_BIN" - "$sandbox/mass-applied.json" "$root/.ie/ie.sqlite3" <<'PY'
import json
import sqlite3
import sys

mass = json.load(open(sys.argv[1]))
assert abs(mass["emergent_self_mass"] - 55.0) < 0.001, mass
assert mass["volume_count"] == 1, mass
assert mass["estimator_count"] == 1, mass
connection = sqlite3.connect(sys.argv[2])
assert connection.execute("SELECT COUNT(*) FROM geometry_receipts").fetchone()[0] == 2
entry = connection.execute(
    "SELECT interaction_count, peer_last_mature_at FROM registry_entries WHERE peer_handle = 'alice'"
).fetchone()
assert entry == (2, None), entry
connection.close()
PY

run_ie policy show --path "$root" > "$sandbox/policy.json"
"$PYTHON_BIN" - "$sandbox/policy.json" <<'PY'
import json
import sys

policy = json.load(open(sys.argv[1]))
assert len(policy["grants"]) == 2, policy
assert policy["quarantines"] == [], policy
PY

mkdir -p "$root/evidence"
printf '%s\n' 'The owner integrated the first causal probe.' > "$root/evidence/first-step.txt"
printf '%s\n' '{"substance":{"current_focus":"pre-beta probe"},"workspace_changes":[{"kind":"commitment","title":"Run next probe","content":"Verify the next boundary."}],"registry_changes":[{"peer_handle":"alice","my_mass_estimate":55,"mass_confidence":0.8}],"reassessment_targets":["alice"]}' > "$sandbox/mature.json"
run_ie mature \
  --path "$root" \
  --source evidence/first-step.txt \
  --notes "integrated first pre-beta probe" \
  --changes "$sandbox/mature.json" > "$sandbox/mature-result.json"
"$PYTHON_BIN" - "$sandbox/mature-result.json" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1]))
assert result["source_ids"], result
assert result["workspace_change_count"] == 1, result
assert result["registry_change_count"] == 1, result
assert len(result["reassessment_request_ids"]) == 1, result
assert result["last_mature_at"], result
PY

run_ie db backup --path "$root" --to "$sandbox/backup.sqlite3" >/dev/null
test -s "$sandbox/backup.sqlite3"
run_ie db integrity-check --path "$root" >/dev/null

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

if ! run_ie registry get alice >/dev/null 2>&1; then
  echo "registry get unexpectedly failed" >&2
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