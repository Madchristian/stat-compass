"""Synthetic observations through the Data.lua generator; no player identities exist in the input."""
import json

import pytest
from lupa.lua51 import LuaRuntime

from tests.test_tools import ROOT, load_tool

NOW = 1800000000
VERSIONS = """Region!STRING:0|BuildConfig!HEX:16|CDNConfig!HEX:16|KeyRing!HEX:16|BuildId!DEC:4|VersionsName!String:0|ProductConfig!HEX:16
## seqn = 1
us|a|b|c|69933|12.1.0.69933|d
eu|a|b|c|69933|12.1.0.69933|d
"""


def observation(i, observed=NOW - 600):
    return {"rank": i, "score": 4000 - i, "exact": True, "crit": 20.0 + i / 10, "haste": 15.0, "mastery": 30.0,
            "versatility": 5.0, "ratings": {"crit": 900 + i, "haste": 700, "mastery": 800, "versatility": 250},
            "itemLevel": 330, "hasteSpread": 0.0, "observedAt": observed}


def observations(**counts):
    return {"season": 18, "periods": [1076, 1083], "generatedAt": "synthetic", "rankingMetric": "synthetic metric",
            "specs": {str(spec): {"certification": {}, "observations": [observation(i) for i in range(1, n + 1)]}
                      for spec, n in counts.items()}}


def test_versions_table_maps_to_interface_and_build():
    tool = load_tool("blizzard_dataset")
    assert tool.parse_versions(VERSIONS) == (120100, 69933)
    with pytest.raises(ValueError, match="missing"):
        tool.parse_versions(VERSIONS, region="kr")


def test_generated_dataset_validates_in_runtime():
    tool = load_tool("blizzard_dataset")
    build = load_tool("build_data")
    source = observations(**{"62": 30, "250": 35, "270": 30, "71": 12})
    data_manifest, skipped = tool.manifest(source, interface=120100, client_build=69933, level=90, now=NOW)
    assert skipped == {270: "mastery value is not a percentage", 71: "only 12 usable players"}
    assert [c["specID"] for c in data_manifest["cohorts"]] == [62, 250]
    assert all(c["selectedCount"] == 30 for c in data_manifest["cohorts"])  # capped at 30
    assert data_manifest["expiresAt"] == NOW - 600 + 30 * 86400
    raw = json.dumps(source).encode()
    data = build.checked(data_manifest, raw, now=NOW)
    text = build.lua_value(data)
    assert "Synthetic" not in text and data["cohorts"][62]["mythic"]["observations"][0]["id"] == "62-1"
    lua = LuaRuntime()
    lua.execute(f"""
      StatCompass = {{}}
      GetBuildInfo = function() return "12.1.0", "69933", "", 120100 end
      UnitLevel = function() return 90 end
      GetServerTime = function() return {NOW} end
    """)
    lua.execute((ROOT / "StatCompass/Core.lua").read_text(encoding="utf-8"))
    lua.execute("StatCompass.releaseData = " + text)
    target = lua.eval('StatCompass.GetTarget(62, "mythic")')
    assert target.sample == 30 and target.rating.crit.min == 901 and target.rating.crit.max == 930
    assert abs(target.range.crit.max - 23.0) < 1e-9
    assert lua.eval('StatCompass.GetTarget(270, "mythic")') is None


def test_stale_or_spread_observations_are_refused():
    tool = load_tool("blizzard_dataset")
    source = observations(**{"62": 25})
    source["specs"]["62"]["observations"][0]["observedAt"] = NOW - 3 * 86400
    with pytest.raises(ValueError, match="no cohort"):
        tool.manifest(source, interface=120100, client_build=69933, level=90, now=NOW)
