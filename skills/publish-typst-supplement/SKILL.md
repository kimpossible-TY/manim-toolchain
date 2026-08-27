---
name: publish-typst-supplement
description: Publish a generated video or other large supplemental file as a versioned GitHub Release asset, link it from a Typst document, keep it out of Git history, and verify the resulting PDF hyperlink. Use when a user wants a static Typst/PDF paper to reference locally generated supplemental media without committing the media file.
---

# Publish a Typst Supplement

Publish supplemental media outside the repository's Git objects while giving the compiled PDF a durable, clickable URL.

## Preserve scope

- Treat release creation and asset upload as external mutations. Perform them only when the user explicitly asks to upload or publish the supplement.
- Do not commit, push source changes, delete releases, replace assets, or move tags unless the user separately authorizes that action.
- Preserve unrelated working-tree changes. Inspect targeted files before editing and use focused patches.
- Prefer GitHub Releases when the repository already uses GitHub and the user has not selected another host. If browser-native streaming is essential, explain that release assets usually download and ask the user to choose a streaming host.

## Preflight

1. Resolve the repository from `git remote get-url origin`; do not assume the owner or repository name.
2. Confirm the asset exists and inspect its size, media type, and SHA-256 digest.
3. Check `gh auth status` and inspect existing releases/tags before selecting a tag.
4. Locate the passage in the Typst source that the supplement explains. Avoid placing the link in an unrelated generic preamble unless a reusable URL constant belongs there.

Use a descriptive, versioned tag such as `distribution-video-v1`. Avoid `/releases/latest/download/...` in a paper because a later release can change what `latest` means.

For owner `OWNER`, repository `REPO`, tag `TAG`, and exact asset filename `FILE`, the durable URL is predictable before upload:

```text
https://github.com/OWNER/REPO/releases/download/TAG/FILE
```

If the chosen release or asset name already exists, inspect it. Do not overwrite or delete it without explicit authorization. Prefer a new version tag when publishing genuinely new content.

## Link the Typst source

Define the URL once near the file's imports or other document-level constants:

```typst
#let supplement-video-url = "https://github.com/OWNER/REPO/releases/download/TAG/FILE"
```

Add a descriptive link beside the relevant explanation:

```typst
The dynamic interpretation is shown in a
#link(supplement-video-url)[#underline[narrated visualization]].
```

Make the link text describe its destination. Typst links are not visually distinct by default, so use the document's existing link style or a restrained visible treatment such as underline.

When the media is generated output that should not enter Git history, add a narrow ignore rule if an equivalent rule is not already present. For example:

```gitignore
video/**/*.mp4
```

Do not ignore the entire source directory when it also contains scripts, narration, thumbnails, or other files intended for version control.

## Publish the release asset

For a new release, upload the local file directly through the GitHub CLI:

```sh
gh release create TAG 'PATH#Human-readable asset label' \
  --repo OWNER/REPO \
  --title 'Descriptive supplement title' \
  --notes 'State which section or result this supplement accompanies.'
```

If `TAG` does not exist, `gh release create` creates it from the remote default branch. The media file is uploaded through the Releases API and is not added to Git history.

For an already-created release with no conflicting asset, use `gh release upload TAG PATH --repo OWNER/REPO`. Keep the Typst URL synchronized with the exact tag and asset filename.

## Verify the result

Verification is part of completion:

1. Query the release and confirm it is published, the asset state is `uploaded`, and its remote size and digest match the local file when GitHub exposes a digest.
2. Follow redirects from the durable asset URL and confirm a successful response.
3. Compile the document to a temporary PDF outside the repository when practical.
4. Confirm the PDF contains the intended URI, using `qpdf`, `mutool`, or another available PDF inspection tool.
5. Report compilation warnings separately from errors; do not imply unrelated existing warnings were introduced by the link.

Finish with the release URL, clickable local file locations for source edits, verification results, and an explicit statement of whether any local edits were committed or pushed.
