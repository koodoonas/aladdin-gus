#!/usr/bin/env python3
"""Audit the distributable repository for game files and copied binary blocks."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = {
    ".gitattributes",
    ".github/workflows/build.yml",
    ".github/workflows/release.yml",
    ".gitignore",
    "ALADGUS.COM",
    "CHANGELOG.md",
    "CONFIG.BAT",
    "INSTALL.BAT",
    "LICENSE",
    "Makefile",
    "PROVENANCE.md",
    "README.md",
    "release/README.TXT",
    "release/RELEASE_NOTES.md",
    "RESTORE.BAT",
    "SECURITY.md",
    "SHA256SUMS.txt",
    "src/aladgus.s",
    "tests/test_config.py",
    "tools/__init__.py",
    "tools/audit_repo.py",
    "tools/patch_aladdin_gus.py",
}
FORBIDDEN_NAMES = {
    "ALADDIN.EXE",
    "ALADDIN.GUS",
    "ALAD_ORG.EXE",
    "SOUND.CFG",
    "SND_ORG.CFG",
}
FORBIDDEN_SUFFIXES = {
    ".iso", ".jam", ".raw", ".rar", ".xis", ".xun", ".zip",
}
EXPECTED_COM_SHA256 = (
    "442d056778de3429fba16dfa5e7edce6a02912bb75e5ad76480e160f99eb0652"
)


def repository_files() -> dict[str, Path]:
    """Return tracked files, or the release allowlist before Git initialization."""
    try:
        output = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            stderr=subprocess.DEVNULL,
        )
        names = [item.decode() for item in output.split(b"\0") if item]
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
        names = sorted(EXPECTED_FILES)
    return {name: ROOT / name for name in names}


def high_information(block: bytes) -> bool:
    """Ignore padding and other low-information binary coincidences."""
    return len(set(block)) >= 8


def copied_blocks(candidate: bytes, original: bytes, width: int = 32):
    """Yield high-information candidate windows also present in original."""
    seen: set[bytes] = set()
    for offset in range(0, len(candidate) - width + 1):
        block = candidate[offset:offset + width]
        if block in seen or not high_information(block):
            continue
        seen.add(block)
        original_offset = original.find(block)
        if original_offset >= 0:
            yield offset, original_offset, block


def audit(original_path: Path | None) -> list[str]:
    errors: list[str] = []
    files = repository_files()
    names = set(files)

    missing = EXPECTED_FILES - names
    unexpected = names - EXPECTED_FILES
    if missing:
        errors.append("missing expected files: " + ", ".join(sorted(missing)))
    if unexpected:
        errors.append("unexpected tracked files: " + ", ".join(sorted(unexpected)))

    for name, path in files.items():
        upper_name = path.name.upper()
        if upper_name in FORBIDDEN_NAMES:
            errors.append(f"forbidden game/generated file: {name}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden archive/game-data format: {name}")
        if not path.is_file():
            errors.append(f"missing tracked file: {name}")
            continue
        data = path.read_bytes()
        if name != "ALADGUS.COM" and data.startswith(b"MZ"):
            errors.append(f"unexpected DOS/Windows executable: {name}")

    com = files.get("ALADGUS.COM")
    if com and com.is_file():
        digest = hashlib.sha256(com.read_bytes()).hexdigest()
        if digest != EXPECTED_COM_SHA256:
            errors.append(f"ALADGUS.COM checksum mismatch: {digest}")

    if original_path is not None:
        original = original_path.read_bytes()
        for name, path in files.items():
            if not path.is_file():
                continue
            matches = list(copied_blocks(path.read_bytes(), original))
            if matches:
                local, source, _ = matches[0]
                errors.append(
                    f"{name} shares a high-information 32-byte block with "
                    f"the original (file+0x{local:x}, original+0x{source:x})"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--original",
        type=Path,
        help="optionally compare against a legally obtained original executable",
    )
    args = parser.parse_args()
    errors = audit(args.original)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Repository content audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
