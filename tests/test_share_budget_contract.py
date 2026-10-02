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
        local item=s.shareComparison[key]; local r=a.rows[i]
        assert(r.axis==item.axisMaxShare and r.band.shown and r.fill.shown)
        assert(r.cachedShare.bounds.low==item.reference.lowShare)
        assert(r.cachedShare.bounds.high==item.reference.highShare)
        assert(math.abs(r.fill.width/r.barWidth-item.currentShare/item.axisMaxShare)<0.00001)
      end
      assert(a.rows[1].current.text=="36%" and a.rows[1].tip.current:find("1014",1,true))
      local prior=GetCombatRating
      GetCombatRating=function(id) if id==26 then return nil end return prior(id) end
      s=a.Snapshot(); a.Render(s)
      for i,key in ipairs(a.statOrder) do
        assert(s.shareComparison[key].currentShare==nil)
        assert(a.rows[i].current.text=="Unknown" and not a.rows[i].fill.shown)
        assert(a.rows[i].band.shown and not a.rows[i].markerCurrent.shown)
      end
      GetServerTime=function() return 1800001000 end
      s=a.Snapshot(); a.Render(s)
      for _,r in ipairs(a.rows) do
        assert(not r.track.shown and not r.band.shown and not r.fill.shown and not r.glow.shown)
      end
    ''')


@pytest.mark.parametrize('mutation',[
    'item.currentShare=nil','item.currentShare={secret=true}',
    'item.currentShare=0/0','item.currentShare=math.huge','item.currentShare=-1',
    'item.currentShare=56','item.currentShare=1e308','item.currentShare="35.9"',
])
def test_unknown_invalid_and_outaxis_own_share_do_not_fallback(mutation):
    lua=load_runtime()
    run(lua,SETUP+mutation+'''; render()
      assert(r.current.text=="Unknown")
      assert(not r.fill.shown and not r.markerCurrent.shown and not r.glow.shown)
      assert(r.band.shown and r.markerMean.shown)
    ''')


@pytest.mark.parametrize('mutation',[
    'item.reference.lowShare=nil','item.reference.highShare=nil',
    'item.reference.lowShare={secret=true}','item.reference.highShare=0/0',
    'item.reference.lowShare=-1','item.reference.highShare=56',
    'item.reference.lowShare=44','item.reference.highShare=math.huge',
    'item.reference.lowShare=setmetatable({},{__lt=function() error("unsafe") end})',
])
def test_invalid_quartile_pair_clears_only_band(mutation):
    lua=load_runtime()
    run(lua,SETUP+'''
      r.bandHit.scripts.OnEnter(r.bandHit)
    '''+mutation+'''; render()
      assert(not r.band.shown and not r.bandCue.shown and not r.bandHit:IsShown())
      assert(not GameTooltip.shown)
      assert(r.markerMin.shown and r.markerMean.shown and r.markerMax.shown and r.fill.shown)
    ''')


@pytest.mark.parametrize('mutation',[
    'item.sourceStatus={secret=true}','item.sourceStatus="unavailable"',
    'item.axisVerified={secret=true}','item.axisVerified=false',
    'item.axisMaxShare=0','item.axisMaxShare=0/0','item.axisMaxShare=math.huge',
    'item.axisMaxShare={secret=true}','item.axisProvenance=nil',
    'item=setmetatable({secret=true},{__index=function() error("secret") end})',
    'item=setmetatable({},{__index=function() error("hostile") end})',
])
def test_unverified_axis_and_hostile_payloads_suppress_all_graphics(mutation):
    lua=load_runtime()
    run(lua,SETUP+mutation+'''; render()
      assert(not r.track.shown and not r.fill.shown and not r.band.shown and not r.glow.shown)
      assert(not r.markerCurrent.shown and not r.markerMin.shown and not r.markerMean.shown and not r.markerMax.shown)
    ''')


def test_status_requires_a_verified_usable_share_axis():
    lua=load_runtime()
    run(lua,SETUP+'''
      item.axisVerified=false; render()
      assert(a.status.text==a.Text("shareNoData","enUS"))
    ''')


def test_reference_percentage_limit_independent_of_headroom_axis():
    lua=load_runtime()
    run(lua,SETUP+'''
      item.axisMaxShare=110; item.currentShare=100
      item.reference={minShare=0,lowShare=0,meanShare=50,highShare=100,maxShare=100}
      render(); assert(r.fill.shown and r.band.shown and r.markerMax.shown)
      item.reference.highShare=101; item.reference.maxShare=101
      render(); assert(not r.band.shown and not r.markerMax.shown)
      item.currentShare=101; render(); assert(not r.fill.shown)
    ''')


def test_synthetic_paladin_supplied_shares_not_effect_percent_or_recomputed():
    lua=load_runtime()
    run(lua,SETUP+'''
      local shares={35.9,32.9,20.9,10.3}
      local lows={31.1,31.9,12.1,6.3}; local highs={43.3,39.7,22.1,14.3}
      local raw={1014,928,591,290}; local payload={shareComparison={},ratingComparison={},current={}}
      for i,key in ipairs(a.statOrder) do
        payload.shareComparison[key]={currentShare=shares[i],axisMaxShare=55,axisVerified=true,axisProvenance="synthetic/test",sourceStatus="verified",sampleCount=30,reference={lowShare=lows[i],highShare=highs[i]}}
        payload.ratingComparison[key]={currentRating=raw[i],sourceStatus="unavailable"}
        payload.current[key]=99
      end
      a.Render(payload)
      for i,key in ipairs(a.statOrder) do
        local row=a.rows[i]
        assert(row.current.text==string.format("%.0f%%",shares[i]))
        assert(row.cachedShare.current==shares[i] and row.cachedShare.bounds.low==lows[i] and row.cachedShare.bounds.high==highs[i])
        assert(row.tip.current:find(tostring(raw[i]),1,true))
      end
      payload.shareComparison=nil; a.Render(payload)
      for _,row in ipairs(a.rows) do assert(row.current.text=="Unknown" and not row.fill.shown) end
    ''')


@pytest.mark.parametrize('locale',['enUS','deDE'])
def test_localized_explanation_and_matching_rating_reference(locale):
    lua=load_runtime('GetLocale=function() return "'+locale+'" end')
    run(lua,SETUP+'''
      assert(a.metadataText:find(a.Text("shareHelp","'''+locale+'''"),1,true))
      rating.sampleCount=29; render(); assert(not r.tip.min:find("500",1,true))
      rating.sampleCount=30; rating.sourceStatus="unavailable"; render()
      assert(not r.tip.min:find("500",1,true))
      local foreign=CreateFrame("Frame"); GameTooltip:SetOwner(foreign); GameTooltip:SetText("foreign"); GameTooltip:Show()
      item.sourceStatus="unavailable"; render()
      assert(GameTooltip.shown and GameTooltip.text=="foreign")
    ''')
