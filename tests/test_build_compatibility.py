"""Client hotfix regressions using synthetic, nonshipping cohort data (Lua 5.1)."""
import pytest

from tests.test_addon import run
from tests.test_combat_core import combat_runtime
from tests.test_followup import NOW, runtime_with_data


@pytest.mark.parametrize("warm_cache", [False, True])
def test_newer_client_build_keeps_targets_on_the_same_interface(warm_cache):
    lua = runtime_with_data()
    if warm_cache:
        run(lua, 'assert(StatCompass.GetTarget(71,"mythic").rating.mastery.mean==800)')
    run(lua, '''
      GetBuildInfo=function() return "12.1.0","69934","synthetic",120100 end
      local target=StatCompass.GetTarget(71,"mythic")
      assert(target and target.rating.mastery.mean==800, "hotfix must preserve comparison values")
      assert(target.clientBuild==69933, "keep the source build as provenance")
      assert(StatCompass.releaseData.clientBuild==69933, "never relabel the dataset")
      assert(StatCompass.GetTarget(71,"mythic").rating.mastery.mean==800)
    ''')


@pytest.mark.parametrize("build,interface", [(69932, 120100), (69934, 120105)])
def test_older_client_or_different_interface_still_rejects_targets(build, interface):
    lua = runtime_with_data()
    run(lua, f'''
      assert(StatCompass.GetTarget(71,"mythic"))
      GetBuildInfo=function() return "synthetic","{build}","synthetic",{interface} end
      assert(StatCompass.GetTarget(71,"mythic")==nil)
    ''')


@pytest.mark.parametrize("change", [
    f'GetServerTime=function() return {NOW+1000} end',
    'UnitLevel=function() return 89 end',
    'StatCompass.releaseData.cohorts[71].mythic.clientBuild=69934',
    'StatCompass.releaseData.cohorts[71].mythic.observations[1].clientBuild=69934',
    'StatCompass.releaseData.cohorts[71].mythic.observations[1].masteryRating=-1',
])
def test_hotfix_does_not_bypass_retention_level_or_source_validation(change):
    lua = runtime_with_data()
    run(lua, '''
      GetBuildInfo=function() return "12.1.0","69934","synthetic",120100 end
      assert(StatCompass.GetTarget(71,"mythic"), "hotfix baseline must be usable")
    ''' + change + '''
      assert(StatCompass.GetTarget(71,"mythic")==nil, "invalid data must remain unavailable")
    ''')


@pytest.mark.parametrize("build", ['"69934"', '0', 'math.huge', '0/0', '{secret=true}'])
def test_validator_rejects_unreadable_or_invalid_live_build(build):
    lua = runtime_with_data()
    run(lua, f'''
      assert(not StatCompass.ValidateDataset(StatCompass.releaseData,120100,{build},90,{NOW}))
    ''')


def test_hotfix_targets_are_cached_before_combat_and_expire_without_rescanning():
    lua = combat_runtime(show=False)
    run(lua, '''
      GetBuildInfo=function() return "12.1.0","69934","synthetic",120100 end
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(last.target and last.ratingTarget.mastery.targetRating==800)
      assert(reads==1 and scans==1)
      fighting=true; StatCompass.SetCombat(true)
      assert(last.preCombat and last.target and last.ratingTarget.mastery.targetRating==800)
      StatCompass.ValidateDataset=function() error("validation in combat") end
      Advance(1000)
      assert(last.preCombat and not last.target and reads==1 and scans==1)
    ''')
