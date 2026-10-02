import copy
import hashlib
import importlib.util
from pathlib import Path
from zipfile import ZipFile
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_manifest():
    rows = [dict(rank=i, id=f"synthetic-{i}", region="EU", mode="raid", specID=71,
                 interface=120100, clientBuild=69933, level=90, unit="percentPoints",
                 semanticKind="masteryEffectPercent", observedAt=1799999000, crit=20, haste=15,
                 mastery=32, versatility=12, critRating=900, hasteRating=700, masteryRating=800,
                 versatilityRating=400) for i in range(1, 51)]
    return dict(interface=120100, clientBuild=69933, level=90, collectedAt=1800000000,
                observedAt=1799999000, expiresAt=1800001000,
                sourceURL="https://example.invalid/synthetic-test-only", permission="synthetic-test-only",
                cohorts=[dict(region="EU", mode="raid", specID=71, interface=120100,
                              clientBuild=69933, level=90, unit="percentPoints", semanticKind="masteryEffectPercent",
                              season="synthetic", rankingMetric="synthetic", difficulty="synthetic",
                              partition="synthetic", observedAt=1799999000, selectedCount=50,
                              validCount=50, observations=rows)])


def test_offline_data_builder_rejects_bad_units_and_counts():
    import pytest
    tool = load_tool("build_data")
    data = tool.checked(fixture_manifest(), b"synthetic test raw", now=1800000000)
    assert data["rawSHA256"] == hashlib.sha256(b"synthetic test raw").hexdigest()
    assert "[71]" in tool.lua_value(data)
    lua = LuaRuntime()
    lua.execute("StatCompass={}; StatCompass.releaseData=" + tool.lua_value(data))
    assert lua.eval("StatCompass.releaseData.cohorts[71].raid.observations[50].rank") == 50
    with pytest.raises(ValueError, match="control"):
        tool.lua_value("bad\u0000text")
    encoded = tool.lua_value('Ä "quoted"')
    assert LuaRuntime().eval(encoded) == 'Ä "quoted"'
    bad = copy.deepcopy(fixture_manifest())
    bad["cohorts"][0]["unit"] = "rating"
    bad["cohorts"][0]["observations"][0]["haste"] = 4000
    with pytest.raises(ValueError, match="ratings"):
        tool.checked(bad, b"synthetic", now=1800000000)
    bad = copy.deepcopy(fixture_manifest())
    bad["cohorts"][0]["validCount"] = 49
    with pytest.raises(ValueError, match="counts"):
        tool.checked(bad, b"synthetic", now=1800000000)
    small = copy.deepcopy(fixture_manifest())
    del small["cohorts"][0]["observations"][30:]
    small["cohorts"][0]["selectedCount"] = small["cohorts"][0]["validCount"] = 30
    assert tool.checked(small, b"synthetic", now=1800000000)["schema"] == 3
    del small["cohorts"][0]["observations"][19:]
    small["cohorts"][0]["selectedCount"] = small["cohorts"][0]["validCount"] = 19
    with pytest.raises(ValueError, match="20 to 50"):
        tool.checked(small, b"synthetic", now=1800000000)
    bad = copy.deepcopy(fixture_manifest())
    del bad["cohorts"][0]["observations"][0]["hasteRating"]
    with pytest.raises(ValueError, match="haste rating"):
        tool.checked(bad, b"synthetic", now=1800000000)


def test_package_exact_inventory_and_rebuild_identity():
    tool = load_tool("package")
    tool.build()
    first = tool.ARCHIVE.read_bytes()
    tool.build()
    assert first == tool.ARCHIVE.read_bytes()
    tool.verify()
    with ZipFile(tool.ARCHIVE) as archive:
        assert archive.namelist() == list(tool.FILES)
    toc = (ROOT / "StatCompass/StatCompass.toc").read_text(encoding="utf-8")
    toc_lua = ["StatCompass/" + line for line in toc.splitlines() if line and not line.startswith("##")]
    assert toc_lua == [name for name in tool.FILES if name.endswith(".lua")]
