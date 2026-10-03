"""Create and verify a deterministic Stat Compass addon archive."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "StatCompass/StatCompass.toc",
    "StatCompass/Locales.lua",
    "StatCompass/Data.lua",
    "StatCompass/Core.lua",
    "StatCompass/UI.lua",
    "StatCompass/Controls.lua",
    "StatCompass/icon.tga",
    "StatCompass/LICENSE.txt",
    "StatCompass/NOTICE.txt",
    "StatCompass/README.txt",
    "StatCompass/README.de.txt",
)
DIST = ROOT / "dist"
ARCHIVE = DIST / "StatCompass-0.1.0.zip"
MANIFEST = DIST / "StatCompass-0.1.0.sha256.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build():
    DIST.mkdir(exist_ok=True)
    hashes = {}
    with ZipFile(ARCHIVE, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            data = (ROOT / name).read_bytes()
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 3
            archive.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
            hashes[name] = digest(data)
    manifest = {"archive": ARCHIVE.name, "archiveSHA256": digest(ARCHIVE.read_bytes()), "files": hashes}
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verify()
    print(manifest["archiveSHA256"])


def verify():
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    toc = (ROOT / "StatCompass/StatCompass.toc").read_text(encoding="utf-8")
    toc_lua = ["StatCompass/" + line for line in toc.splitlines() if line and not line.startswith("##")]
    assert toc_lua == [name for name in FILES if name.endswith(".lua")]
    assert expected["archive"] == ARCHIVE.name
    assert digest(ARCHIVE.read_bytes()) == expected["archiveSHA256"]
    assert list(expected["files"]) == sorted(FILES)
    with ZipFile(ARCHIVE) as archive:
        assert archive.namelist() == list(FILES)
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.filename in FILES
            payload = archive.read(info.filename)
            assert digest(payload) == expected["files"][info.filename]
            assert digest((ROOT / info.filename).read_bytes()) == expected["files"][info.filename]
    print("verified", len(FILES), "files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    verify() if args.verify else build()
