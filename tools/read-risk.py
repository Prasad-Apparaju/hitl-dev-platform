#!/usr/bin/env python3
"""Read risk level from a decision packet. Used by deployment workflows."""
import sys
try:
    import yaml
except ImportError:
    print("medium")  # safe default if yaml not available
    sys.exit(0)

packet_path = sys.argv[1] if len(sys.argv) > 1 else None
if not packet_path:
    print("high")  # unknown = manual approval
    sys.exit(0)

try:
    with open(packet_path) as f:
        data = yaml.safe_load(f)
    rollout = data.get("rollout", {})
    risk = rollout.get("risk") or data.get("risk_level") or "high"
    print(risk)
except Exception:
    print("high")  # fail safe = manual approval
