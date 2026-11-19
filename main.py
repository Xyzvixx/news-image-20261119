#!/usr/bin/env python3
"""Validate and copy the news-image entry PNG.

Reads ``entry.png`` sitting next to this script, validates it strictly
as a PNG (signature, per-chunk CRCs, IHDR dimensions of at most
1024x1024, a terminating IEND chunk with nothing after it), then copies
the bytes verbatim to ``<output-dir>/entry.png`` and re-reads the copy
to prove it is byte-identical to the source.

Usage:
    python3 main.py [output-dir]

The output directory defaults to ``/output``. Only the Python standard
library is used; there is no network access and the output is fully
deterministic.
"""

from __future__ import annotations

import hashlib
import struct
import sys
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_DIMENSION = 1024


class ValidationError(ValueError):
    """Raised when entry.png fails strict PNG validation."""


def validate_png(data: bytes) -> tuple[int, int]:
    """Check *data* is a well-formed PNG; return (width, height)."""
    if len(data) < len(PNG_SIGNATURE) or data[:8] != PNG_SIGNATURE:
        raise ValidationError("missing or incorrect PNG signature")

    offset = 8
    first_chunk = True
    width = 0
    height = 0

    while True:
        if offset + 8 > len(data):
            raise ValidationError("truncated chunk header")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        offset += 8
        if offset + length + 4 > len(data):
            raise ValidationError("truncated chunk body")
        chunk_data = data[offset:offset + length]
        offset += length
        stored_crc = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            raise ValidationError(
                "CRC mismatch in chunk " + chunk_type.decode("latin-1")
            )

        if first_chunk:
            if chunk_type != b"IHDR":
                raise ValidationError("first chunk must be IHDR")
            if len(chunk_data) != 13:
                raise ValidationError("IHDR chunk must be 13 bytes long")
            width, height = struct.unpack(">II", chunk_data[:8])
            if width == 0 or height == 0:
                raise ValidationError("IHDR dimensions must be positive")
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                raise ValidationError(
                    f"dimensions {width}x{height} exceed "
                    f"{MAX_DIMENSION}px limit"
                )
            first_chunk = False
        elif chunk_type == b"IHDR":
            raise ValidationError("duplicate IHDR chunk")

        if chunk_type == b"IEND":
            if len(chunk_data) != 0:
                raise ValidationError("IEND chunk must be empty")
            if offset != len(data):
                raise ValidationError("trailing bytes after IEND chunk")
            return width, height


def run(argv: list[str]) -> int:
    """Entry point; returns a process exit code."""
    if len(argv) > 2:
        print("usage: main.py [output-dir]", file=sys.stderr)
        return 2

    source = Path(__file__).resolve().parent / "entry.png"
    output_dir = Path(argv[1]) if len(argv) == 2 else Path("/output")

    try:
        raw = source.read_bytes()
    except OSError as exc:
        print(f"error: cannot read {source}: {exc}", file=sys.stderr)
        return 1

    try:
        width, height = validate_png(raw)
    except ValidationError as exc:
        print(f"error: invalid entry.png: {exc}", file=sys.stderr)
        return 1

    target = output_dir / "entry.png"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        copied = target.read_bytes()
    except OSError as exc:
        print(f"error: cannot write {target}: {exc}", file=sys.stderr)
        return 1

    if copied != raw:
        print("error: copied bytes differ from source", file=sys.stderr)
        return 1

    digest = hashlib.sha256(copied).hexdigest()
    print(f"ok: {width}x{height}, {len(raw)} bytes, sha256={digest} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv))
