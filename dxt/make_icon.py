"""Generate dxt/icon.png — a 256x256 app icon, pure stdlib (no Pillow).

A blue rounded square with a white invoice/document glyph and ledger lines.
Re-run with `python dxt/make_icon.py` to regenerate.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 256
BG = (31, 111, 235, 255)        # #1F6FEB Billit-ish blue
PAPER = (255, 255, 255, 255)
LINE = (203, 213, 225, 255)     # slate-300
ACCENT = (31, 111, 235, 255)    # header band matches bg


def rounded(x: int, y: int, x0: int, y0: int, x1: int, y1: int, r: int) -> bool:
    """True if (x,y) is inside the rounded rect [x0,y0]-[x1,y1] with radius r."""
    if not (x0 <= x < x1 and y0 <= y < y1):
        return False
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        in_corner_x = x < x0 + r if cx == x0 + r else x >= x1 - r
        in_corner_y = y < y0 + r if cy == y0 + r else y >= y1 - r
        if in_corner_x and in_corner_y:
            if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                return False
    return True


def build_pixels() -> list[list[tuple[int, int, int, int]]]:
    px = [[(0, 0, 0, 0) for _ in range(SIZE)] for _ in range(SIZE)]
    # Background rounded square
    for y in range(SIZE):
        for x in range(SIZE):
            if rounded(x, y, 0, 0, SIZE, SIZE, 48):
                px[y][x] = BG
    # Paper
    px0, py0, px1, py1 = 72, 48, 184, 208
    for y in range(SIZE):
        for x in range(SIZE):
            if rounded(x, y, px0, py0, px1, py1, 12):
                px[y][x] = PAPER
    # Header accent band
    for y in range(py0 + 14, py0 + 34):
        for x in range(px0 + 16, px1 - 16):
            if 0 <= y < SIZE:
                px[y][x] = ACCENT
    # Ledger lines
    for i in range(4):
        ly = py0 + 56 + i * 26
        for y in range(ly, ly + 8):
            for x in range(px0 + 16, px1 - 16 - (20 if i == 3 else 0)):
                if 0 <= y < SIZE:
                    px[y][x] = LINE
    return px


def encode_png(px: list[list[tuple[int, int, int, int]]]) -> bytes:
    raw = bytearray()
    for row in px:
        raw.append(0)  # filter type 0
        for r, g, b, a in row:
            raw += bytes((r, g, b, a))
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", comp)
        + chunk(b"IEND", b"")
    )


def main() -> None:
    out = Path(__file__).with_name("icon.png")
    out.write_bytes(encode_png(build_pixels()))
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
