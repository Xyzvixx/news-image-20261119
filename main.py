#!/usr/bin/env python3
"""News-image entry for make.fun bounty news-image-20261119.

Writes the day's front-page image (entry.png, held in this repository) to
/output/entry.png. Python 3.13, standard library only, no network: the
program copies the image byte for byte, so two runs write identical bytes.

Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for /output:
    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import os
import struct
import sys
import zlib

IMAGE_NAME = "entry.png"
MAX_BYTES = 1048576  # 1 MiB
MAX_SIDE = 1024


def repo_image_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, IMAGE_NAME)


def verify_png(data):
    """Check the image is a whole PNG within the bounty limits."""
    if len(data) > MAX_BYTES:
        raise SystemExit(f"entry.png is {len(data)} bytes, over the 1 MiB limit")
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("entry.png is not a PNG (bad signature)")
    # Walk every chunk, checking its CRC, so a truncated file is refused.
    pos = 8
    saw_ihdr = saw_iend = False
    while pos < len(data):
        if pos + 8 > len(data):
            raise SystemExit("entry.png is truncated (short chunk header)")
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        end = pos + 12 + length
        if end > len(data):
            raise SystemExit("entry.png is truncated (short chunk body)")
        crc = zlib.crc32(data[pos + 4:end - 4]) & 0xFFFFFFFF
        if struct.unpack(">I", data[end - 4:end])[0] != crc:
            raise SystemExit(f"entry.png has a bad CRC in chunk {ctype!r}")
        if ctype == b"IHDR":
            width, height = struct.unpack(">II", data[pos + 8:pos + 16])
            if width > MAX_SIDE or height > MAX_SIDE:
                raise SystemExit(f"entry.png is {width}x{height}, over 1024x1024")
            saw_ihdr = True
        if ctype == b"IEND":
            saw_iend = True
            if end != len(data):
                raise SystemExit("entry.png has trailing bytes after IEND")
        pos = end
    if not saw_ihdr or not saw_iend:
        raise SystemExit("entry.png is missing IHDR or IEND")


def main():
    with open(repo_image_path(), "rb") as f:
        data = f.read()
    verify_png(data)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, IMAGE_NAME)
    with open(out_path, "wb") as f:
        f.write(data)
    # Read the output back: the grader runs the program twice and both
    # runs must write the same bytes, so confirm what landed on disk.
    with open(out_path, "rb") as f:
        written = f.read()
    if written != data:
        raise SystemExit(f"{out_path} does not match {IMAGE_NAME}")
    print(f"wrote {out_path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
