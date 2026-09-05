#!/usr/bin/env bash
set -euo pipefail

# The foreground renderer owns the Pod lifetime. It exits after publishing a
# terminal R2 status document, allowing the local controller to delete the Pod.
exec python3 /opt/render/worker/pod_runner.py
