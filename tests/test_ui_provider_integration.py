"""Current production builder/Core -> snapshot -> UI; synthetic rows stay in tests."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_followup import runtime_with_data, synthetic_manifest, NOW
from tests.test_tools import load_tool


@pytest.mark.parametrize("locale", ["enUS", "deDE"])
@pytest.mark.parametrize("own", ["800", "nil"])
def test_pr26_pure_rating_snapshot_renders_without_personal(locale, own):
    lua = runtime_with_data()
    run(lua, 'GetLocale=function() return "'+locale+'" end; GetCombatRating=function() return '+own+' end')
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; local snapshot=a.Snapshot()
      for i,key in ipairs(a.statOrder) do
        local item=snapshot.ratingTarget[key]
        assert(item.sourceStatus=="verified" and item.personal==nil)
        a.Render(snapshot)
        local r=a.rows[i]
        assert(r.cachedTarget.target==item.targetRating, "PR26 cohort median must render")
        assert(r.cachedTarget.low==item.lowRating and r.cachedTarget.high==item.highRating)
        assert(r.markerTarget.shown and (r.band.shown or r.bandCue.shown) and r.axis==2000)
        assert(not r.cachedTarget.fallback)
        assert(not r.tip.target:find(a.Text("targetFallback",GetLocale()),1,true))
        assert(r.fill.shown==(item.currentRating~=nil))
      end
    ''')



def test_current_core_populates_quartiles_and_ui_preserves_observed_axis():
    manifest = synthetic_manifest()
    manifest["cohorts"][0]["mode"]="mythic"
    for row in manifest["cohorts"][0]["observations"]: row["mode"]="mythic"
    for i, row in enumerate(manifest['cohorts'][0]['observations'], 1):
        row['critRating'] = i * 10
    builder = load_tool('build_data')
    data = builder.checked(manifest, b'synthetic integration fixture', now=NOW)
    lua = load_runtime('GetCombatRating=function() return 800 end')
    run(lua, 'StatCompass.releaseData=' + builder.lua_value(data))
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; local snapshot=a.Snapshot()
      local item=snapshot.ratingComparison.crit
      assert(item.sourceStatus=="verified")
      assert(item.reference.lowRating==130 and item.reference.highRating==380)
      assert(item.reference.minRating==10 and item.reference.maxRating==500)
      assert(item.reference.meanRating==255)
      assert(item.axisMaxRating==900 and item.axisVerified)
      assert(item.axisProvenance:find("own rating",1,true))
      a.Render(snapshot)
      local r=a.rows[1]
      local target=snapshot.ratingTarget.crit
      assert(r.cachedTarget.target==target.targetRating)
      assert(r.cachedTarget.low==target.lowRating and r.cachedTarget.high==target.highRating)
      assert(r.band.shown and r.axis==2000)
      assert(math.abs(r.fill.width/r.barWidth-target.currentRating/r.axis)<0.001)
      r.bandHit.scripts.OnEnter(r.bandHit)
      assert(GameTooltip.text:find("P40–P60",1,true))
      assert(r.tip.target:find("Target percent",1,true))
    ''')


def test_metadata_without_reference_does_not_claim_technical_cap():
    for locale, forbidden in [('enUS', 'not a cap'), ('deDE', 'keine Grenze')]:
        lua=load_runtime('GetLocale=function() return "'+locale+'" end')
        run(lua, '''
          Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
          local a=StatCompass
          a.metadataHit.scripts.OnEnter(a.metadataHit)
          assert(GameTooltip.text:find("'''+forbidden+'''",1,true),"display scale is not a technical cap")
        ''')
