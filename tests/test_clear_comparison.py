"""Player/reference redesign: production Lua 5.1, synthetic data only."""
from tests.test_addon import load_runtime, run
from tests.test_footer_pointer import POINTER
from tests.test_share_budget_ui import SETUP
import pytest


@pytest.mark.parametrize("scale", [0.64, 1, 1.76])
@pytest.mark.parametrize("pixel_density", [1, 1.5, 2])
def test_sidebar_fits_host_gap_below_close_above_equipment_tabs(scale, pixel_density):
    """Screenshot-derived host-local exclusion regions, not native glyph proof.

    The reported 56px-tall button was 32 host units at about 1.76 scale.
    Reserve host-local y=0..18 for the close control and y>=54 for tabs.
    Test the same geometry after independent host-scale/pixel-density changes.
    """
    lua=load_runtime(POINTER)
    run(lua, f'''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      CharacterFrame:SetScale({scale})
      local a=StatCompass; local b=a.sidebarButton
      assert(b.parent==CharacterFrame)
      local factor=b:GetEffectiveScale()*{pixel_density}
      local top=-b.point[5]*factor
      local bottom=top+b:GetHeight()*factor
      assert(top>=22*factor, "sidebar overlaps close-control clearance")
      assert(bottom<=50*factor, "sidebar overlaps equipment-tab clearance")
      assert(b:GetHeight()<=20 and b:GetWidth()<=20, "sidebar must match compact host chrome")
      assert(b.point[4]<=-4 and b.point[4]-b:GetWidth()>-(CharacterFrame:GetRight()-CharacterFrame:GetLeft()))
      assert(b.caption:GetStringWidth()<=b.caption:GetWidth())
      for _,order in ipairs({{true,false}}) do
        assert(PointerClickCenter(b,order)==b and a.settings.collapsed)
        assert(b:IsVisible() and not a.panel:IsVisible())
        assert(PointerClickCenter(b,order)==b and not a.settings.collapsed)
      end
    ''')


def test_sidebar_tooltip_updates_and_respects_foreign_owner():
    lua=load_runtime(POINTER)
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; local b=a.sidebarButton
      b.scripts.OnEnter(b); b.hooks.OnEnter(b)
      assert(a.TooltipIsOwned(b) and GameTooltip.text==a.Text("collapsePanel","enUS"))
      a.SetCollapsed(true)
      assert(GameTooltip.text==a.Text("expandPanel","enUS"))
      local foreign=CreateFrame("Frame",nil,UIParent)
      GameTooltip:SetOwner(foreign); GameTooltip:SetText("foreign"); GameTooltip:Show()
      a.SetCollapsed(false); b.hooks.OnLeave(b)
      PaperDollFrame:Hide()
      assert(GameTooltip.text=="foreign" and GameTooltip.shown)
      PaperDollFrame:Show()
      b.hooks.OnEnter(b)
      UIParent:Hide()
      assert(not GameTooltip.shown, "ancestor hide releases owned sidebar tooltip")
    ''')


def test_collapsed_pending_callbacks_and_font_work_are_idle():
    lua=load_runtime(POINTER)
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; local reads,layouts=0,0
      local snapshot,layout=a.Snapshot,a.Layout
      a.Snapshot=function() reads=reads+1; return snapshot() end
      a.Layout=function(...) layouts=layouts+1; return layout(...) end
      Fire("COMBAT_RATING_UPDATE")
      a.SetCollapsed(true)
      a.SetSkin("flat"); a.SetMinimapAngle(50)
      CharacterFrame:SetScale(0.9); RunCallbacks()
      a.Flush(); a.Render({}); a.QueueRefresh()
      assert(reads==0 and layouts==0)
      a.SetCollapsed(false)
      assert(reads==1)
      RunCallbacks(); assert(reads==1)
    ''')


def test_reference_copy_explains_arithmetic_mean_in_both_locales():
    lua=load_runtime()
    run(lua, '''
      local a=StatCompass
      assert(a.Text("shareDescriptive","enUS"):find("arithmetic mean",1,true))
      assert(a.Text("shareDescriptive","deDE"):find("arithmetische Mittelwert",1,true))
      assert(a.Text("unavailableHelp","enUS"):find("rating",1,true))
      assert(a.Text("unavailableHelp","deDE"):find("Wertung",1,true))
    ''')


@pytest.mark.parametrize("locale,unit,obsolete", [("enUS", "rating", "share"), ("deDE", "Wertung", "Anteil")])
def test_visible_options_help_uses_rating_units(locale, unit, obsolete):
    from tests.test_controls import CONTROLS_MOCK
    lua = load_runtime(CONTROLS_MOCK + f'GetLocale=function() return "{locale}" end')
    run(lua, f'''
      Fire("ADDON_LOADED","StatCompass")
      Settings.OpenToCategory(StatCompass.settingsCategory:GetID())
      local found=false
      for _,font in ipairs(StatCompass.options.canvas.regions) do
        if font.text==StatCompass.Text("unavailableHelp","{locale}") then
          assert(font:IsVisible())
          assert(font.text:find("{unit}",1,true))
          assert(not font.text:find("{obsolete}",1,true))
          found=true
        end
      end
      assert(found,"visible options help must be tested")
    ''')


def test_mythic_only_migration_and_snapshot():
    lua = load_runtime()
    run(lua, '''
      local a=StatCompass
      for _,raw in ipairs({{}, {mode="raid"}, {mode="mythic"}, {mode={secret=true}}}) do
        assert(a.SanitizeSettings(raw).mode=="mythic", "all settings migrate to M+")
      end
      assert(a.SanitizeSettings(nil).mode=="mythic")
      Fire("PLAYER_LOGIN")
      local mode
      a.GetTarget=function(_,value) mode=value end
      a.settings.mode="raid"; a.Snapshot()
      assert(mode=="mythic", "active snapshot must never select raid")
      a.ResetSettings(); assert(StatCompassDB.mode=="mythic")
      a.SetMode("raid"); assert(StatCompassDB.mode=="mythic")
    ''')


def test_sidebar_collapse_same_tree_lifecycle_and_pointer():
    lua = load_runtime(POINTER)
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      assert(#a.buttons==3, "only the actual skin/reset controls remain")
      local b=a.sidebarButton
      assert(b and b.parent==CharacterFrame and b:IsVisible())
      local reads,renders=0,0
      local snapshot,render=a.Snapshot,a.Render
      a.Snapshot=function() reads=reads+1; return snapshot() end
      a.Render=function(s) renders=renders+1; render(s) end
      local frames=widgets.frames
      for _,early in ipairs({true,false}) do
        assert(PointerClickCenter(b,early)==b)
        assert(StatCompassDB.collapsed and not a.visible and not a.panel:IsVisible())
        assert(b:IsVisible(), "expander must survive panel hide")
        local r,n=reads,renders
        for i=1,10 do Fire("COMBAT_RATING_UPDATE") end
        CharacterFrame:SetSize(400,600); RunCallbacks()
        assert(reads==r and renders==n, "collapsed work must be idle")
        PaperDollFrame:Hide(); assert(not b:IsVisible())
        PaperDollFrame:Show(); assert(b:IsVisible() and not a.visible)
        UIParent:Hide(); assert(not b:IsVisible())
        UIParent:Show(); assert(b:IsVisible() and not a.visible)
        C_SpecializationInfo.GetSpecializationInfo=function() return 72,"Fury" end
        assert(PointerClickCenter(b,early)==b)
        assert(not StatCompassDB.collapsed and a.visible)
        assert(reads==r+1 and renders==n+1)
        assert(a.spec.text=="Fury")
      end
      assert(widgets.frames==frames)
    ''')


def test_collapsed_settings_are_boolean_and_resettable():
    lua=load_runtime('StatCompassDB={collapsed=true,mode="raid",skin="flat"}')
    run(lua, '''
      local a=StatCompass
      for _,value in ipairs({"true",1,{}, {secret=true}}) do
        assert(a.SanitizeSettings({collapsed=value}).collapsed==false)
      end
      assert(a.SanitizeSettings(nil).collapsed==false)
      local layouts=0; local layout=a.Layout
      a.Layout=function(...) layouts=layouts+1; return layout(...) end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(not a.visible and a.sidebarButton:IsVisible())
      assert(layouts==0, "persisted collapse must skip initial panel layout")
      a.SetCollapsed(nil); a.SetCollapsed({secret=true})
      assert(StatCompassDB.collapsed==true)
      a.ResetSettings()
      assert(a.visible and StatCompassDB.collapsed==false)
    ''')


@pytest.mark.parametrize("locale,reference", [("deDE","Ziel"),("enUS","Target")])
def test_own_value_is_distinct_from_reference(locale, reference):
    lua=load_runtime('GetLocale=function() return "%s" end' % locale)
    run(lua, SETUP + '''
      assert(r.current.text=="400")
      assert(r.target.text=="%s 638")
      assert(r.current.justify=="LEFT" and r.current.point[4]<r.target.point[4])
      assert(r.current:GetStringHeight()>r.target:GetStringHeight())
      for i=1,3 do assert(r.current.color[i]==r.palette[i] and r.fill.color[i]==r.palette[i]) end
      assert(r.fill.color[4]==1 and r.glow==nil)
      assert(r.band.shown and r.band.height<=3)
      assert(r.tip.target:find(a.Text("targetHelp","%s"),1,true))
    ''' % (reference,locale))
