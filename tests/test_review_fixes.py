"""Bounded review regressions using synthetic data only."""
import copy
import pytest
from tests.test_addon import load_runtime, run
from tests.test_followup import synthetic_manifest, NOW
from tests.test_tools import load_tool


def runtime_with_manifest(manifest):
    builder = load_tool("build_data")
    data = builder.checked(manifest, b"synthetic review fixture", now=NOW)
    lua = load_runtime()
    run(lua, "StatCompass.releaseData=" + builder.lua_value(data))
    return lua


def test_effective_ancestor_visibility_suppresses_work_and_refreshes_on_restore():
    lua = load_runtime()
    run(lua, '''
      local reads,renders=0,0
      GetHaste=function() reads=reads+1; return 15 end
      local original=StatCompass.Render
      StatCompass.Render=function(snapshot) renders=renders+1; original(snapshot) end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(reads==1 and renders==1 and StatCompass.panel:IsVisible())
      UIParent:Hide()
      assert(CharacterFrame:IsShown() and not StatCompass.panel:IsVisible())
      Fire("COMBAT_RATING_UPDATE"); RunCallbacks()
      assert(reads==1 and renders==1)
      UIParent:Show()
      assert(reads==2 and renders==2 and StatCompass.panel:IsVisible())
    ''')


def test_large_finite_percentages_have_finite_mean_and_bounded_text():
    manifest = synthetic_manifest()
    for row in manifest["cohorts"][0]["observations"]:
        row["haste"] = 1e308
    lua = runtime_with_manifest(manifest)
    run(lua, '''
      local target=StatCompass.GetTarget(71,"raid")
      assert(target and target.haste==1e308 and target.haste<math.huge)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(#StatCompass.rows[2].target.text <= 40)
      assert(not StatCompass.rows[2].target.text:find("inf"))
    ''')


def test_visible_target_expires_once_and_old_lifecycle_timer_cannot_render():
    lua = runtime_with_manifest(synthetic_manifest())
    run(lua, '''
      local now=1800000000
      GetServerTime=function() return now end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(#widgets.timers==1 and widgets.timers[1].delay==1000)
      Fire("COMBAT_RATING_UPDATE"); RunCallbacks()
      assert(#widgets.timers==1)
      local old=widgets.timers[1].fn
      now=1800001000
      old()
      assert(StatCompass.status.text==StatCompass.Text("shareNoData","enUS"))
      assert(#widgets.timers==1) -- no recurring timer
      PaperDollFrame:Hide()
      now=1800000000
      PaperDollFrame:Show()
      local stale=widgets.timers[2].fn
      PaperDollFrame:Hide()
      local shown=StatCompass.status.text
      now=1800001000
      stale()
      assert(StatCompass.status.text==shown)
      PaperDollFrame:Show()
      assert(StatCompass.status.text==StatCompass.Text("shareNoData","enUS"))
    ''')


def test_expiry_timer_is_replaced_on_context_data_refresh_and_unknown_clock():
    lua = runtime_with_manifest(synthetic_manifest())
    run(lua, '''
      local now=1800000000
      GetServerTime=function() return now end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local old=widgets.timers[1].fn
      StatCompass.SetMode("mythic"); RunCallbacks()
      local before=StatCompass.status.text
      old()
      assert(StatCompass.status.text==before)
      StatCompass.SetMode("raid"); RunCallbacks()
      local oldDataTimer=widgets.timers[2].fn
      StatCompass.releaseData={}
      Fire("COMBAT_RATING_UPDATE"); RunCallbacks()
      oldDataTimer()
      assert(StatCompass.status.text==StatCompass.Text("shareNoData","enUS"))
    ''')
    lua = runtime_with_manifest(synthetic_manifest())
    run(lua, '''
      local clock=1800000000
      GetServerTime=function() return clock end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local expiry=widgets.timers[1].fn
      clock=nil
      expiry()
      assert(StatCompass.status.text==StatCompass.Text("shareNoData","enUS"))
    ''')


def test_observation_window_and_summary_in_builder_and_runtime():
    builder = load_tool("build_data")
    valid = synthetic_manifest()
    valid["cohorts"][0]["observations"][0]["observedAt"] = valid["observedAt"] - 86400
    data = builder.checked(valid, b"synthetic", now=NOW)
    lua = load_runtime()
    run(lua, "StatCompass.releaseData=" + builder.lua_value(data))
    assert lua.eval("StatCompass.GetTarget(71,'raid')~=nil")
    stale = copy.deepcopy(valid)
    stale["cohorts"][0]["observations"][0]["observedAt"] -= 1
    with pytest.raises(ValueError, match="observation window"):
        builder.checked(stale, b"synthetic", now=NOW)
    run(lua, "StatCompass.releaseData.cohorts[71].raid.observations[1].observedAt=StatCompass.releaseData.observedAt-86401")
    assert not lua.eval("StatCompass.ValidateDataset(StatCompass.releaseData,120100,69933,90,1800000000)")
    wrong = copy.deepcopy(valid)
    wrong["observedAt"] -= 1
    with pytest.raises(ValueError, match="observedAt summary"):
        builder.checked(wrong, b"synthetic", now=NOW)
    run(lua, "StatCompass.releaseData.cohorts[71].raid.observations[1].observedAt=StatCompass.releaseData.observedAt-86400; StatCompass.releaseData.observedAt=StatCompass.releaseData.observedAt-1")
    assert not lua.eval("StatCompass.ValidateDataset(StatCompass.releaseData,120100,69933,90,1800000000)")


def test_all_render_bound_metadata_escapes_wow_markup():
    manifest = synthetic_manifest()
    cohort = manifest["cohorts"][0]
    cohort["season"] = "|TInterface\\Icons\\INV_Misc_QuestionMark:256|t"
    cohort["rankingMetric"] = "|cffff0000red|r"
    cohort["difficulty"] = "|Hitem:1|hlink|h"
    cohort["partition"] = "x|ny"
    manifest["sourceURL"] = "https://example.invalid/|Tbad|t"
    lua = runtime_with_manifest(manifest)
    run(lua, '''
      C_SpecializationInfo.GetSpecializationInfo=function() return 71,"|Tbad|t" end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.metadataText:find("||T",1,true))
      assert(StatCompass.metadataText:find("||c",1,true))
      assert(StatCompass.metadataText:find("||H",1,true))
      assert(StatCompass.metadataText:find("||n",1,true))
      assert(StatCompass.spec.text:find("||T",1,true))
    ''')


def test_panel_placement_uses_physical_scales_and_owner_move_signals():
    lua = load_runtime()
    run(lua, '''
      UIParent.right=1920; UIParent.top=1080
      CharacterFrame.left=700; CharacterFrame.right=1100
      CharacterFrame.bottom=300; CharacterFrame.top=900
      CharacterFrame.scale=1.5
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.panel.point[1]=="TOPRIGHT") -- right side would end at 2235
      local scale=StatCompass.panel:GetEffectiveScale()
      local firstRight=CharacterFrame:GetLeft()*CharacterFrame:GetEffectiveScale()
      local firstLeft=firstRight-StatCompass.panel:GetWidth()*scale
      assert(firstLeft>=UIParent:GetLeft()*UIParent:GetEffectiveScale())
      assert(firstRight<=UIParent:GetRight()*UIParent:GetEffectiveScale())
      CharacterFrame:SetScale(1)
      CharacterFrame:SetBounds(300,600,300,900)
      assert(StatCompass.panel.point[1]=="TOPLEFT")
      CharacterFrame:SetBounds(1400,1800,300,900)
      assert(StatCompass.panel.point[1]=="TOPRIGHT")
      CharacterFrame:SetBounds(1400,1800,0,120)
      assert(not StatCompass.visible) -- too short for four readable bars
      CharacterFrame:SetBounds(1400,1800,300,900)
      assert(StatCompass.visible and StatCompass.panel.point[1]=="TOPRIGHT")
      local point=StatCompass.panel.point
      local old=StatCompass.panel.point[1]
      CharacterFrame.GetRight=function() return {secret=true} end
      CharacterFrame:SetBounds(1400,1800,300,900)
      assert(not StatCompass.visible or StatCompass.panel.point[1]==old)
    ''')


def test_packaged_german_readme_has_matching_status_and_inventory():
    from pathlib import Path
    from tests.test_tools import load_tool
    root = Path(__file__).resolve().parents[1]
    text = (root / "StatCompass/README.de.txt").read_text(encoding="utf-8")
    assert "EU-Top-50" in text and "keine" in text.lower()
    assert "StatCompass/README.de.txt" in load_tool("package").FILES


def test_row_age_relative_to_collection_boundary_in_builder_and_lua():
    builder = load_tool("build_data")
    valid = synthetic_manifest()
    observed = NOW - 30*86400
    valid["observedAt"] = observed
    valid["cohorts"][0]["observedAt"] = observed
    for row in valid["cohorts"][0]["observations"]:
        row["observedAt"] = observed
    data = builder.checked(valid, b"synthetic", now=NOW)
    lua = load_runtime()
    run(lua, "StatCompass.releaseData=" + builder.lua_value(data))
    assert lua.eval("StatCompass.ValidateDataset(StatCompass.releaseData,120100,69933,90,1800000000)")
    stale = copy.deepcopy(valid)
    stale["observedAt"] -= 1
    stale["cohorts"][0]["observedAt"] -= 1
    for row in stale["cohorts"][0]["observations"]:
        row["observedAt"] -= 1
    with pytest.raises(ValueError, match="collection age"):
        builder.checked(stale, b"synthetic", now=NOW)
    run(lua, "StatCompass.releaseData.observedAt=StatCompass.releaseData.observedAt-1; local c=StatCompass.releaseData.cohorts[71].raid; c.observedAt=c.observedAt-1; for i=1,50 do c.observations[i].observedAt=c.observedAt end")
    assert not lua.eval("StatCompass.ValidateDataset(StatCompass.releaseData,120100,69933,90,1800000000)")


def test_native_owner_move_signals_and_finite_derived_anchor():
    lua = load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      CharacterFrame.left=1400; CharacterFrame.right=1800
      CharacterFrame:StopMovingOrSizing()
      assert(StatCompass.panel.point[1]=="TOPRIGHT")
      CharacterFrame.left=300; CharacterFrame.right=600
      CharacterFrame:SetAllPoints(UIParent)
      assert(StatCompass.panel.point[1]=="TOPLEFT")
      local old=StatCompass.panel.point
      CharacterFrame.scale=1e308
      CharacterFrame:StopMovingOrSizing()
      assert(StatCompass.panel.point==old)
    ''')


def test_same_expiry_replacement_invalidates_callback_and_refreshes_shown_tooltip():
    lua = runtime_with_manifest(synthetic_manifest())
    run(lua, '''
      local now=1800000000
      GetServerTime=function() return now end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      StatCompass.metadataHit.scripts.OnEnter(StatCompass.metadataHit)
      local old=widgets.timers[1].fn
      local oldData=StatCompass.releaseData
      local replacement={}
      for k,v in pairs(oldData) do replacement[k]=v end
      replacement.sourceURL="https://example.invalid/refreshed"
      StatCompass.releaseData=replacement
      Fire("COMBAT_RATING_UPDATE"); RunCallbacks()
      assert(GameTooltip.text:find("refreshed",1,true))
      local renders=0
      local original=StatCompass.Render
      StatCompass.Render=function(snapshot) renders=renders+1; original(snapshot) end
      old()
      assert(renders==0 and #widgets.timers==2)
      now=1800001000
      widgets.timers[2].fn()
      assert(renders==1 and GameTooltip.text==StatCompass.metadataText)
      assert(not GameTooltip.text:find("refreshed",1,true))
    ''')


def test_same_expiry_mode_and_spec_context_invalidate_old_callbacks():
    manifest = synthetic_manifest()
    raid = manifest["cohorts"][0]
    mythic = copy.deepcopy(raid)
    mythic["mode"] = "mythic"
    for row in mythic["observations"]:
        row["mode"] = "mythic"
    other_spec = copy.deepcopy(raid)
    other_spec["specID"] = 72
    for row in other_spec["observations"]:
        row["specID"] = 72
    manifest["cohorts"].extend([mythic, other_spec])
    lua = runtime_with_manifest(manifest)
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local raidTimer=widgets.timers[1].fn
      StatCompass.SetMode("mythic"); RunCallbacks()
      assert(#widgets.timers==2)
      local renders=0
      local original=StatCompass.Render
      StatCompass.Render=function(snapshot) renders=renders+1; original(snapshot) end
      raidTimer()
      assert(renders==0)
      local mythicTimer=widgets.timers[2].fn
      StatCompass.SetMode("raid"); RunCallbacks()
      local oldSpecTimer=widgets.timers[3].fn
      C_SpecializationInfo.GetSpecializationInfo=function() return 72,"Other" end
      Fire("PLAYER_SPECIALIZATION_CHANGED","player"); RunCallbacks()
      local before=renders
      mythicTimer()
      oldSpecTimer()
      assert(renders==before and #widgets.timers==4)
    ''')


@pytest.mark.parametrize("spec_result", ["nil", "{secret=true}", "72"], ids=["missing", "secret", "changed-without-event"])
def test_expiry_invalidates_target_when_spec_unreadable_or_changed(spec_result):
    lua = runtime_with_manifest(synthetic_manifest())
    run(lua, '''
      local now=1800000000
      GetServerTime=function() return now end
      local renders=0
      local original=StatCompass.Render
      StatCompass.Render=function(snapshot) renders=renders+1; original(snapshot) end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(renders==1 and #widgets.timers==1)
      assert(StatCompass.rows[1].target.text:find("32.1%%")) -- cohort rating mean from Core
      StatCompass.metadataHit.scripts.OnEnter(StatCompass.metadataHit)
      local expiry=widgets.timers[1].fn
      C_SpecializationInfo.GetSpecializationInfo=function() return SPEC_RESULT end
      now=1800001000
      expiry()
      assert(renders==2, "expiry must refresh even without a readable matching spec")
      assert(StatCompass.expiryScheduled==nil and StatCompass.expiryAt==nil)
      assert(StatCompass.status.text==StatCompass.Text("shareNoData","enUS"))
      assert(StatCompass.rows[1].target.text==StatCompass.Text("unknown","enUS"))
      assert(not StatCompass.rows[1].markerMin.shown and not StatCompass.rows[1].markerMax.shown)
      assert(GameTooltip.text:find(StatCompass.Text("shareReferenceUnavailable","enUS"),1,true))
      assert(#widgets.timers==1 and #widgets.callbacks==0)
      expiry() -- consumed callback cannot render twice
      assert(renders==2 and #widgets.timers==1 and #widgets.callbacks==0)
    '''.replace("SPEC_RESULT", spec_result))


def test_extreme_scientific_target_text_fits_measured_column():
    manifest = synthetic_manifest()
    for i, row in enumerate(manifest["cohorts"][0]["observations"]):
        row["mastery"] = 1e-308 if i < 25 else 1e308
    lua = runtime_with_manifest(manifest)
    run(lua, '''
      Fire("PLAYER_LOGIN")
      StatCompass.rows[3].max.GetStringWidth=function(self) return #self.text*9 end
      CharacterFrame:Show(); PaperDollFrame:Show()
      StatCompass.Render({shareComparison={mastery={currentShare=100,axisMaxShare=100,axisVerified=true,axisProvenance="synthetic cap",sourceStatus="verified",reference={minShare=1e-308,maxShare=100}}}})
      local target=StatCompass.rows[3].max
      assert(target:GetStringWidth()<=target.width)
      assert(target.text:find("100.0%",1,true))
      assert(not target.text:find("inf",1,true))
      assert(StatCompass.rows[3].min.text:find("1.0e-308",1,true))
      assert(StatCompass.rows[3].fill.width<=StatCompass.rows[3].track.width)
    ''')
