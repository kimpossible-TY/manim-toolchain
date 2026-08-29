"""Small Blender-native helpers for Cycles device selection and reporting.

This module is deliberately imported only by Blender's embedded Python.  It is
kept separate from scene code because Blender's device API varies by release.
"""

from __future__ import annotations

from typing import Any


_GPU_BACKENDS = ("OPTIX", "CUDA", "METAL", "HIP", "ONEAPI")


def _cycles_preferences(bpy: Any) -> Any | None:
    addon = bpy.context.preferences.addons.get("cycles")
    return addon.preferences if addon else None


def _refresh_devices(preferences: Any) -> list[Any]:
    for method_name in ("refresh_devices", "get_devices"):
        method = getattr(preferences, method_name, None)
        if method is not None:
            try:
                method()
            except Exception:
                # Some Blender builds expose one of these methods without
                # supporting it for every platform.  The current list remains
                # useful for a safe CPU fallback.
                pass
    return list(getattr(preferences, "devices", ()))


def _device_records(devices: list[Any]) -> list[dict[str, object]]:
    return [
        {
            "name": str(getattr(device, "name", "unknown")),
            "type": str(getattr(device, "type", "unknown")),
            "use": bool(getattr(device, "use", False)),
        }
        for device in devices
    ]


def _try_backend(preferences: Any, backend: str) -> list[Any]:
    try:
        preferences.compute_device_type = backend
    except Exception:
        return []
    return _refresh_devices(preferences)


def configure_cycles(
    bpy: Any,
    scene: Any,
    *,
    requested_device: str = "auto",
    require_gpu: bool = False,
) -> dict[str, object]:
    """Select Cycles and an actually configured compute device.

    A real render must still be performed before treating this result as a
    success.  The report deliberately distinguishes configured state from a
    completed render.
    """

    scene.render.engine = "CYCLES"
    preferences = _cycles_preferences(bpy)
    result: dict[str, object] = {
        "requested_device": requested_device,
        "configured_device": "CPU",
        "compute_backend": "NONE",
        "devices": [],
        "fallback_reason": None,
    }

    if requested_device == "cpu":
        scene.cycles.device = "CPU"
        return result

    if preferences is None:
        message = "Cycles preferences are unavailable in this Blender build"
        if require_gpu:
            raise RuntimeError(message)
        result["fallback_reason"] = message
        scene.cycles.device = "CPU"
        return result

    requested_backends = (
        _GPU_BACKENDS
        if requested_device in {"auto", "gpu"}
        else (requested_device.upper(),)
    )
    for backend in requested_backends:
        devices = _try_backend(preferences, backend)
        gpu_devices = [
            device for device in devices if str(getattr(device, "type", "")).upper() != "CPU"
        ]
        if not gpu_devices:
            continue
        for device in devices:
            device.use = device in gpu_devices
        scene.cycles.device = "GPU"
        result.update(
            {
                "configured_device": "GPU",
                "compute_backend": backend,
                "devices": _device_records(devices),
            }
        )
        return result

    devices = _refresh_devices(preferences)
    for device in devices:
        device.use = str(getattr(device, "type", "")).upper() == "CPU"
    scene.cycles.device = "CPU"
    result["devices"] = _device_records(devices)
    message = "No compatible Cycles GPU device was configured; using CPU"
    if require_gpu:
        raise RuntimeError(message)
    result["fallback_reason"] = message
    return result
