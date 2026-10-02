"""Current production builder/Core -> snapshot -> UI; synthetic rows stay in tests."""
from tests.test_addon import load_runtime, run
from tests.test_followup import synthetic_manifest, NOW
from tests.test_tools import load_tool


def test_current_core_populates_quartiles_and_ui_preserves_observed_axis():
    manifest = synthetic_manifest()
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
      assert(r.cachedRating.bounds.low==130 and r.cachedRating.bounds.high==380,"Core quartiles must reach UI")
      assert(r.band.shown and r.axis==item.axisMaxRating)
      assert(math.abs(r.fill.width/r.barWidth-800/900)<0.001)
      r.bandHit.scripts.OnEnter(r.bandHit)
      assert(GameTooltip.text=="Middle 50 % of top players: 130 – 380")
    ''')


def test_metadata_without_reference_does_not_claim_technical_cap():
    for locale, forbidden in [('enUS', 'cap'), ('deDE', 'Wertungsgrenze')]:
        lua=load_runtime('GetLocale=function() return "'+locale+'" end')
        run(lua, '''
          Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
          local a=StatCompass
          a.metadataHit.scripts.OnEnter(a.metadataHit)
          assert(not GameTooltip.text:find("'''+forbidden+'''",1,true),"display scale is not a technical cap")
        ''')
