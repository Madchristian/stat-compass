"""Runtime icon contract, using only stdlib decoding for the owned assets."""
import hashlib
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]


def test_readme_uses_repository_icon():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "![Stat Compass](assets/icon/stat-compass-128.png)" in readme
    assert (ROOT / "assets/icon/stat-compass-128.png").is_file()


def png_rgba(path):
    """Decode the source's non-interlaced RGBA PNG, including all row filters."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, compressed = 8, bytearray()
    while pos < len(data):
        size = struct.unpack_from(">I", data, pos)[0]
        kind, payload = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + size]
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            assert (depth, color, compression, filtering, interlace) == (8, 6, 0, 0, 0)
        elif kind == b"IDAT":
            compressed.extend(payload)
        pos += size + 12
    raw = zlib.decompress(compressed)
    stride = width * 4
    assert len(raw) == height * (stride + 1)
    previous, pixels = bytearray(stride), bytearray()
    for y in range(height):
        offset = y * (stride + 1)
        method = raw[offset]
        assert method in range(5)
        row = bytearray(raw[offset + 1:offset + 1 + stride])
        for x in range(stride):
            left = row[x - 4] if x >= 4 else 0
            above = previous[x]
            upper_left = previous[x - 4] if x >= 4 else 0
            prediction = left + above - upper_left
            paeth = min((left, above, upper_left), key=lambda value: abs(prediction - value))
            row[x] = (row[x] + (0, left, above, (left + above) // 2, paeth)[method]) % 256
        pixels.extend(row)
        previous = row
    return width, height, bytes(pixels)


def test_addon_list_icon_resolves_to_unchanged_rgba_asset():
    toc = (ROOT / "StatCompass/StatCompass.toc").read_text()
    assert r"## IconTexture: Interface\AddOns\StatCompass\icon" in toc.splitlines()
    shipped = ROOT / "StatCompass/icon.tga"
    assert shipped.is_file()
    data = shipped.read_bytes()
    source = (ROOT / "assets/icon/stat-compass-64.tga").read_bytes()
    assert hashlib.sha256(data).digest() == hashlib.sha256(source).digest()
    assert data == source
    # Uncompressed BGRA, top-left origin, eight attribute (alpha) bits.
    assert struct.unpack("<BBBHHBHHHHBB", data[:18]) == (0, 0, 2, 0, 0, 0, 0, 0, 64, 64, 32, 40)
    assert len(data) == 18 + 64 * 64 * 4
    rgba = bytes(channel for b, g, r, a in struct.iter_unpack("BBBB", data[18:]) for channel in (r, g, b, a))
    assert png_rgba(ROOT / "assets/icon/stat-compass-small-64.png") == (64, 64, rgba)
    alpha = rgba[3::4]
    assert min(alpha) == 0 and max(alpha) == 255
    assert any(0 < value < 255 for value in alpha)
    assert all(alpha[index] == 0 for index in (0, 63, 63 * 64, 64 * 64 - 1))
