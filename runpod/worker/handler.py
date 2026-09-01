#!/usr/bin/env python3
"""Runpod Serverless adapter for the dependency-free Blender worker core."""

from __future__ import annotations

import runpod

from core import handle_event


runpod.serverless.start({"handler": handle_event, "return_aggregate_stream": True})
