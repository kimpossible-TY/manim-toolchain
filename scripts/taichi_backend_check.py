"""Initialize one requested Taichi backend and execute a tiny kernel."""

import sys

import taichi as ti


if len(sys.argv) != 2 or sys.argv[1] not in {"metal", "cpu"}:
    raise SystemExit("Usage: taichi_backend_check.py [metal|cpu]")

requested = sys.argv[1]
arch = ti.metal if requested == "metal" else ti.cpu
ti.init(arch=arch, enable_fallback=False, offline_cache=False, default_fp=ti.f32)
value = ti.field(dtype=ti.f32, shape=1)


@ti.kernel
def step():
    value[0] = 3.0


step()
if value[0] != 3.0:
    raise SystemExit("Taichi kernel did not update state")
print(f"Taichi requested backend: {requested}")
print(f"Taichi initialized backend: {ti.lang.impl.current_cfg().arch}")
print("Taichi backend initialization: PASS")
