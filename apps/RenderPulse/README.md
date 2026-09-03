# RenderPulse

RenderPulse is a native macOS menu-bar monitor for RunPod render work. It keeps
internal Pod or shot names out of the primary UI and instead shows each
user-visible work with its name, progress, Pods, warning count, error count,
and ETA.

## Run locally

```sh
cd /Users/taeyoung/Developer/visual-explainer-toolchain/apps/RenderPulse
swift run
```

Choose **Add Work**, give the work a human-readable name, and select its
`runpod.jobs.json` file. RenderPulse stores only the display name and local jobs
file path in `~/Library/Application Support/RenderPulse/works.json`.

The app invokes the existing `visual-runpod` wrapper, which remains responsible
for RunPod credentials and API access. It looks first in `~/.local/bin`, then
in the source checkout when run through SwiftPM. To override that path when
launching the app, set `RENDER_PULSE_RUNPOD_PATH`.

```sh
RENDER_PULSE_RUNPOD_PATH=/Users/taeyoung/Developer/visual-explainer-toolchain/bin/visual-runpod swift run
```

## Current scope

- Active work is shown with a rotating gear in the menu bar.
- Multiple works appear as individual cards in the popover; one can be pinned as
  the menu-bar work.
- Status refreshes every five seconds through `visual-runpod status --stream --json`.
- `visual-runpod wait` and `visual-runpod progress` automatically register a
  Work using the jobs-file's parent directory name; pass `--work-name` to set
  a human-readable title.
- ETA is calculated locally after enough progress samples are available.
- Warning and error counts are aggregated from RunPod Pod states.

For a Work that spans multiple jobs files, register them together from the
central toolchain:

```sh
visual-runpod register-work \
  --work-name "Gardasil 전체 렌더링" \
  --jobs-file /path/to/B01/runpod.jobs.json \
  --jobs-file /path/to/B02/runpod.jobs.json
```

The app is intentionally unsandboxed for this development build so it can read
jobs files outside the repository. A signed, sandboxed `.app` distribution would
store security-scoped bookmarks for each selected jobs file.
