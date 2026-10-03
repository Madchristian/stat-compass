"""Event-to-render combat integration, using the real Lua 5.1 UI and Core."""
import pytest

from tests.test_addon import run
from tests.test_followup import runtime_with_data


def ui_runtime(startup="", locale=None):
    lua = runtime_with_data(locale)
    run(lua, '''
      clock=0; fighting=false
      GetCombatRating=function() return 500 end
      GetTime=function() return clock end
      InCombatLockdown=function() return fighting end
      GetServerTime=function() return 1800000000+math.floor(clock) end
      C_Timer.After=function(delay,fn)
        table.insert(widgets.timers,{due=clock+delay,fn=fn})
      end
      function Advance(seconds)
        local finish=clock+seconds
        while true do
          local index,due
          for i,t in ipairs(widgets.timers) do
            if t.due<=finish and (not due or t.due<due) then index,due=i,t.due end
          end
          if not index then break end
          local t=table.remove(widgets.timers,index); clock=due; t.fn()
        end
        clock=finish
      end
      function Dispatch(event,arg)
        assert(StatCompass.EventFrame.events[event], "event not registered: "..event)
        Fire(event,arg)
      end
      reads=0; scans=0; renders=0; combatTargets=0
      local read,validate,render,target=StatCompass.ReadStats,StatCompass.ValidateDataset,StatCompass.Render,StatCompass.GetTarget
      StatCompass.ReadStats=function() assert(not fighting, "combat stat read"); reads=reads+1; return read() end
      local ratings=StatCompass.ReadRatings
      StatCompass.ReadRatings=function() assert(not fighting, "combat rating read"); return ratings() end
      StatCompass.ValidateDataset=function(...) assert(not fighting, "combat aggregation"); scans=scans+1; return validate(...) end
      StatCompass.GetTarget=function(...)
        if fighting then combatTargets=combatTargets+1 end
        return target(...)
      end
      StatCompass.Render=function(s) renders=renders+1; last=s; return render(s) end
    ''' + startup)
    return lua


@pytest.mark.parametrize("event", ["PLAYER_SPECIALIZATION_CHANGED", "ACTIVE_TALENT_GROUP_CHANGED", "PLAYER_TALENT_UPDATE", "TRAIT_CONFIG_UPDATED", "UNIT_LEVEL", "PLAYER_ENTERING_WORLD"])
def test_context_events_invalidate_immediately_in_combat(event):
    lua = shown_runtime()
    run(lua, '''
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      table.sort=function() error("combat sort") end
    ''')
    lua.globals().context_event = event
    run(lua, '''
      Dispatch(context_event,"player")
      assert(not last.target, "context event must remove cached reference immediately")
      assert(reads==1 and scans==1)
      assert(StatCompass.rows[1].target.text=="")
      Advance(60); assert(reads==1 and scans==1 and not last.target and last.preCombat)
    ''')


@pytest.mark.parametrize("event", ["ADDON_LOADED", "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD"])
@pytest.mark.parametrize("api", [
    'function() return true end', 'function() return nil end',
    'function() error("unreadable") end', 'function() return {secret=true} end',
    'nil', '{secret=true}',
])
def test_startup_synchronizes_combat_before_attach_or_show(event, api):
    lua = ui_runtime()
    lua.globals().startup_event = event
    run(lua, 'InCombatLockdown=' + api)
    run(lua, '''
      local set=StatCompass.SetCombat
      local synchronized=false
      StatCompass.SetCombat=function(active)
        assert(active==true, "unknown startup state must fail closed")
        synchronized=true; return set(active)
      end
      local apply=StatCompass.ApplySkin
      StatCompass.ApplySkin=function(...)
        assert(synchronized, "combat synchronization must precede attachment/show")
        return apply(...)
      end
      CharacterFrame:Show(); PaperDollFrame:Show()
      Dispatch(startup_event,"StatCompass")
      assert(synchronized and StatCompass.visible and reads==0 and scans==0)
      Advance(60); assert(reads==0 and scans==0 and not last.target and not last.preCombat)
      assert(StatCompass.title.text=="Stat Compass")
      assert(StatCompass.rows[1].current.text=="Unknown")
      StatCompass.SetCombat=set
      InCombatLockdown=function() return false end
      Dispatch("PLAYER_REGEN_ENABLED")
      assert(reads==1 and scans==1 and last.target and not last.preCombat)
    ''')


def shown_runtime(locale=None):
    return ui_runtime('Dispatch("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()', locale)


@pytest.mark.parametrize("locale,expected", [("deDE", "Stand vor Kampf"), ("enUS", "Pre-combat snapshot")])
def test_freeze_label_entry_exit_and_locale(locale, expected):
    lua = shown_runtime(locale)
    lua.globals().expected_label = expected
    run(lua, '''
      local a=StatCompass
      assert(a.title.text=="Stat Compass")
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      assert(last.preCombat==true)
      assert(a.title.text=="Stat Compass - "..expected_label)
      assert(a.title:GetStringWidth()<=a.title:GetWidth())
      Dispatch("TRAIT_CONFIG_UPDATED")
      assert(not last.target and last.preCombat)
      assert(a.title.text=="Stat Compass - "..expected_label)
      fighting=false; Dispatch("PLAYER_REGEN_ENABLED")
      assert(not last.preCombat and a.title.text=="Stat Compass")
      assert(reads==2)
    ''')


@pytest.mark.parametrize("event", ["UNIT_AURA", "UNIT_STATS", "UNIT_SPELL_HASTE", "UNIT_LEVEL", "PLAYER_SPECIALIZATION_CHANGED"])
@pytest.mark.parametrize("unit", ['"target"', 'nil', '{secret=true}'])
def test_unit_filters_do_not_queue_or_invalidate(event, unit):
    lua = shown_runtime()
    lua.globals().unit_event = event
    run(lua, '''
      local queue=StatCompass.QueueRefresh
      local calls=0
      StatCompass.QueueRefresh=function(...) calls=calls+1; return queue(...) end
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      Dispatch(unit_event,''' + unit + ''')
      assert(calls==0 and reads==1 and last.target)
    ''')


def test_visibility_flips_and_expiry_use_core_scheduler_only():
    lua = shown_runtime()
    run(lua, '''
      local a=StatCompass
      a.releaseData.expiresAt=1800000015
      Dispatch("PLAYER_TALENT_UPDATE"); Advance(0)
      local before=reads
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      Advance(3); CharacterFrame:Hide(); Advance(1); CharacterFrame:Show()
      a.SetCollapsed(true); a.SetCollapsed(false)
      assert(reads==before)
      Advance(6); assert(reads==before and last.target and last.preCombat)
      PaperDollFrame:Hide(); Advance(1); PaperDollFrame:Show()
      Advance(4)
      assert(reads==before and not last.target and a.rows[1].target.text=="")
      assert(last.preCombat and a.title.text=="Stat Compass - Pre-combat snapshot")
      CharacterFrame:Hide(); Advance(1100)
      assert(reads==before and #widgets.timers==0, "hidden callbacks must stop rearming")
      fighting=false; Dispatch("PLAYER_REGEN_ENABLED")
      assert(reads==before)
      CharacterFrame:Show(); assert(reads==before+1 and not last.preCombat)
    ''')


def test_hidden_context_event_prevents_cached_target_revival():
    lua = shown_runtime()
    run(lua, '''
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      CharacterFrame:Hide(); Dispatch("TRAIT_CONFIG_UPDATED")
      Advance(2); CharacterFrame:Show()
      assert(reads==1 and not last.target)
      Advance(60); assert(reads==1 and scans==1 and not last.target and last.preCombat)
      fighting=false; Dispatch("PLAYER_REGEN_ENABLED")
      assert(reads==2 and scans==2 and last.target)
    ''')


@pytest.mark.parametrize("event", ["ADDON_LOADED", "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD"])
@pytest.mark.parametrize("visibility", ["shown", "character_hidden", "paper_hidden", "collapsed"])
@pytest.mark.parametrize("previous", ["combat", "unknown"])
@pytest.mark.parametrize("timer", [True, False])
def test_lifecycle_recovery_refreshes_once(event, visibility, previous, timer):
    lua = shown_runtime()
    lua.globals().recovery_event = event
    lua.globals().visibility = visibility
    lua.globals().previous = previous
    lua.globals().has_timer = timer
    run(lua, '''
      if visibility=="character_hidden" then CharacterFrame:Hide() end
      if visibility=="paper_hidden" then PaperDollFrame:Hide() end
      if visibility=="collapsed" then StatCompass.SetCollapsed(true) end
      if previous=="combat" then
        fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      else
        InCombatLockdown=function() return nil end
        Dispatch("PLAYER_LOGIN")
      end
      local before,validated=reads,scans
      if not has_timer then C_Timer.After=nil end
      fighting=false; InCombatLockdown=function() return false end
      Dispatch(recovery_event,"StatCompass")
      if visibility=="shown" then
        assert(reads==before+1, "visible recovery must refresh immediately once")
        if recovery_event=="PLAYER_ENTERING_WORLD" then
          assert(scans==validated+1, "world context must validate in the recovery refresh")
        end
      else
        assert(reads==before, "hidden recovery must not query stats")
      end
      Advance(0)
      if visibility=="shown" then
        assert(reads==before+1, "recovery must not queue a second refresh")
      else
        assert(reads==before)
        if visibility=="character_hidden" then CharacterFrame:Show() end
        if visibility=="paper_hidden" then PaperDollFrame:Show() end
        if visibility=="collapsed" then StatCompass.SetCollapsed(false) end
        assert(reads==before+1)
        if recovery_event=="PLAYER_ENTERING_WORLD" then assert(scans==validated+1) end
        Advance(0); assert(reads==before+1)
      end
      assert(last.target and not last.preCombat)
    ''')


@pytest.mark.parametrize("event", ["ADDON_LOADED", "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD"])
@pytest.mark.parametrize("visible", [True, False])
def test_out_of_combat_initial_attach_refreshes_once(event, visible):
    lua = ui_runtime()
    lua.globals().startup_event = event
    lua.globals().initially_visible = visible
    run(lua, '''
      if initially_visible then CharacterFrame:Show(); PaperDollFrame:Show() end
      Dispatch(startup_event,"StatCompass")
      assert(StatCompass.panel, "startup must attach the panel")
      if initially_visible then assert(reads==1 and scans==1)
      else assert(reads==0 and scans==0) end
      Advance(0)
      if not initially_visible then CharacterFrame:Show(); PaperDollFrame:Show() end
      assert(reads==1 and scans==1 and last.target)
      Advance(0); assert(reads==1 and scans==1)
    ''')


@pytest.mark.parametrize("timer", [True, False])
def test_world_entry_without_combat_transition_revalidates_context(timer):
    lua = shown_runtime()
    if not timer:
        run(lua, 'C_Timer.After=nil')
    run(lua, '''
      local before,validated=reads,scans
      Dispatch("PLAYER_ENTERING_WORLD")
      Advance(0)
      assert(reads==before+1 and scans==validated+1 and last.target)
      Advance(0); assert(reads==before+1 and scans==validated+1)
    ''')


def test_world_entry_resynchronizes_missed_combat_transition():
    lua = shown_runtime()
    run(lua, '''
      fighting=true; Dispatch("PLAYER_ENTERING_WORLD")
      assert(reads==1 and not last.target)
      Advance(60); assert(reads==1 and scans==1)
      fighting=false; Dispatch("PLAYER_ENTERING_WORLD")
      assert(reads==2 and last.target)
      Advance(0); assert(reads==2 and scans==2 and last.target)
    ''')


@pytest.mark.parametrize("locale", ["deDE", "enUS"])
@pytest.mark.parametrize("skin", ["default", "flat"])
def test_frozen_display_survives_events_and_reopen(locale, skin):
    lua = shown_runtime(locale)
    lua.globals().skin = skin
    run(lua, '''
      local a=StatCompass
      a.SetSkin(skin)
      local saved={}
      for i,row in ipairs(a.rows) do
        saved[i]={row.current.text,row.target.text,row.status.text,row.fill.width,row.tip.current}
      end
      GetCombatRating=function() error("live combat rating API") end
      GetHaste=function() error("live combat percent API") end
      table.sort=function() error("combat aggregation") end
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      local entered=renders
      for i=1,100 do Dispatch("COMBAT_RATING_UPDATE"); Dispatch("UNIT_AURA","player") end
      Advance(120)
      assert(renders==entered, "combat event bursts must not render")
      local snapshot=a.Snapshot()
      snapshot.ratingTarget.crit.currentRating=9999
      snapshot.target.priority[1]="versatility"
      CharacterFrame:Hide(); Advance(5); CharacterFrame:Show()
      a.SetCollapsed(true); a.SetCollapsed(false)
      assert(last.preCombat and reads==1 and scans==1 and combatTargets==0)
      for i,row in ipairs(a.rows) do
        local old=saved[i]
        assert(row.current.text==old[1] and row.target.text==old[2] and row.status.text==old[3])
        assert(row.fill.width==old[4] and row.tip.current==old[5])
      end
      assert(a.title.text=="Stat Compass - "..a.Text("preCombat",GetLocale()))
    ''')


@pytest.mark.parametrize("locale", ["deDE", "enUS"])
@pytest.mark.parametrize("flag", ["nil", "false", '"true"', "1", "{secret=true}"])
def test_label_requires_public_true_provenance(locale, flag):
    lua = shown_runtime(locale)
    run(lua, '''
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      local snapshot=StatCompass.Snapshot()
      snapshot.preCombat=''' + flag + '''
      StatCompass.Render(snapshot)
      assert(StatCompass.title.text=="Stat Compass")
    ''')


@pytest.mark.parametrize("locale", ["deDE", "enUS"])
@pytest.mark.parametrize("skin", ["default", "flat"])
def test_freeze_title_fits_existing_header_without_layout_shift(locale, skin):
    lua = shown_runtime(locale)
    lua.globals().skin = skin
    run(lua, '''
      local a=StatCompass
      a.SetSkin(skin)
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      for _,height in ipairs({420,424,750}) do
        a.Layout(360,height)
        assert(a.title:GetStringWidth()<=a.title:GetWidth())
        local titleY=a.title.point[5]
        local specY=a.spec.point[5]
        local _,size=a.title:GetFont()
        assert(titleY-size>specY, "title overlaps specialization")
      end
    ''')


def test_combat_dispatch_never_calls_get_target():
    lua = shown_runtime()
    run(lua, '''
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      Advance(10)
      assert(combatTargets==0, "Core readContext still calls GetTarget during combat")
    ''')


def test_combat_events_freeze_and_immediate_exit_refresh():
    lua = shown_runtime()
    run(lua, '''
      assert(reads==1 and scans==1 and last.target)
      Dispatch("UNIT_AURA","player") -- pending out-of-combat callback
      fighting=true; Dispatch("PLAYER_REGEN_DISABLED")
      for i=1,100 do Dispatch("COMBAT_RATING_UPDATE"); Dispatch("UNIT_AURA","player") end
      Advance(9.99); assert(reads==1)
      Advance(0.01); assert(reads==1 and scans==1 and last.target)
      assert(StatCompass.rows[1].current.text~="Unknown")
      Advance(60); assert(reads==1 and scans==1)
      fighting=false; Dispatch("PLAYER_REGEN_ENABLED")
      assert(reads==2 and last.target)
      Dispatch("PLAYER_REGEN_ENABLED"); Advance(10); assert(reads==2)
      for i=1,20 do Dispatch("COMBAT_RATING_UPDATE") end
      Advance(0); assert(reads==3)
    ''')
