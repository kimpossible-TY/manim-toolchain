# Runpod Pod Blender/Cycles workflow

Runpod Pods are the default backend for substantial Blender Cycles sequences.
Use this guide after selecting remote rendering under the
[main skill's mode and budget guidance](../SKILL.md#select-and-retain-the-blender-render-mode).
Local EEVEE/Cycles iteration and suitable bounded local production remain available.
For a remote job, one disposable Linux GPU Pod renders the complete requested
frame range.

## Components and ownership

```text
video repository
  -> visual-runpod-prepare
  -> portable bundle + runpod-pod render_manifest.json
  -> Cloudflare R2 input archive
  -> visual-runpod submit
  -> one Runpod Pod / one GPU / one Blender process
  -> R2 status object + output archive
  -> visual-runpod download -> local PNG verification + FFmpeg composition
  -> Pod deletion
```

`visual-runpod` uses `runpodctl` to create, inspect, and delete Pods. It does
not use a Serverless endpoint or the Runpod Python SDK. Export `RUNPOD_API_KEY`
in the shell that launches the command; the client never reads or writes a
Runpod key from a config file. Pod placement settings and R2 credentials are
environment variables only; they are never copied into a bundle or manifest.

The Pod is created after the input archive is already available in R2. Its
environment contains only the one-time input URL, output/status PUT URLs, and
the render event. The worker publishes progress and the final result to R2;
the local process consequently remains restartable while the Pod runs.

## Cloudflare R2 storage

The recommended storage path is a private Cloudflare R2 Standard bucket. R2 is
S3-compatible, so the local client makes short-lived presigned URLs without
putting R2 credentials in the Pod or the jobs file. Create a bucket-scoped R2
API token with Object Read & Write permission, then configure the protected
central `.env` with mode `600`:

```sh
R2_ACCOUNT_ID=...
R2_BUCKET=manim-render
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_PREFIX=manim-render                 # optional
R2_URL_EXPIRY_SECONDS=86400             # optional; max 604800
```

`R2_ENDPOINT_URL` may be used instead of `R2_ACCOUNT_ID` when the S3 API
endpoint is already known. `visual-runpod` is the only wrapper that loads this
credential set; generic visualization and Blender wrappers scrub it from child
processes. Never put these values in a bundle, jobs file, or Git repository.
Use the R2 S3 API endpoint for presigned URLs, not a custom domain.

The Pod needs no cloud credential to call R2: the client passes only presigned
URLs. The status object remains useful if the local terminal disconnects.

## Pod configuration

Install `runpodctl` and authenticate it with the same Runpod account as the API
key. The command must be discoverable on `PATH`, or configure `RUNPODCTL_BIN`.
Set the image by immutable digest whenever practical and use the exact Runpod
GPU type ID accepted by `runpodctl pod create`:

```sh
RUNPOD_API_KEY=...
RUNPOD_POD_IMAGE=ghcr.io/kimpossible-ty/manim-blender-worker@sha256:3d33302c2c79371832cf320514c2b8a112b0a435a92b22af7779bbadb9acec78
RUNPOD_POD_GPU_ID=replace-with-runpod-gpu-id
RUNPOD_POD_CONTAINER_DISK_GB=30       # optional; default 30
RUNPOD_POD_TERMINATE_AFTER=8h          # local wait/cost budget; default 8h
# Optional affinity and private-image registry access:
# RUNPOD_POD_DATA_CENTER_IDS=EU-RO-1,US-KS-2
# RUNPOD_REGISTRY_AUTH_ID=...
```

`RUNPOD_POD_TERMINATE_AFTER` accepts a duration such as `8h`, `45m`, or `1d`.
The client probes the installed `runpodctl`: newer versions may pass a
create-time termination flag, while the current v2.12 command surface does
not expose one. In that case the value is the local monitor's maximum wait
budget; `visual-runpod status`, `visual-runpod wait`, and
`visual-runpod progress` delete the Pod automatically on a terminal result,
and a bounded wait timeout also deletes it. Use `--keep-pod` only while
diagnosing a failure. Use the explicit, confirmation-gated `terminate`
command to stop a non-terminal Pod. For unattended runs, also enforce an
account spend limit because a hard local process failure cannot run cleanup.

## Prepare the bundle

```sh
visual-runpod-prepare \
  --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
  --output render-job --width 1920 --height 1080 --fps 30 \
  --frame-start 1 --frame-end 240 --samples 128 --device auto

visual-runpod-prepare --scene scene.blend --output render-job \
  --width 960 --height 540 --fps 24 --frame-start 1 --frame-end 24 \
  --samples 32 --device auto --validate-source
```

`--asset-dir` copies directory contents, but it does not infer files imported
by a scene wrapper. If `scene.py` loads another Python file (for example with
`runpy` or `exec`), name that dependency explicitly with `--asset-file` and
make the wrapper resolve it from the bundle's `assets/` directory:

```sh
visual-runpod-prepare \
  --scene scene.blend --scene-script scenes/runpod_B03.py \
  --asset-dir assets --asset-file scenes/gardasil9_blender.py \
  --output render-job ...
```

Run `verify_runpod_render_job.py` before submission; missing wrapper
dependencies should fail locally rather than during Pod asset validation. The
default is `--require-gpu`: a completed worker report must say
`render_device=GPU`. Use `--no-require-gpu` only for an intentional CPU
diagnostic.

The bundle contains `scene.blend`, an optional `scene.py`, explicitly selected
assets, the Blender runner, and the frame verifier. It does not include the
repository, credentials, browser data, or local output. Asset paths must be
Blender-relative (`//...`) or packed for remote portability.

## GPU compatibility gate

Device enumeration alone is not evidence that Cycles can render on a particular
GPU image. Before sending a long production range to a new GPU type, submit a
one-frame Cycles probe and retain its report with `compute_backend` and GPU
model. For `auto` or `gpu`, the worker retries a recognised OptiX/PTX compiler
failure once with CUDA in a fresh Blender process; an explicit `--device optix`
remains strict. Do not scale the range until the probe passes with the selected
GPU type.

Treat a `COMPLETED` status as render success only when the final status has a
valid output archive digest. A Pod that exits before writing status is a
failure, not an implicit completed render.

## Build the worker image

```sh
docker build --platform linux/amd64 \
  -f runpod/Dockerfile \
  --build-arg BLENDER_VERSION=5.2.1 \
  --build-arg BLENDER_SHA256=a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9 \
  -t ghcr.io/kimpossible-ty/manim-blender-worker:5.2.1-pod-slim-py310.20260903 .
docker push ghcr.io/kimpossible-ty/manim-blender-worker:5.2.1-pod-slim-py310.20260903
```

The image has a digest-pinned CUDA base and Blender 5.2.1 with a required
official SHA-256. It starts `pod_start.sh`, which runs the Pod event runner;
the runner executes one Blender process for the full requested range, uploads
the archive, and exits. Update the Blender version and matching hash
deliberately, then set `RUNPOD_POD_IMAGE` to the pushed digest.

The image uses the CUDA **base** image rather than the larger CUDA runtime
variant. This keeps disposable-Pod pull time and storage lower while retaining
the CUDA/OptiX libraries Blender needs. The worker is tested against the
Python 3.10 interpreter shipped by Ubuntu 22.04; code that runs inside the Pod
must use `datetime.timezone.utc` rather than the Python 3.11-only
`datetime.UTC` API.

## Submit, monitor, download, and clean up

The standard R2 path archives the bundle once, uploads it once, creates one
input GET URL, and creates output/status PUT and GET URLs for the Pod:

```sh
visual-runpod submit --bundle render-job --r2

# Report R2-backed phase/frame progress; delete the terminal Pod automatically.
visual-runpod progress --jobs-file render-job.runpod.json --download

# The same operation without progress lines:
visual-runpod wait --jobs-file render-job.runpod.json --download

# Inspect, retry as a new Pod, or stop the current Pod explicitly:
visual-runpod status --jobs-file render-job.runpod.json
visual-runpod retry --jobs-file render-job.runpod.json
visual-runpod terminate --jobs-file render-job.runpod.json --confirm

# After retaining verified local output, delete this batch's R2 objects:
visual-runpod cleanup --jobs-file render-job.runpod.json --confirm
```

The R2 object layout is `R2_PREFIX/<batch-id>/input.tar.gz`,
`R2_PREFIX/<batch-id>/output.tar.gz`, and
`R2_PREFIX/<batch-id>/status.json`. Configure an R2 lifecycle rule to delete
old job prefixes after the chosen retention period.

`download` verifies the archive digest and exact frame range, then writes
`output/render_report.json`. Only after local verification should the frames
be passed to FFmpeg. The jobs file contains presigned URLs and Pod metadata,
has mode `0600`, and must not be committed. The API key itself is never written
to it.

The worker Pod is created with SSH disabled (`--ssh=false`) and publishes no
SSH port. This is intentional: the batch worker receives its event through
environment variables and R2 presigned URLs, so an SSH endpoint adds attack
surface without helping the render. For interactive diagnosis, use a separate
explicitly configured Pod rather than weakening the production worker default.

## Operational boundaries

- One submitted job equals one Pod, one GPU, and one Blender process. The
  client deliberately does not split the range or create a Pod pool.
- Do not call `parallel_blender_render.py` inside the Pod. Multiple Blender
  processes competing for one GPU increase memory pressure and reduce
  predictability.
- Size `RUNPOD_POD_CONTAINER_DISK_GB` for the uncompressed bundle, working
  files, and output range. A Pod disk is not persistent storage; R2 is the
  durable handoff.
- `runpodctl pod create` can wait for capacity. The client uses a
  create-time `--terminate-after` when the installed CLI supports it; current
  v2.12 builds do not, so unattended runs should add an account spend limit or
  an external watchdog in addition to the client's terminal/timeout cleanup.
- The installed CLI is probed at runtime instead of assuming a particular flag
  set. In particular, `--terminate-after` is absent from current v2.12 help
  output; the local wait budget is still enforced, and terminal/timeout
  cleanup is idempotent if a Pod was removed by a user or watchdog.
- Status is written to R2 with short-lived PUT URLs and can arrive out of order
  while the output archive is uploading. The client merges progress
  monotonically, so a late upload status cannot make RenderPulse show fewer
  completed frames.
- The CLI does create and delete Pods, but it does not manage account budgets,
  buy credits, or mutate templates. Select GPU/image settings deliberately in
  the protected environment configuration.
