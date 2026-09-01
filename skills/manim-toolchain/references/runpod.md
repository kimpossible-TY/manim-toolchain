# Runpod Serverless Blender/Cycles workflow

Runpod is the production backend for Blender Cycles image sequences in this
toolchain. Local macOS rendering remains useful for EEVEE composition previews,
but the final image sequence is rendered by a Linux GPU worker.

## Components

```text
video repository
  -> visual-runpod-prepare
  -> portable bundle + render_manifest.json
  -> object storage (signed GET/PUT URLs)
  -> visual-runpod submit
  -> Runpod endpoint queue
  -> one worker/GPU/Blender process per chunk
  -> signed output archives
  -> visual-runpod download
  -> local PNG verification + FFmpeg composition
```

The local project does not install the Runpod SDK. `scripts/runpod_client.py`
uses the standard-library HTTPS client for the endpoint API; the worker image
installs `runpod` only for its handler adapter. `RUNPOD_API_KEY` and
`RUNPOD_ENDPOINT_ID` are environment variables, never manifest fields.

## Cloudflare R2 storage

The recommended storage path is a private Cloudflare R2 Standard bucket. R2 is
S3-compatible, so the client creates short-lived GET/PUT presigned URLs without
putting R2 credentials in Runpod jobs or bundles. Create a bucket-scoped R2 API
token with Object Read & Write permission, then configure the protected central
`.env` with mode `600`:

```sh
R2_ACCOUNT_ID=...
R2_BUCKET=manim-render
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_PREFIX=manim-render                 # optional
R2_URL_EXPIRY_SECONDS=86400             # optional; max 604800
```

`R2_ENDPOINT_URL` may be used instead of `R2_ACCOUNT_ID` when the endpoint is
already known. `visual-runpod` is the only wrapper that loads this credential
set; generic visualization and Blender wrappers scrub it from child processes.
Never put these values in a bundle, jobs file, or Git repository. Use the R2 S3
API endpoint for presigned URLs, not a custom domain.

## Prepare the bundle

```sh
visual-runpod-prepare \
  --scene scene.blend --scene-script scenes/hero.py --asset-dir assets \
  --output render-job --width 1920 --height 1080 --fps 30 \
  --frame-start 1 --frame-end 240 --chunk-size 60 \
  --samples 128 --device auto

visual-runpod-prepare --scene scene.blend --output render-job \
  --width 960 --height 540 --fps 24 --frame-start 1 --frame-end 24 \
  --chunk-size 24 --samples 32 --device auto --validate-source
```

The default is `--require-gpu`: a completed worker report must say
`render_device=GPU`. Use `--no-require-gpu` only for an intentional CPU
diagnostic. Local source validation is opt-in because final portability
validation happens in the worker; it is also useful when a source `.blend`
contains an absolute or missing asset path.

The bundle contains `scene.blend`, an optional `scene.py`, explicitly selected
assets, the Blender runner, and the frame verifier. It does not include the
repository, credentials, browser data, or a local output sequence. Asset paths
must be Blender-relative (`//...`) or packed for remote portability.

## Build the worker image

```sh
docker build --platform linux/amd64 \
  -f runpod/Dockerfile \
  --build-arg BLENDER_VERSION=5.2.1 \
  --build-arg BLENDER_SHA256=a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9 \
  -t ghcr.io/ORG/manim-blender-worker:5.2.1 .
docker push ghcr.io/ORG/manim-blender-worker:5.2.1
```

Select this image in a queue-based Runpod Serverless endpoint. Start with zero
or a small active-worker floor and cap maximum workers to the available GPU
budget. A queue endpoint fits batch frame work: the client creates independent
chunk jobs and the endpoint schedules them. The image uses a digest-pinned CUDA
base, Blender 5.2.1 with a required official SHA-256, and a pinned Runpod SDK.
Update the Blender version and matching hash deliberately, then deploy the
pushed image by immutable digest rather than a mutable tag.

## Submit and orchestrate chunks

The simplest path uses the built-in R2 mode. It uploads the archived bundle,
creates one input GET URL, and creates distinct output PUT/GET URLs for every
chunk automatically:

```sh
# Put RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in the protected central .env.

visual-runpod submit --bundle render-job --r2 \
  --execution-timeout-ms 3600000 --ttl-ms 86400000

visual-runpod wait --jobs-file render-job.runpod.json --download

# Retry terminally failed chunks with fresh R2 URLs:
visual-runpod retry --jobs-file render-job.runpod.json

# Delete only this batch's R2 input/output objects after local verification:
visual-runpod cleanup --jobs-file render-job.runpod.json --confirm
```

The generated object layout is `R2_PREFIX/<batch-id>/input.tar.gz` and
`R2_PREFIX/<batch-id>/chunks/<chunk-id>.tar.gz`. Configure an R2 lifecycle rule
to delete old job prefixes after the retention period.

The client also supports manually supplied signed HTTPS URLs when another
storage provider is required. It can upload the archive through a signed PUT
URL, and each output chunk needs a distinct object key. For multiple chunks,
use a URL template or a URL map:

```sh
# Put RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID in the protected central .env.

visual-runpod submit --bundle render-job \
  --input-url 'https://storage.example/input/render-job.tar.gz' \
  --input-upload-url 'https://storage.example/input/render-job.tar.gz?...' \
  --output-upload-url-template 'https://storage.example/output/{chunk_id}.tar.gz?...' \
  --output-download-url-template 'https://storage.example/output/{chunk_id}.tar.gz?...' \
  --execution-timeout-ms 3600000 --ttl-ms 86400000

visual-runpod wait --jobs-file render-job.runpod.json --download
```

When the storage provider uses different signed URLs for upload and download,
write a JSON map such as:

```json
{
  "chunk-0000-000001-000060": {
    "upload": "https://storage.example/output/chunk-0000.tar.gz?...",
    "download": "https://storage.example/output/chunk-0000.tar.gz?..."
  }
}
```

Pass it with `--output-url-file`. The jobs file contains signed URLs and is
ignored by Git; treat it like a secret and delete or rotate URLs after use.
The API key is never written to that file.

The first chunk requests asset validation. Every chunk then runs one Blender
process, writes a PNG sequence/report, verifies the exact frame range, uploads
`output.tar.gz`, and returns its archive digest. The client polls with:

```sh
visual-runpod status --jobs-file render-job.runpod.json
visual-runpod wait --jobs-file render-job.runpod.json --poll-seconds 10
visual-runpod download --jobs-file render-job.runpod.json
```

`download` verifies each archive digest and frame range, rejects conflicting
frames, merges all chunks, and writes `output/render_report.json`. Only after
that local verification should the frames be passed to FFmpeg.

`retry` resubmits only failed R2 chunks and keeps the same verified input
archive. `cleanup` is explicit and confirmation-gated because presigned URLs
expiring does not delete the underlying R2 objects.

## Operational boundaries

- Do not put PNGs or base64 media in the Runpod JSON input/result. Use object
  storage for archives and return metadata plus signed URLs.
- Do not call `parallel_blender_render.py` in the worker. Runpod supplies the
  horizontal fan-out; multiple Blender processes competing for one GPU usually
  increase memory pressure and reduce predictability.
- Keep endpoint execution timeout above the slowest expected chunk and set a
  finite TTL so abandoned jobs do not remain indefinitely.
- The client does not create an endpoint, configure a GPU type, or upload an
  image registry credential. Those are deliberate Runpod account/deployment
  actions.
- The default documentation and wrappers use Runpod Serverless.
