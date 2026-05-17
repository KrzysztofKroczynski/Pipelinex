import sys
import json

args = json.load(sys.stdin)
channel = args.get("channel", "#general")
message = args.get("message", "")

# Stub: print to stdout instead of sending to Slack
print(f"[SLACK STUB] {channel}: {message}", file=sys.stderr)
print(json.dumps({"ok": True, "stub": True, "channel": channel}))
