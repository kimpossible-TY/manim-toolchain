#!/usr/bin/env python3
"""Small, dependency-free helpers shared by the Runpod client and worker."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tarfile


SENSITIVE_FILENAMES = {
    ".env",
    ".netrc",
    "id_rsa",
    "id_ecdsa",
    "id_dsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
    "application_default_credentials.json",
    "adc.json",
    "cookies",
    "cookies.sqlite",
    "login data",
    "web data",
    "local state",
}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SENSITIVE_DIRECTORY_NAMES = {
    ".aws",
    ".ssh",
    "gcloud",
    "chrome",
    "chromium",
    "firefox",
    "user data",
    "browser profile",
    "browser profiles",
}
SENSITIVE_NAME_MARKERS = (
    "credential",
    "private_key",
    "private-key",
    "privatekey",
    "service_account",
    "service-account",
    "application_default_credentials",
)


def is_sensitive(path: Path) -> bool:
    """Return whether a path looks like a credential or browser-secret file."""

    lowered_parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return (
        name in SENSITIVE_FILENAMES
        or name.startswith(".env")
        or path.suffix.lower() in SENSITIVE_SUFFIXES
        or bool(lowered_parts & SENSITIVE_DIRECTORY_NAMES)
        or any(marker in name for marker in SENSITIVE_NAME_MARKERS)
    )


def copy_asset(source: Path, destination: Path, copied: list[str]) -> None:
    """Copy one explicit file/directory while rejecting links and secrets."""

    source = source.expanduser()
    if source.is_symlink():
        raise ValueError(f"Refusing to include symlink asset: {source}")
    source = source.resolve()
    if is_sensitive(source):
        raise ValueError(f"Refusing to include credential-like asset: {source.name}")
    if source.is_file():
        files = [(source, Path(source.name))]
    elif source.is_dir():
        files = [
            (child, child.relative_to(source))
            for child in sorted(source.rglob("*"))
            if child.is_file()
        ]
    else:
        raise ValueError(f"Asset path does not exist: {source}")

    for file_path, relative_path in files:
        if file_path.is_symlink():
            raise ValueError(f"Refusing to include symlink asset: {file_path.name}")
        if is_sensitive(file_path) or is_sensitive(file_path.resolve()):
            raise ValueError(f"Refusing to include credential-like asset: {file_path.name}")
        target = destination / relative_path
        if target.exists():
            raise ValueError(f"Asset destination collision: {target.relative_to(destination.parent)}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        copied.append(target.relative_to(destination.parent).as_posix())


def copy_file(source: Path, destination: Path) -> None:
    source = source.expanduser()
    if source.is_symlink():
        raise ValueError(f"Refusing to include symlink file: {source}")
    source = source.resolve()
    if not source.is_file():
        raise ValueError(f"File does not exist: {source}")
    if is_sensitive(source):
        raise ValueError(f"Refusing to include credential-like file: {source.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_directory(source: Path, archive_path: Path, arcname: str = "output") -> None:
    """Create a gzip tar without following symlinks."""

    source = source.resolve()
    if not source.is_dir():
        raise ValueError(f"Archive source is not a directory: {source}")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        for child in sorted(source.rglob("*")):
            if child.is_symlink():
                raise ValueError(f"Refusing to archive symlink: {child}")
            archive.add(child, arcname=(Path(arcname) / child.relative_to(source)).as_posix())


def safe_extract_tar(archive_path: Path, destination: Path) -> None:
    """Extract regular files/directories only, preventing traversal and links."""

    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:*") as archive:
        members = archive.getmembers()
        for member in members:
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe archive path: {member.name}")
            target = (destination / member_path).resolve()
            if not target.is_relative_to(destination):
                raise ValueError(f"Unsafe archive path: {member.name}")
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError(f"Archive links/devices are not allowed: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"Unsupported archive entry: {member.name}")

        for member in members:
            target = destination / member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"Could not read archive entry: {member.name}")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def load_manifest(bundle: Path) -> dict[str, object]:
    import json

    manifest_path = bundle / "render_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing render manifest: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid render manifest: {manifest_path}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("render_manifest.json must contain an object")
    return manifest
