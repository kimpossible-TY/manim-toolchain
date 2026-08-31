# Colab compute and Cycles rendering via Colab CLI

Read this when executing Blender Cycles rendering or Taichi compute workloads
remotely. Colab CLI is the standard remote destination for all Blender Cycles
production rendering. Manim, ordinary PyGfx, EEVEE previews, and final FFmpeg
composition remain local by default.

The persistent session (`visual-render`) serves as a fast remote GPU worker that
eliminates repeated provisioning and installation overhead across jobs.

The installed official CLI is a separate system-level tool, not a dependency
of the central visualization project. This repository was validated against
`google-colab-cli 0.6.0`; consult the current official
[`google-colab-cli` installation guidance](https://github.com/googlecolab/google-colab-cli)
before changing it. Do not reinstall a working CLI just to refresh it.

## Session and job lifecycles

The default remote-session policy is:

```text
session = visual-render
accelerator = T4
policy = reuse before create
```

The lifetimes are deliberately separate:

```text
job lifecycle:     prepare -> upload -> execute -> download -> verify
session lifecycle: create -> reuse for zero or more jobs -> explicit stop
```

`visual-render` is the default name for every generated job, so later jobs can
reuse the same worker. A normal successful job leaves it running. Stop it when
remote work is actually finished:

```sh
visual-colab-stop
# or, from this repository:
./bin/visual-colab-stop --session visual-render
```

`COLAB_SESSION` or `visual-colab-stop --session NAME` selects another named
session. The generated commands also accept `--stop-after-job` (or
`COLAB_STOP_AFTER_JOB=1`) as an explicitly disposable compatibility mode. A
job failure never automatically stops a healthy shared session.

## Authorization and reuse

Do not authenticate, start a remote session, upload, start remote computation,
or consume paid/limited GPU quota without clear authorization in the current
request. Interactive OAuth or ADC setup is a user action. Reusing an already
authorized session during the same explicitly requested remote workflow does
not require another allocation authorization, but uploading the next job and
running it remain visible authorization-marked remote actions.

`visual-colab-prepare` only creates a local bundle. It never logs in, uploads,
allocates a runtime, or starts a job. Once the bundle has been reviewed and
the remote work authorized, run its generated commands:

```sh
./render-job/colab_commands.sh
```

The script first calls the supported official commands `colab sessions`,
`colab status -s NAME`, and `colab ls -s NAME /content`:

- an exact named, IDLE, reachable session is reported as
  `COLAB_SESSION_ACTION=reused`;
- an absent session is never created silently;
- allocation requires `--allow-new-session` or
  `COLAB_ALLOW_NEW_SESSION=1`;
- a listed-but-stale/unreachable or busy session fails clearly instead of
  creating a second runtime;
- a detectable accelerator mismatch fails as incompatible because a session's
  accelerator cannot change in place.

The helper validates accelerator input before invoking `colab new`. The CLI's
currently exposed GPU names are `T4`, `L4`, `G4`, `H100`, and `A100`. T4 is the
default; no automatic escalation or fallback is performed. `cpu` is an
explicit local policy sentinel that creates a CPU session by omitting
`--gpu`. If a different accelerator is required, use another explicitly named
session or explicitly stop the old session before a new allocation. The
workflow reports both `COLAB_REQUESTED_GPU` and `COLAB_ACTUAL_GPU`; a flag
alone is never treated as proof of hardware use.

## Portable bundle and remote paths

Prepare a portable Blender bundle after validating the source scene:

```sh
visual-colab-prepare \
  --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
  --output render-job --width 1920 --height 1080 --fps 30 \
  --frame-start 1 --frame-end 240 --samples 128 --device auto
```

The resulting `render-job/` contains the `.blend`, optional scene script,
explicit assets, compact Blender helpers, `render_manifest.json`, an empty
`output/`, and authorization-marked command/bootstrap/verification helpers.
Bundle creation runs no remote command. Its source and asset boundary rejects
`.env` files, credentials/ADC files, SSH/private keys, common browser-profile
files, and sensitive key/certificate suffixes. Only explicitly named assets
are copied; do not add unrelated or confidential data.

Each execution derives a unique `REMOTE_JOB_ID` unless `COLAB_JOB_ID` is
explicitly supplied. The upload and output archive use unique `/content`
paths, and the remote runner executes in:

```text
/content/manim-toolchain/jobs/<job-id>/
```

This prevents a failed job's files from being mistaken for the next job's
files. Successful jobs remove their job-specific remote cache after the local
download; failed jobs retain the exact job directory for diagnosis. A reused
VM may cache dependencies or files during its lifetime, but that cache is not
part of correctness.

`/content` is ephemeral. Important artifacts must always return to local
storage. The generated flow is:

```text
remote Cycles render -> PNG sequence/report -> download -> local frame/report verification -> local FFmpeg
```

The bundle remains recoverable on a newly provisioned authorized session: the
remote bootstrap checks whether a working Blender is already available and
installs it only when necessary. It then performs a real Cycles render and
verifies the complete frame sequence/report. A configured device listing alone
is not evidence of a successful GPU render.

## Generated command status

The command script emits machine-readable lines such as:

```text
COLAB_SESSION=visual-render
COLAB_SESSION_ACTION=reused
COLAB_REQUESTED_GPU=T4
COLAB_ACTUAL_GPU=T4
COLAB_SESSION_HEALTH=reachable
REMOTE_JOB_ID=...
REMOTE_JOB_DIRECTORY=/content/manim-toolchain/jobs/...
REMOTE_EXECUTION=completed
LOCAL_ARCHIVE=...
COLAB_SESSION_LEFT_RUNNING=yes
```

When the script allocates a worker, the action is `created`. When it cannot
reuse or safely allocate one, it emits `unavailable` (or `incompatible` for a
detected fixed-accelerator mismatch) and does not provision a second runtime.
Completion is reported only after the remote command, output archive, local
download, frame verification, and report verification succeed.

## Current CLI limitations

The current CLI exposes human-readable, not JSON, output for `sessions` and
`status`; the bundled `colab_session.py` therefore parses the documented
display lines. `colab sessions` can label a server assignment `[?]` when the
CLI has no local state mapping for its friendly name, so that orphan cannot be
reused safely by name. `colab status` reports assignment metadata and
IDLE/BUSY state; the additional `colab ls` probe confirms that the contents
proxy responds, but neither proves that Blender will use a GPU. Backend quota
or entitlement for an accepted accelerator name can still fail at allocation.

The CLI has no supported command to change a session's accelerator in place.
For a new accelerator, use another named session or the explicit sequence
`visual-colab-stop --session OLD` followed by a newly authorized job with the
requested `COLAB_GPU`. The CLI also has no stable machine-readable output
contract, so after upgrading it, recheck the session display format and rerun
the local mock tests before relying on generated commands.

For Taichi, benchmark a reduced local simulation first. If Colab CUDA is
chosen, keep algorithm, time step, precision, and seed explicit; usually
download state data and render it locally with PyGfx. Do not assume Colab
headless PyGfx is reliable until a real remote frame has been verified.
