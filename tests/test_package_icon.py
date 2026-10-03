"""Icon inventory and source binding for local packaging."""
import json
from zipfile import ZipFile

import pytest

from tests.test_tools import load_tool


@pytest.mark.parametrize("mutation", ["omitted", "wrong-path", "tampered"])
def test_verify_rejects_icon_mutations_with_rehashed_manifest(tmp_path, monkeypatch, mutation):
    tool = load_tool("package")
    monkeypatch.setattr(tool, "DIST", tmp_path)
    monkeypatch.setattr(tool, "ARCHIVE", tmp_path / tool.ARCHIVE.name)
    monkeypatch.setattr(tool, "MANIFEST", tmp_path / tool.MANIFEST.name)
    tool.build()
    with ZipFile(tool.ARCHIVE) as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
    # Recompute all advertised hashes: rejection must bind to inventory/source,
    # not merely catch a stale checksum on the ZIP container.
    hashes = {}
    with ZipFile(tool.ARCHIVE, "w") as archive:
        for info, payload in entries:
            if info.filename == "StatCompass/icon.tga":
                if mutation == "omitted":
                    continue
                if mutation == "wrong-path":
                    info.filename = "StatCompass/assets/icon.tga"
                if mutation == "tampered":
                    payload = bytes([payload[0] ^ 1]) + payload[1:]
            archive.writestr(info, payload)
            hashes[info.filename] = tool.digest(payload)
    tool.MANIFEST.write_text(json.dumps({
        "archive": tool.ARCHIVE.name,
        "archiveSHA256": tool.digest(tool.ARCHIVE.read_bytes()),
        "files": hashes,
    }, sort_keys=True), encoding="utf-8")
    with pytest.raises(AssertionError):
        tool.verify()
