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
    assert skipped == {71: "only 12 usable players"}
    assert [c["specID"] for c in data_manifest["cohorts"]] == [62, 250, 270]
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
    assert lua.eval('StatCompass.GetTarget(270, "mythic")').rating.mastery.max == 800  # Mistweaver ships


def test_stale_or_spread_observations_are_refused():
    tool = load_tool("blizzard_dataset")
    source = observations(**{"62": 25})
    source["specs"]["62"]["observations"][0]["observedAt"] = NOW - 3 * 86400
    with pytest.raises(ValueError, match="no cohort"):
        tool.manifest(source, interface=120100, client_build=69933, level=90, now=NOW)


def test_hero_cohorts_are_preferred_in_runtime():
    tool = load_tool("blizzard_dataset")
    build = load_tool("build_data")
    source = observations(**{"268": 30})
    rows = source["specs"]["268"]["observations"]
    for i, row in enumerate(rows):
        row["heroTree"] = {"id": 66, "name": "Master of Harmony"} if i < 27 else {"id": 65, "name": "Shado-Pan"}
    harmony = [dict(observation(i), heroTree={"id": 66, "name": "Master of Harmony"}, crit=40.0) for i in range(1, 31)]
    shado = [dict(observation(i), heroTree={"id": 65, "name": "Shado-Pan"}) for i in range(1, 6)]
    source["specs"]["268"]["heroes"] = {"66": {"name": "Master of Harmony", "observations": harmony},
                                        "65": {"name": "Shado-Pan", "observations": shado}}
    data_manifest, skipped = tool.manifest(source, interface=120100, client_build=69933, level=90, now=NOW)
    assert skipped == {"268/Shado-Pan": "only 5 usable players"}
    assert data_manifest["cohorts"][0]["heroMix"] == {"Master of Harmony": 27, "Shado-Pan": 3}
    data = build.checked(data_manifest, json.dumps(source).encode(), now=NOW)
    lua = LuaRuntime()
    lua.execute(f"""
      StatCompass = {{}}
      GetBuildInfo = function() return "12.1.0", "69933", "", 120100 end
      UnitLevel = function() return 90 end
      GetServerTime = function() return {NOW} end
    """)
    lua.execute((ROOT / "StatCompass/Core.lua").read_text(encoding="utf-8"))
    lua.execute("StatCompass.releaseData = " + build.lua_value(data))
    hero = lua.eval('StatCompass.GetTarget(268, "mythic", 66)')
    assert hero.heroTreeName == "Master of Harmony" and hero.crit == 40.0
    spec = lua.eval('StatCompass.GetTarget(268, "mythic", 65)')  # no Shado-Pan cohort: whole spec
    assert spec.heroTreeName is None and spec.heroMix["Shado-Pan"] == 3 and spec.crit < 40.0
    assert lua.eval('StatCompass.GetTarget(268, "mythic")').sample == 30
    lua.execute('StatCompass.releaseData.heroCohorts[268][66].mythic.heroTreeID = 65')
    assert lua.eval('StatCompass.GetTarget(268, "mythic", 66)') is None  # mismatched tree invalidates the dataset
    lua.execute('C_ClassTalents = {GetActiveHeroTalentSpec = function() return 66 end}')
    assert lua.eval('StatCompass.ReadHeroTree()') == 66
    lua.execute('C_ClassTalents.GetActiveHeroTalentSpec = function() error("unavailable") end')
    assert lua.eval('StatCompass.ReadHeroTree()') is None


def test_rating_comparison_feeds_the_bars():
    from tests.test_addon import load_runtime, run
    build = load_tool("build_data")
    tool = load_tool("blizzard_dataset")
    source = observations(**{"71": 30})
    data_manifest, _ = tool.manifest(source, interface=120100, client_build=69933, level=90, now=NOW)
    data = build.checked(data_manifest, b"synthetic", now=NOW)
    lua = load_runtime("""
      local ratings = {[9]=950, [10]=800, [11]=1000, [18]=700, [19]=700, [20]=700, [26]=746, [29]=2000}
      function GetCombatRating(id) return ratings[id] end
    """)
    run(lua, "StatCompass.releaseData=" + build.lua_value(data))
    run(lua, f"GetServerTime=function() return {NOW} end")
    run(lua, '''
      StatCompass.settings.mode = "mythic"
      local r = StatCompass.ReadRatings()
      assert(r.crit == 1000 and r.haste == 700 and r.mastery == 746 and r.versatility == 2000)
      local snap = StatCompass.Snapshot()
      local crit = snap.ratingComparison.crit
      assert(crit.currentRating == 1000 and crit.sourceStatus == "verified" and crit.axisVerified == true)
      assert(crit.reference.minRating == 901 and crit.reference.maxRating == 930 and crit.sampleCount == 30)
      assert(crit.reference.lowRating == 908 and crit.reference.highRating == 923)  -- ranks ceil(30/4)=8, ceil(90/4)=23
      assert(crit.axisMaxRating == 1100)                 -- own 1000 beats cohort 930: 1000 * 1.1
      assert(snap.ratingComparison.haste.axisMaxRating == 800)   -- cohort 700 * 1.1 = 770 -> 800
      assert(snap.ratingComparison.versatility.axisMaxRating == 2200)
      assert(crit.axisProvenance:find("top 30"))
      -- no cohort: only the own rating, nothing that could draw a reference
      local empty = StatCompass.RatingComparison(nil, r)
      assert(empty.crit.currentRating == 1000 and empty.crit.sourceStatus == "unavailable" and empty.crit.axisMaxRating == nil)
      GetCombatRating = function() error("unavailable") end
      assert(StatCompass.ReadRatings().crit == nil)
    ''')


def test_share_comparison_ignores_gear_level():
    from tests.test_addon import load_runtime, run
    build = load_tool("build_data")
    tool = load_tool("blizzard_dataset")
    source = observations(**{"71": 30})
    for i, row in enumerate(source["specs"]["71"]["observations"]):
        scale = 1 + i / 10  # same split, very different budgets (item levels)
        row["ratings"] = {"crit": 400 * scale, "haste": 300 * scale, "mastery": 200 * scale, "versatility": 100 * scale}
    data_manifest, _ = tool.manifest(source, interface=120100, client_build=69933, level=90, now=NOW)
    data = build.checked(data_manifest, b"synthetic", now=NOW)
    lua = load_runtime("""
      local ratings = {[9]=200, [10]=200, [11]=200, [18]=150, [19]=150, [20]=150, [26]=100, [29]=50}
      function GetCombatRating(id) return ratings[id] end
    """)
    run(lua, "StatCompass.releaseData=" + build.lua_value(data))
    run(lua, f"GetServerTime=function() return {NOW} end")
    run(lua, '''
      StatCompass.settings.mode = "mythic"
      local t = StatCompass.GetTarget(71, "mythic")
      local function near(a, b) return math.abs(a - b) < 1e-9 end
      assert(near(t.share.crit.min, 40) and near(t.share.crit.max, 40) and near(t.share.versatility.mean, 10))
      assert(t.rating.crit.max > 3 * t.rating.crit.min)          -- ratings spread with gear level ...
      local snap = StatCompass.Snapshot()
      local crit = snap.shareComparison.crit                      -- ... shares do not
      assert(near(crit.currentShare, 40) and near(crit.reference.lowShare, 40) and crit.sourceStatus == "verified")
      assert(crit.axisMaxShare == 45 and crit.sampleCount == 30)  -- 40 * 1.1 = 44 -> 45
      assert(near(snap.shareComparison.versatility.currentShare, 10))
      GetCombatRating = function(id) if id == 26 then return nil end return 100 end
      local partial = StatCompass.ShareComparison(t, StatCompass.ReadRatings())
      assert(partial.crit.currentShare == nil and partial.crit.reference)  -- no own share without all four
    ''')



def test_personal_rating_targets_use_own_conversion():
    from tests.test_addon import load_runtime, run
    build = load_tool("build_data")
    tool = load_tool("blizzard_dataset")
    source = observations(**{"71": 30})   # crit 20.1 .. 23.0 %, mastery 30 %, versatility 5 %, haste rating 700
    data_manifest, _ = tool.manifest(source, interface=120100, client_build=69933, level=90, now=NOW)
    data = build.checked(data_manifest, b"synthetic", now=NOW)
    lua = load_runtime("""
      local bonus = {[9]=8, [10]=8, [11]=8, [18]=0, [19]=0, [20]=0, [26]=10, [29]=5}
      function GetCombatRatingBonus(id) return bonus[id] end
    """)
    run(lua, "StatCompass.releaseData=" + build.lua_value(data))
    run(lua, f"GetServerTime=function() return {NOW} end")
    run(lua, """
      GetMasteryEffect = function() return 30, 1.5 end      -- 10 points from rating * 1.5 = 15 % from rating
      local function near(a, b) return math.abs(a - b) < 1e-9 end
      local t = StatCompass.GetTarget(71, "mythic")
      assert(near(t.pct.crit.median, 21.5) and near(t.pct.crit.low, 21.2) and near(t.pct.crit.high, 21.8))  -- ranks 15, 12, 18
      local current = {crit=18, haste=10, mastery=30, versatility=5}
      local ratings = {crit=400, haste=300, mastery=500, versatility=250}
      local r = StatCompass.RatingTargets(t, ratings, current)
      -- crit: 8 % from 400 rating -> 0.02 %/rating, base 10 %; median 21.5 % needs 575 rating
      assert(r.crit.personal and near(r.crit.targetRating, 575) and near(r.crit.lowRating, 560) and near(r.crit.highRating, 590))
      assert(r.crit.currentRating == 400 and near(r.crit.targetPercent, 21.5) and r.crit.sampleCount == 30)
      -- mastery: base 15 %, 0.03 %/rating; cohort 30 % -> 500
      assert(r.mastery.personal and near(r.mastery.targetRating, 500))
      -- haste: no readable bonus -> the cohort's own median rating stands in
      assert(r.haste.personal == false and r.haste.targetRating == 700)
      assert(near(r.totals.targetRating, 575 + 700 + 500 + 250) and r.totals.ownRating == 1450)
      -- above the target percent the need never goes negative
      local rich = StatCompass.RatingTargets(t, ratings, {crit=60, haste=10, mastery=30, versatility=5})
      assert(rich.crit.targetRating == 0)
      -- no cohort: nothing to aim at, but the own rating stays
      local none = StatCompass.RatingTargets(nil, ratings, current)
      assert(none.crit.sourceStatus == "unavailable" and none.crit.currentRating == 400 and none.totals.targetRating == nil)
      GetMasteryEffect = function() error("unavailable") end
      assert(StatCompass.RatingTargets(t, ratings, current).mastery.personal == false)
      -- the snapshot carries the targets
      StatCompass.settings.mode = "mythic"
      assert(StatCompass.Snapshot().ratingTarget.totals)
    """)


def test_priority_follows_the_cohorts_budget_shares():
    build = load_tool("build_data")
    tool = load_tool("blizzard_dataset")
    source = observations(**{"104": 30})
    for row in source["specs"]["104"]["observations"]:
        row["ratings"] = {"crit": 900, "haste": 1200, "mastery": 450, "versatility": 400}  # Guardian-like split
    data_manifest, _ = tool.manifest(source, interface=120100, client_build=69933, level=90, now=NOW)
    data = build.checked(data_manifest, b"synthetic", now=NOW)
    lua = LuaRuntime()
    lua.execute(f"""
      StatCompass = {{}}
      GetBuildInfo = function() return "12.1.0", "69933", "", 120100 end
      UnitLevel = function() return 90 end
      GetServerTime = function() return {NOW} end
    """)
    lua.execute((ROOT / "StatCompass/Core.lua").read_text(encoding="utf-8"))
    lua.execute("StatCompass.releaseData = " + build.lua_value(data))
    target = lua.eval('StatCompass.GetTarget(104, "mythic")')
    assert [target.priority[i] for i in range(1, 5)] == ["haste", "crit", "mastery", "versatility"]
    assert round(target.share.haste.median, 1) == 40.7
    # equal shares keep the Character-window order
    for row in source["specs"]["104"]["observations"]:
        row["ratings"] = {"crit": 500, "haste": 500, "mastery": 500, "versatility": 500}
    data = build.checked(tool.manifest(source, interface=120100, client_build=69933, level=90, now=NOW)[0],
                         b"synthetic", now=NOW)
    lua.execute("StatCompass.releaseData = " + build.lua_value(data))
    tied = lua.eval('StatCompass.GetTarget(104, "mythic")').priority
    assert [tied[i] for i in range(1, 5)] == ["crit", "haste", "mastery", "versatility"]
