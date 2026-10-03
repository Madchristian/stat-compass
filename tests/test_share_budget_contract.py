"""Synthetic test-only cohorts and hostile share contracts, never shipped as data."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_share_budget_ui import SETUP
from tests.test_followup import synthetic_manifest, NOW
from tests.test_tools import load_tool


@pytest.mark.parametrize("sample_count",[30,50])
def test_actual_core_snapshot_to_ui_and_one_missing_raw_invalidates_all_own_shares(sample_count):
    builder=load_tool('build_data')
    manifest=synthetic_manifest()
    manifest["cohorts"][0]["mode"]="mythic"
    for row in manifest["cohorts"][0]["observations"]: row["mode"]="mythic"
    cohort=manifest["cohorts"][0]
    cohort["observations"]=cohort["observations"][:sample_count]
    cohort["selectedCount"]=cohort["validCount"]=sample_count
    for i,row in enumerate(manifest['cohorts'][0]['observations'],1):
        row['critRating']=800+i*10
    data=builder.checked(manifest,b'synthetic/test share integration',now=NOW)
    lua=load_runtime('GetCombatRating=function(id) if id==9 or id==10 or id==11 then return 1014 elseif id==18 or id==19 or id==20 then return 928 elseif id==26 then return 591 else return 290 end end')
    run(lua,'StatCompass.releaseData='+builder.lua_value(data))
    run(lua,"expectedSample="+str(sample_count))
    run(lua,'''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; local s=a.Snapshot(); a.Render(s)
      assert(s.shareComparison.crit.sourceStatus=="verified")
      assert(s.shareComparison.crit.sampleCount==expectedSample)
      for i,key in ipairs(a.statOrder) do
        local item=s.ratingTarget[key]; local r=a.rows[i]
        assert(r.cachedTarget.target==item.targetRating)
        assert(r.cachedTarget.low==item.lowRating and r.cachedTarget.high==item.highRating)
        assert(r.fill.shown and r.markerTarget.shown)
        assert(math.abs(r.fill.width/r.barWidth-item.currentRating/r.axis)<0.00001)
      end
      assert(a.rows[1].current.text=="1014")
      local prior=GetCombatRating
      GetCombatRating=function(id) if id==26 then return nil end return prior(id) end
      s=a.Snapshot(); a.Render(s)
      assert(a.rows[3].current.text=="Unknown" and not a.rows[3].fill.shown)
      assert(a.rows[1].current.text=="1014" and a.rows[1].fill.shown)
      assert(a.rows[3].markerTarget.shown)
      GetServerTime=function() return 1800001000 end
      s=a.Snapshot(); a.Render(s)
      for _,r in ipairs(a.rows) do
        assert(not r.track.shown and not r.band.shown and not r.fill.shown and not r.markerTarget.shown)
      end
    ''')


@pytest.mark.parametrize('mutation',[
    'item.currentRating=nil','item.currentRating={secret=true}',
    'item.currentRating=0/0','item.currentRating=math.huge','item.currentRating=-1',
    'item.currentRating=false','item.currentRating="35.9"',
])
def test_unknown_invalid_and_outaxis_own_share_do_not_fallback(mutation):
    lua=load_runtime()
    run(lua,SETUP+mutation+'''; render()
      assert(r.current.text=="Unknown")
      assert(not r.fill.shown and r.glow==nil)
      assert(r.band.shown and r.markerTarget.shown)
    ''')


@pytest.mark.parametrize('mutation',[
    'item.lowRating=nil','item.highRating=nil',
    'item.lowRating={secret=true}','item.highRating=0/0',
    'item.lowRating=-1','item.highRating=599',
    'item.lowRating=671','item.highRating=math.huge',
    'item.lowRating=setmetatable({},{__lt=function() error("unsafe") end})',
])
def test_invalid_quartile_pair_clears_only_band(mutation):
    lua=load_runtime()
    run(lua,SETUP+'''
      r.bandHit.scripts.OnEnter(r.bandHit)
    '''+mutation+'''; render()
      assert(not r.band.shown and not r.bandCue.shown and not r.bandHit:IsShown())
      assert(not GameTooltip.shown)
      assert(r.markerTarget.shown and r.fill.shown)
    ''')


@pytest.mark.parametrize('mutation',[
    'item.sourceStatus={secret=true}','item.sourceStatus="unavailable"',
    'item.targetRating={secret=true}','item.targetRating=nil',
    'item.targetRating=-1','item.targetRating=0/0','item.targetRating=math.huge',
    'item.targetPercent=nil','item.personal=0',
    'item=setmetatable({secret=true},{__index=function() error("secret") end})',
    'item=setmetatable({},{__index=function() error("hostile") end})',
])
def test_unverified_axis_and_hostile_payloads_suppress_all_graphics(mutation):
    lua=load_runtime()
    run(lua,SETUP+mutation+'''; render()
      assert(not r.track.shown and not r.fill.shown and not r.band.shown and r.glow==nil)
      assert(not r.markerTarget.shown)
    ''')


def test_status_requires_a_verified_usable_share_axis():
    lua=load_runtime()
    run(lua,SETUP+'''
      item.targetRating=nil; render()
      assert(a.status.text==a.Text("targetUnavailable","enUS"))
    ''')


@pytest.mark.parametrize("value", [0, 1e-308, 1e308, 1.79e308])
def test_rating_extremes_are_finite_on_fixed_scale(value):
    lua=load_runtime()
    run(lua,SETUP+f'''
      item.currentRating={value}; item.targetRating={value}
      item.lowRating={value}; item.highRating={value}; render()
      assert(r.axis==2000)
      assert(r.markerTarget.shown and r.bandCue.shown)
      assert(r.fill.width==nil or r.fill.width<=r.barWidth)
      assert(not r.current.text:find("inf",1,true))
      assert(r.status.text==("fits" .. ({value}>2000 and "; Band >2000" or "")))
    ''')


@pytest.mark.parametrize('locale',['enUS','deDE'])
def test_localized_explanation_and_foreign_ownership(locale):
    lua=load_runtime('GetLocale=function() return "'+locale+'" end')
    run(lua,SETUP+'''
      assert(a.metadataText:find(a.Text("priorityHelp","'''+locale+'''"),1,true))
      r.markerHit.target.scripts.OnEnter(r.markerHit.target)
      local foreign=CreateFrame("Frame"); GameTooltip:SetOwner(foreign); GameTooltip:SetText("foreign"); GameTooltip:Show()
      item.sourceStatus="unavailable"; render()
      assert(GameTooltip.shown and GameTooltip.text=="foreign")
    ''')
