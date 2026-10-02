"""Regression-first checks for release policy, provenance, and panel behavior.

All cohorts here are synthetic test fixtures and never ship in Data.lua.
"""
import copy
import pytest
from tests.test_addon import load_runtime, run
from tests.test_tools import load_tool

NOW = 1800000000


def synthetic_manifest():
    rows = [dict(rank=i, id=f"synthetic-{i}", region="EU", mode="raid", specID=71,
                 interface=120100, clientBuild=69933, level=90, unit="percentPoints",
                 semanticKind="masteryEffectPercent", observedAt=NOW-1000,
                 crit=25, haste=30, mastery=199, versatility=12, critRating=900, hasteRating=700,
                 masteryRating=800, versatilityRating=400) for i in range(1, 51)]
    cohort = dict(region="EU", mode="raid", specID=71, interface=120100,
                  clientBuild=69933, level=90, unit="percentPoints",
                  semanticKind="masteryEffectPercent", season="synthetic-season",
                  rankingMetric="synthetic-dps", difficulty="synthetic-mythic",
                  partition="synthetic-partition", selectedCount=50, validCount=50,
                  observedAt=NOW-1000, observations=rows)
    return dict(interface=120100, clientBuild=69933, level=90,
                collectedAt=NOW, observedAt=NOW-1000, expiresAt=NOW+1000,
                sourceURL="https://example.invalid/synthetic", permission="synthetic-test-only",
                cohorts=[cohort])


def runtime_with_data(locale=None):
    builder = load_tool("build_data")
    data = builder.checked(synthetic_manifest(), b"synthetic raw", now=NOW)
    lua = load_runtime('GetLocale=function() return "deDE" end' if locale == "deDE" else "")
    run(lua, "StatCompass.releaseData=" + builder.lua_value(data))
    run(lua, f"GetServerTime=function() return {NOW} end")
    return lua


def test_expiry_and_build_fail_closed():
    lua = runtime_with_data()
    run(lua, f'''
      assert(StatCompass.GetTarget(71,"raid").mastery==199)
      GetBuildInfo=function() return "12.1.0","69934","synthetic",120100 end
      assert(StatCompass.GetTarget(71,"raid")==nil)
      GetBuildInfo=function() return "12.1.0","69933","synthetic",120100 end
      GetServerTime=function() return {NOW+1000} end
      assert(StatCompass.GetTarget(71,"raid")==nil) -- expiry boundary
      GetServerTime=function() return {NOW-1} end
      assert(StatCompass.GetTarget(71,"raid")==nil) -- future collection
      GetServerTime=nil
      assert(StatCompass.GetTarget(71,"raid")==nil)
      GetServerTime=function() return math.huge end
      assert(StatCompass.GetTarget(71,"raid")==nil)
      GetServerTime=function() return {NOW} end
      StatCompass.releaseData.observedAt={NOW+1}
      assert(StatCompass.GetTarget(71,"raid")==nil)
    ''')


def test_manifest_rejects_mastery_points_hash_and_future_policy():
    builder = load_tool("build_data")
    manifest = synthetic_manifest()
    assert builder.checked(manifest, b"synthetic raw", now=NOW)["clientBuild"] == 69933
    bad = copy.deepcopy(manifest)
    bad["cohorts"][0]["semanticKind"] = "masteryPoints"
    with pytest.raises(ValueError): builder.checked(bad, b"synthetic", now=NOW)
    bad = copy.deepcopy(manifest)
    bad["expiresAt"] = bad["collectedAt"] + 31*86400
    with pytest.raises(ValueError): builder.checked(bad, b"synthetic", now=NOW)
    bad = copy.deepcopy(manifest)
    bad["sourceURL"] += "\u0000"
    with pytest.raises(ValueError): builder.checked(bad, b"synthetic", now=NOW)
    lua = runtime_with_data()
    run(lua, '''
      local secret=setmetatable({secret=true},{__eq=function() error("secret equality") end,__index=function() error("secret index") end})
      assert(StatCompass.GetTarget(secret,"raid")==nil)
      assert(StatCompass.GetTarget(71,secret)==nil)
      StatCompass.releaseData.rawSHA256="bad"
      assert(StatCompass.GetTarget(71,"raid")==nil)
      StatCompass.releaseData.rawSHA256=string.rep("a",64)
      StatCompass.releaseData.cohorts[71].raid.semanticKind="masteryPoints"
      assert(StatCompass.GetTarget(71,"raid")==nil)
    ''')


def test_panel_columns_spec_tooltip_skin_and_clamp():
    lua = runtime_with_data()
    run(lua, r'''
      Fire("PLAYER_LOGIN")
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.spec.text:find("71"))
      assert(StatCompass.headers.current.text=="Current")
      assert(StatCompass.headers.target.text:find("Rating"))
      assert(StatCompass.rows[3].min.text:find("800") and StatCompass.rows[3].max.text:find("800"))  -- cohort mastery rating
      assert(StatCompass.rows[3].tip.mean:find("Cohort average"))
      assert(StatCompass.panel.mouseEnabled==false)
      StatCompass.metadataHit.scripts.OnEnter(StatCompass.metadataHit)
      assert(GameTooltip.shown and GameTooltip.text==StatCompass.metadataText)
      StatCompass.metadataHit.scripts.OnLeave(StatCompass.metadataHit)
      assert(not GameTooltip.shown)
      assert(StatCompass.metadataText:find("synthetic%-season"))
      assert(StatCompass.metadataText:find("Selected: 50"))
      assert(StatCompass.metadataText:find("Expires:"))
      assert(StatCompass.panel.border.texture==[[Interface\Buttons\WHITE8X8]] and StatCompass.panel.border.color[1]==0.55)
      StatCompass.buttons[4].scripts.OnClick(StatCompass.buttons[4])
      assert(StatCompass.panel.border.texture==[[Interface\Buttons\WHITE8X8]])
      assert(StatCompass.buttons[4].selected==true)
      assert(StatCompass.buttons[4].bg.color[1]~=StatCompass.buttons[3].bg.color[1])
      StatCompass.buttons[4].scripts.OnEnter(StatCompass.buttons[4])
      assert(StatCompass.buttons[4].hover.shown==true)
      StatCompass.buttons[4].scripts.OnLeave(StatCompass.buttons[4])
      assert(StatCompass.buttons[4].hover.shown==false)
      StatCompass.buttons[3].scripts.OnClick(StatCompass.buttons[3])
      assert(StatCompass.panel.border.texture==[[Interface\Buttons\WHITE8X8]] and StatCompass.panel.border.color[1]==0.55)
      assert(StatCompass.panel.point[2]==CharacterFrame and StatCompass.panel.point[1]=="TOPLEFT")
      CharacterFrame.right=1800
      PaperDollFrame:Hide(); PaperDollFrame:Show()
      assert(StatCompass.panel.point[1]=="TOPRIGHT")
      UIParent.right=600
      CharacterFrame.right=400
      CharacterFrame.left=200
      PaperDollFrame:Hide(); PaperDollFrame:Show()
      assert(StatCompass.panel.point[2]==UIParent)
      StatCompass.buttons[2].scripts.OnClick(StatCompass.buttons[2])
      assert(StatCompassDB.mode=="mythic" and StatCompass.buttons[2].selected)
      RunCallbacks()
      assert(StatCompass.status.text==StatCompass.Text("noData","enUS"))
      StatCompass.buttons[5].scripts.OnClick(StatCompass.buttons[5])
      assert(StatCompassDB.mode=="raid" and StatCompassDB.skin=="default")
    ''')


def test_hidden_skin_and_parent_close_no_render_or_frame_growth():
    lua = runtime_with_data()
    run(lua, r'''
      local reads,renders=0,0
      GetHaste=function() reads=reads+1; return 30 end
      local original=StatCompass.Render
      StatCompass.Render=function(s) renders=renders+1; original(s) end
      Fire("PLAYER_LOGIN")
      local before=StatCompass.panel.bg.texture
      StatCompass.SetSkin("flat")
      assert(reads==0 and renders==0 and StatCompass.panel.bg.texture==before)
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(reads==1 and renders==1)
      assert(StatCompass.panel.bg.texture==[[Interface\Buttons\WHITE8X8]])
      local frames=widgets.frames
      StatCompass.SetSkin("default")
      assert(reads==1 and renders==1)
      CharacterFrame:Hide()
      Fire("COMBAT_RATING_UPDATE")
      assert(reads==1 and renders==1)
      CharacterFrame:Show()
      assert(reads==2 and renders==2 and widgets.frames==frames)
    ''')


def test_de_locale_column_bounds_and_lazy_attach():
    lua = runtime_with_data("deDE")
    run(lua, '''
      for i=1,50 do StatCompass.releaseData.cohorts[71].raid.observations[i].mastery=999.9 end
      GetMasteryEffect=function() return 999.9 end
      Fire("PLAYER_LOGIN")
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.headers.current.text=="Aktuell")
      for i=1,4 do
        local row=StatCompass.rows[i]
        assert(row.label:GetStringWidth() <= row.label.width)
        assert(row.current:GetStringWidth() <= row.current.width)
        assert(row.min:GetStringWidth() <= row.min.width)
        assert(row.max:GetStringWidth() <= row.max.width)
        assert(row.label.point[4]+row.label.width <= row.current.point[4])
        assert(row.min.point[4]+row.min.width < row.max.point[4])
      end
      assert(StatCompass.status:GetStringWidth() <= StatCompass.status.width)
    ''')
    lazy = load_runtime('CharacterFrame=nil; PaperDollFrame=nil; StatCompassDB={mode="mythic",skin="flat"}')
    run(lazy, '''
      Fire("PLAYER_LOGIN")
      assert(StatCompass.panel==nil and StatCompassDB.mode=="mythic")
      CharacterFrame=CreateFrame("Frame","CharacterFrame")
      PaperDollFrame=CreateFrame("Frame","PaperDollFrame",CharacterFrame)
      Fire("ADDON_LOADED","Blizzard_UIPanels_Game")
      assert(StatCompass.panel and StatCompass.settings.skin=="flat")
      local frames=widgets.frames
      Fire("ADDON_LOADED","another-addon")
      assert(widgets.frames==frames)
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.visible)
    ''')


def test_secret_api_returns_and_all_relevant_events():
    lua = runtime_with_data()
    run(lua, '''
      local secret=setmetatable({secret=true},{__eq=function() error("secret compared") end,__index=function() error("secret indexed") end})
      Fire("PLAYER_LOGIN")
      CharacterFrame:Show(); PaperDollFrame:Show()
      for _,event in ipairs({"COMBAT_RATING_UPDATE","PLAYER_EQUIPMENT_CHANGED","MASTERY_UPDATE","UNIT_SPELL_HASTE","UNIT_STATS","UNIT_AURA","PLAYER_SPECIALIZATION_CHANGED","ACTIVE_TALENT_GROUP_CHANGED","PLAYER_TALENT_UPDATE","UNIT_LEVEL"}) do
        Fire(event,"player")
      end
      assert(#widgets.callbacks==1)
      RunCallbacks()
      GetServerTime=function() return secret end
      assert(StatCompass.GetTarget(71,"raid")==nil)
      GetBuildInfo=function() return "12.1.0",secret,"synthetic",120100 end
      assert(StatCompass.GetTarget(71,"raid")==nil)
      C_SpecializationInfo.GetSpecializationInfo=function() return secret,secret end
      assert(StatCompass.ReadSpecInfo()==nil)
      C_SpecializationInfo.GetSpecializationInfo=function() return 71,secret end
      local id,name=StatCompass.ReadSpecInfo()
      assert(id==71 and name==nil)
      GetBuildInfo=function() return "12.1.0","69933","synthetic",120100 end
      GetServerTime=function() return 1800000000 end
      StatCompass.releaseData.cohorts[71].raid.observations[1].mastery=secret
      assert(StatCompass.GetTarget(71,"raid")==nil)
      StatCompass.releaseData.cohorts[71].raid.observations[1].mastery=199
      StatCompass.releaseData.cohorts[71].raid.season=secret
      assert(StatCompass.GetTarget(71,"raid")==nil)
      CharacterFrame.GetRight=function() return secret end
      PaperDollFrame:Hide(); PaperDollFrame:Show()
    ''')
    locale = load_runtime('GetLocale=function() return {secret=true} end')
    run(locale, '''
      Fire("PLAYER_LOGIN")
      assert(StatCompass.headers.current.text=="Current")
    ''')
