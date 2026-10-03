"""Lua 5.1 combat regression tests; synthetic, nonshipping data only."""
import pytest

from tests.test_addon import run
from tests.test_followup import runtime_with_data


def combat_runtime(show=True):
    lua = runtime_with_data()
    run(lua, '''
      clock=0; fighting=false
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
      reads=0; scans=0; renders=0
      local read=StatCompass.ReadStats
      StatCompass.ReadStats=function() reads=reads+1; return read() end
      local validate=StatCompass.ValidateDataset
      StatCompass.ValidateDataset=function(...) scans=scans+1; return validate(...) end
      StatCompass.Render=function(s) renders=renders+1; last=s end
      Fire("PLAYER_LOGIN")
    ''')
    if show:
        run(lua, 'CharacterFrame:Show(); PaperDollFrame:Show()')
    return lua


def test_combat_freezes_precombat_snapshot_without_stat_timers():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      assert(reads==1 and scans==1 and last.target)
      local before=last.current.haste
      fighting=true
      -- The new freeze policy supersedes the old ten-second stat cadence.
      a.SetCombat(true)
      assert(last.preCombat == true and last.current.haste == before)
      local entryRenders=renders
      for _,timer in ipairs(widgets.timers) do
        assert(timer.due~=clock+10, "no ten-second callback may be scheduled")
      end
      a.ReadStats=function() error("combat stat read") end
      a.ReadRatings=function() error("combat rating read") end
      a.GetTarget=function() error("combat target recomputation") end
      for i=1,100 do a.QueueRefresh("UNIT_AURA") end
      Advance(60)
      assert(reads==1 and scans==1 and last.target and renders==entryRenders)
      assert(a.Snapshot().preCombat == true)
      a.Flush()
      assert(reads==1 and scans==1)

    ''')


def test_unchanged_dataset_reuses_validation_and_targets_but_mutation_is_checked():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      local sorts=0; local sort=table.sort
      table.sort=function(...) sorts=sorts+1; return sort(...) end
      a.Flush(); a.Flush()
      assert(scans==1 and sorts==0, "unchanged data must reuse validation and quantiles")
      a.releaseData.cohorts[71].mythic.observations[2].masteryRating=-1
      a.Flush()
      assert(not last.target and scans==2, "nested mutation must not reuse validated data")
      a.releaseData.cohorts[71].mythic.observations[2].masteryRating=800
      a.Flush()
      assert(last.target and scans==3 and sorts>0)
      last.target.rating.mastery.median=99999
      assert(a.Snapshot().target.rating.mastery.median==800, "caller cannot poison private cache")
    ''')


@pytest.mark.parametrize("change", [
    'a.releaseData={}',
    'a.releaseData.expiresAt=1800000001',
    'C_SpecializationInfo.GetSpecializationInfo=function() return 72 end',
    'C_ClassTalents={GetActiveHeroTalentSpec=function() return 66 end}',
    'GetBuildInfo=function() return "12.1", "69934", "", 120100 end',
    'GetBuildInfo=function() return nil end',
    'UnitLevel=function() return 89 end',
    'a.QueueRefresh("PLAYER_TALENT_UPDATE")',
    'a.releaseData.cohorts[71].mythic={}',
    'a.settings.mode="raid"',
])
def test_combat_context_invalidates_without_validation_or_sorting(change):
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      fighting=true; a.SetCombat(true)
      table.sort=function() error("sorting in combat") end
      local data=a.releaseData
      local build=GetBuildInfo
    ''' + change + '''
      a.Flush() -- explicit display access checks context; no periodic combat work
      assert(reads==1 and scans==1 and not last.target, "changed context must fail closed")
      a.releaseData=data; GetBuildInfo=build
      assert(not a.Snapshot().target, "invalidated targets must not revive in combat")
    ''')


def test_expiry_clears_target_without_extra_current_stat_read():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      a.releaseData.expiresAt=1800000005; a.Flush()
      local before=reads
      fighting=true; a.SetCombat(true)
      Advance(5)
      assert(not last.target, "expiry must hide references at the boundary")
      assert(reads==before, "expiry is not a stat polling bypass")
      Advance(5)
      assert(reads==before and not last.target and last.preCombat)
    ''')


def test_hidden_and_collapsed_have_no_periodic_reads_and_old_callbacks_are_inert():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      fighting=true; a.SetCombat(true)
      Advance(3); PaperDollFrame:Hide()
      Advance(20); assert(reads==1)
      PaperDollFrame:Show(); assert(reads==1 and last.preCombat)
      Advance(1); a.SetCollapsed(true)
      Advance(20); assert(reads==1)
      a.SetCollapsed(false); assert(reads==1 and last.preCombat)
      Advance(1); PaperDollFrame:Hide(); PaperDollFrame:Show()
      assert(reads==1, "reopen must use the frozen snapshot")
      Advance(9); assert(reads==1)
      fighting=false; a.SetCombat(false)
      assert(reads==2 and not last.preCombat)
      local before=reads; Advance(20); assert(reads==before)
    ''')


def test_combat_without_precombat_cache_never_validates():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      PaperDollFrame:Hide()
      fighting=true; a.SetCombat(true)
      a.InvalidateTarget() -- valid dataset, but no precombat cache remains
      PaperDollFrame:Show()
      Advance(10)
      assert(not last.target and scans==1)
      assert(not a.ValidateDataset(a.releaseData,120100,69933,90,1800000000))
    ''')


def test_reopen_clears_changed_context_without_stat_read():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      fighting=true; a.SetCombat(true); Advance(10)
      PaperDollFrame:Hide(); Advance(1)
      C_SpecializationInfo.GetSpecializationInfo=function() return 72 end
      PaperDollFrame:Show()
      assert(reads==1 and not last.target, "reopen must not expose the old spec target")
    ''')


def test_unreadable_hero_cannot_reuse_generic_precombat_reference():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      fighting=true; a.SetCombat(true)
      local secret=setmetatable({secret=true},{__index=function() error("secret indexed") end})
      C_ClassTalents=secret
      a.Flush()
      assert(not last.target and scans==1)
    ''')


def test_combat_secret_current_stats_are_never_queried():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      local before=last.current.haste
      local rating=last.ratingTarget.haste.currentRating
      fighting=true; a.SetCombat(true)
      local secret=setmetatable({secret=true},{__index=function() error("secret indexed") end})
      GetCombatRating=function() return secret end
      GetHaste=function() return secret end
      Advance(10)
      a.Flush()
      assert(last.target and last.current.haste==before and last.preCombat)
      assert(last.ratingTarget.haste.currentRating==rating and scans==1 and reads==1)
    ''')


def test_queued_ooc_callback_cannot_run_after_combat_transition():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      a.QueueRefresh(); fighting=true; a.SetCombat(true)
      Advance(0); assert(reads==1)
      fighting=false; a.SetCombat(false)
      assert(reads==2)
      Advance(10); assert(reads==2)
    ''')


def test_out_of_combat_context_burst_coalesces_one_render():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      for i=1,100 do a.QueueRefresh("PLAYER_TALENT_UPDATE") end
      assert(reads==1 and renders==1)
      Advance(0)
      assert(reads==2 and renders==2 and last.target)
    ''')


def test_nonplain_dataset_is_not_accepted_as_immutable_combat_cache():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      setmetatable(a.releaseData,{})
      a.Flush(); assert(last.target)
      fighting=true; a.SetCombat(true); Advance(10)
      assert(not last.target)
    ''')


def test_combat_expiry_after_hide_reopen_remains_armed():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      a.releaseData.expiresAt=1800000015; a.Flush()
      fighting=true; a.SetCombat(true); Advance(10)
      local before=reads
      PaperDollFrame:Hide(); Advance(1); PaperDollFrame:Show()
      Advance(4)
      assert(reads==before and not last.target, "reopen must rearm exact expiry")
    ''')


def test_first_open_in_combat_is_neutral_without_precombat_claim():
    lua = combat_runtime(show=False)
    run(lua, '''
      local a=StatCompass
      fighting=true; a.SetCombat(true)
      CharacterFrame:Show(); PaperDollFrame:Show(); Advance(60)
      assert(reads==0 and scans==0 and last.preCombat==false)
      assert(not last.target and not last.current.haste and not last.ratingTarget.haste.currentRating)
      PaperDollFrame:Hide(); fighting=false; a.SetCombat(false)
      Advance(60); assert(reads==0 and scans==0)
      PaperDollFrame:Show()
      assert(reads==1 and scans==1 and last.target and last.preCombat==false)
    ''')


def test_expiry_still_clears_visible_reference_after_unannounced_header_change():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      a.releaseData.expiresAt=1800000005; a.Flush()
      fighting=true; a.SetCombat(true)
      local before=reads
      a.releaseData={secret=true}
      Advance(5)
      assert(not last.target and reads==before and last.preCombat)
    ''')


def test_old_expiry_and_refresh_callbacks_cannot_touch_new_visible_generation():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      a.releaseData.expiresAt=1800000005; a.Flush(); a.QueueRefresh()
      local old={}; for _,timer in ipairs(widgets.timers) do old[#old+1]=timer.fn end
      fighting=true; a.SetCombat(true)
      PaperDollFrame:Hide(); PaperDollFrame:Show()
      local beforeReads,beforeRenders=reads,renders
      for _,fn in ipairs(old) do fn() end
      assert(reads==beforeReads and renders==beforeRenders and last.target)
      Advance(5); assert(not last.target and reads==beforeReads)
      fighting=false; a.SetCombat(false)
      assert(reads==beforeReads+1 and not last.preCombat)
      a.SetCombat(false); Advance(60); assert(reads==beforeReads+1)
    ''')


def test_unreadable_ooc_sample_with_replaced_catalog_cannot_revive_old_targets():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      a.ReadStats=function() return {} end; a.ReadRatings=function() return {} end
      a.releaseData.cohorts[71].mythic.observations[2].masteryRating=900
      a.Flush(); assert(last.target)
      fighting=true; a.SetCombat(true)
      assert(last.preCombat and not last.target, "historical target belongs to another cache generation")
    ''')


def test_all_unknown_ooc_sample_does_not_claim_precombat_readable_data():
    lua = combat_runtime(show=False)
    run(lua, '''
      local a=StatCompass
      a.ReadStats=function() return {} end; a.ReadRatings=function() return {} end
      CharacterFrame:Show(); PaperDollFrame:Show()
      fighting=true; a.SetCombat(true)
      assert(last.preCombat==false and not last.target and not last.current.haste)
    ''')


def test_last_readable_snapshot_survives_unreadable_ooc_sample_and_caller_mutation():
    lua = combat_runtime()
    run(lua, '''
      local a=StatCompass
      local value=last.current.haste
      last.current.haste=99999; last.ratingTarget.haste.currentRating=99999
      a.ReadStats=function() return {} end; a.ReadRatings=function() return {} end
      a.Flush(); assert(not last.current.haste)
      fighting=true; a.SetCombat(true)
      assert(last.preCombat==true and last.current.haste==value)
      last.current.haste=99999
      assert(a.Snapshot().current.haste==value)
    ''')
