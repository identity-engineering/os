#!/usr/bin/env bash

set -euo pipefail

IE_BIN="${IE_BIN:-ie}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixtures="$script_dir/tests/fixtures/messaging/v0.1"
sandbox="$(mktemp -d "${TMPDIR:-/tmp}/ie-messaging-dogfood.XXXXXX")"
root="$sandbox/ie"
config="$sandbox/config"
workdir="$sandbox/workdir"

trap 'rm -rf "$sandbox"' EXIT
mkdir -p "$workdir"

run_ie() {
  (
    cd "$workdir"
    HOME="$sandbox/home" \
      XDG_CONFIG_HOME="$config" \
      IE_ROOT="" \
      "$IE_BIN" "$@"
  )
}

printf '%s\n' "Messaging dogfood using $IE_BIN"
printf 'version: %s\n' "$(run_ie --version)"

run_ie init \
  --path "$root" \
  --account no_account \
  --name "Messaging Dogfood" \
  --handle messaging-dogfood \
  --yes >/dev/null

test -f "$root/.ie/ie.sqlite3"

run_ie messaging card register --path "$root" --file "$fixtures/card-jonas.json" \
  > "$sandbox/card-jonas.json"
run_ie messaging card register --path "$root" --file "$fixtures/card-coding-agent.json" \
  > "$sandbox/card-coding-agent.json"
run_ie messaging card list --path "$root" --json > "$sandbox/cards.json"

"$PYTHON_BIN" - "$sandbox/cards.json" <<'PY'
import json
import sys

cards = json.load(open(sys.argv[1], encoding="utf-8"))["cards"]
assert {card["identityId"] for card in cards} == {
    "018f3a2b-7c9e-7d01-8a2b-0000000000a1",
    "018f3a2b-7c9e-7d01-8a2b-0000000000a2",
}, cards
for card in cards:
    assert card["recognitionPolicy"]["default"] == "accept-known", card
PY

if run_ie messaging send --path "$root" --file "$fixtures/envelope-unknown.json" \
  > "$sandbox/rejected.json" 2>&1; then
  echo "unknown sender was unexpectedly accepted" >&2
  exit 1
fi

"$PYTHON_BIN" - "$sandbox/rejected.json" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1], encoding="utf-8"))
assert result["status"] == "rejected", result
assert "recognition" in result["receipt"]["reason"], result
PY

run_ie messaging send --path "$root" --file "$fixtures/envelope-task.json" \
  > "$sandbox/delivered.json"
message_id="$($PYTHON_BIN - "$sandbox/delivered.json" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1], encoding="utf-8"))
assert result["status"] == "delivered", result
assert result["receipt"]["receiptType"] == "delivered", result
print(result["envelope"]["messageId"])
PY
)"

run_ie messaging inbox --path "$root" --json > "$sandbox/inbox.json"
"$PYTHON_BIN" - "$sandbox/inbox.json" "$message_id" <<'PY'
import json
import sys

messages = json.load(open(sys.argv[1], encoding="utf-8"))["messages"]
assert [message["messageId"] for message in messages] == [sys.argv[2]], messages
assert messages[0]["signal"]["type"] == "task", messages
PY

run_ie messaging status --path "$root" --json > "$sandbox/status.json"
"$PYTHON_BIN" - "$sandbox/status.json" <<'PY'
import json
import sys

status = json.load(open(sys.argv[1], encoding="utf-8"))
assert status["cards"]["count"] == 2, status
assert status["inbox"]["count"] == 1, status
assert status["outbox"]["count"] == 2, status
assert status["receipts"]["by_type"] == {"delivered": 1, "rejected": 1}, status
assert status["consent_audit"]["count"] == 0, status
assert status["metabolizations"]["count"] == 0, status
assert len(status["rejections"]) == 1, status
assert "recognition" in status["rejections"][0]["reason"], status
PY

run_ie messaging metabolize "$message_id" \
  --path "$root" \
  --notes "Accepted after restrictive Recognition and routed to the local Biology Single." \
  --classification task-accepted \
  --mature > "$sandbox/metabolized.json"

"$PYTHON_BIN" - "$sandbox/metabolized.json" "$root" "$message_id" <<'PY'
import json
import sys
from pathlib import Path

result = json.load(open(sys.argv[1], encoding="utf-8"))
root = Path(sys.argv[2])
message_id = sys.argv[3]
assert result["status"] == "metabolized", result
assert result["record"]["messageId"] == message_id, result
assert result["record"]["classification"] == "task-accepted", result
assert result["receipt"]["receiptType"] == "metabolized", result
assert result["mature"]["mature_id"], result
assert (root / ".ie" / "messaging" / "metabolized" / f"{message_id}.json").is_file()
assert (root / "trajectory" / "messaging" / f"{message_id}.json").is_file()
PY

run_ie messaging status --path "$root" --json > "$sandbox/status-after-metabolize.json"
"$PYTHON_BIN" - "$sandbox/status-after-metabolize.json" <<'PY'
import json
import sys

status = json.load(open(sys.argv[1], encoding="utf-8"))
assert status["receipts"]["by_type"] == {
  "delivered": 1,
  "metabolized": 1,
  "rejected": 1,
}, status
assert status["metabolizations"]["by_status"] == {"metabolized": 1}, status
PY

"$PYTHON_BIN" - "$root/.ie/messaging/receipts" <<'PY'
import json
import sys
from pathlib import Path

receipt_types = {
    json.loads(path.read_text(encoding="utf-8"))["receiptType"]
    for path in Path(sys.argv[1]).glob("*.json")
}
assert {"rejected", "delivered", "metabolized"}.issubset(receipt_types), receipt_types
PY

printf '%s\n' "Messaging dogfood: PASS"