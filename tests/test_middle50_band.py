"""UI-only provider low/high handoff, executed with actual Lua 5.1."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_footer_pointer import POINTER

INVALID = [
    'item.reference.lowShare=nil; item.reference.highShare=nil',
    'item.reference.lowShare=nil', 'item.reference.highShare=nil',
    'item.reference.lowShare=false', 'item.reference.highShare="70"',
    'item.reference.lowShare=70.1', 'item.reference.lowShare=-1',
    'item.reference.highShare=100.1', 'item.reference.lowShare=math.huge',
    'item.reference.highShare=-math.huge', 'item.reference.lowShare=0/0',
    'item.reference.highShare=0/0', 'item.reference.lowShare={secret=true}',
    'item.reference.highShare={secret=true}',
    'item.reference.lowShare=setmetatable({},{__lt=function() error("unsafe scalar") end})',
]


SETUP = '''
Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
a=StatCompass; r=a.rows[1]
item={currentShare=95,axisMaxShare=100,axisVerified=true,
 axisProvenance="observed scale",sourceStatus="verified",sampleCount=27,
 reference={minShare=10,meanShare=50,maxShare=90,lowShare=30,highShare=70}}
function render() a.Render({shareComparison={crit=item}}) end
render()
'''


def test_consumes_provider_middle50_with_real_behind_layer():
    lua=load_runtime()
    run(lua, SETUP+'''
      assert(r.cachedShare.bounds.low==30 and r.cachedShare.bounds.high==70,"provider band not consumed")
      assert(r.band.shown and r.bandHit:IsShown())
      local span=r.barWidth-2*r.markerInset
      assert(math.abs(r.band.width-span*0.4)<0.001)
      assert(math.abs(r.band.point[4]-(r.markerInset+span*0.3))<0.001)
      assert(r.band.layer=="ARTWORK" and r.band.sublevel<r.fill.sublevel)
      assert(r.markerMean.layer=="OVERLAY")
      assert(r.fill.color[4]<1,"opaque own fill hides underlying band")
      assert(r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      r.bandHit.scripts.OnEnter(r.bandHit)
      assert(GameTooltip.text=="Middle 50 % of top players: 30.0% – 70.0%")
      assert(not r.hoverFrame.mouseEnabled and not a.panel.mouseEnabled)
    ''')


@pytest.mark.parametrize('mutation', INVALID)
def test_invalid_band_clears_without_losing_existing_markers(mutation):
    lua=load_runtime()
    run(lua, SETUP+'''
      assert(r.band.shown)
      r.bandHit.scripts.OnEnter(r.bandHit)
    '''+mutation+'''
      render()
      assert(not r.band.shown and not r.bandCue.shown and not r.bandHit:IsShown())
      assert(r.cachedShare.bounds.low==nil and r.cachedShare.bounds.high==nil)
      assert(r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      assert(r.fill.color[4]==1 and not GameTooltip.shown)
      assert(not a.tooltipOpen)
    ''')


@pytest.mark.parametrize('mutation', [
    'item.sourceStatus=false', 'item.sourceStatus="unverified"',
    'item.sourceStatus={secret=true}', 'item.axisVerified=false',
    'item.axisVerified={secret=true}', 'item.axisMaxShare=0',
    'item.axisMaxShare=-1', 'item.axisMaxShare=math.huge',
    'item.axisMaxShare=0/0', 'item.axisMaxShare={secret=true}',
    'item.axisProvenance=nil', 'item.reference={secret=true}',
    'item.reference=false',
    'item.reference=setmetatable({},{__index=function() error("unsafe reference") end})',
    'item=setmetatable({},{__index=function() error("unsafe item") end})',
])
def test_invalid_source_axis_or_containers_fail_closed(mutation):
    lua=load_runtime()
    run(lua, SETUP+mutation+'''
      render()
      assert(not r.band.shown and not r.bandCue.shown and not r.bandHit:IsShown())
    ''')


@pytest.mark.parametrize('low,high', [(0,100),(0,0),(100,100),(50,50)])
def test_axis_endpoints_and_zero_width_are_truthful(low,high):
    lua=load_runtime()
    run(lua, SETUP+f'''
      item.reference.lowShare={low}; item.reference.highShare={high}; render()
      local expected=(r.barWidth-2*r.markerInset)*({high}/100-{low}/100)
      assert(math.abs(r.bandWidth-expected)<0.001)
      if {low}=={high} then
        assert(not r.band.shown and r.bandCue.shown)
        assert(r.bandWidth==0 and r.bandCue.width==r.markerInset/3)
      else assert(r.band.shown and not r.bandCue.shown) end
      assert(r.bandHit:IsShown())
    ''')


@pytest.mark.parametrize('container', [
    '{secret=true}',
    'setmetatable({secret=true},{__index=function() error("secret outer") end})',
    'setmetatable({},{__index=function() error("hostile outer") end})',
    'false',
])
def test_outer_rating_container_is_not_indexed(container):
    lua=load_runtime()
    run(lua, SETUP+'a.Render({shareComparison='+container+'})'+'''
      assert(not r.band.shown and not r.bandHit:IsShown())
    ''')


def test_band_not_derived_from_markers_and_inherited_quartiles_rejected():
    lua=load_runtime()
    run(lua, SETUP+'''
      item.reference={lowShare=30,highShare=70}; render()
      assert(r.band.shown and not r.markerMean.shown and not r.markerMin.shown and not r.markerMax.shown)
      item.reference=setmetatable({minShare=10,meanShare=50,maxShare=90},
        {__index={lowShare=30,highShare=70}})
      render()
      assert(not r.band.shown and r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      item.reference=setmetatable({secret=true},{__index=function() error("secret ref") end})
      render(); assert(not r.band.shown)
    ''')


def test_band_does_not_change_glow_proximity_or_palette():
    lua=load_runtime()
    run(lua, SETUP+'''
      item.currentShare=55; render()
      local alpha=r.glow.color[4]; local red=r.fill.color[1]
      item.reference.lowShare=65; item.reference.highShare=80; render()
      assert(r.glow.color[4]==alpha and r.fill.color[1]==red)
      item.reference.highShare=nil; render()
      assert(r.glow.color[4]==alpha and r.fill.color[1]==red)
    ''')


def test_german_tooltip_refresh_skin_and_foreign_ownership():
    lua=load_runtime('GetLocale=function() return "deDE" end')
    run(lua, SETUP+'''
      for _,skin in ipairs({"flat","default","flat"}) do
        a.SetSkin(skin); render()
        assert(r.band.color[4]>0 and r.band.shown)
        r.bandHit.scripts.OnEnter(r.bandHit)
        assert(GameTooltip.text=="Mittlere 50 % der Top-Spieler: 30.0% – 70.0%")
        item.reference.highShare=80; render()
        assert(GameTooltip.text=="Mittlere 50 % der Top-Spieler: 30.0% – 80.0%")
        item.reference.highShare=70; render()
      end
      local foreign=CreateFrame("Frame"); GameTooltip:SetOwner(foreign); GameTooltip:SetText("foreign")
      item.reference.highShare=nil; render()
      assert(GameTooltip.text=="foreign" and GameTooltip.shown)
    ''')


def test_band_footer_and_marker_pointer_targets_with_valid_band():
    lua=load_runtime(POINTER)
    run(lua, SETUP+'''
      a.Render({shareComparison={crit=item,haste=item,mastery=item,versatility=item}})
      for _,height in ipairs({424,530,750,1080}) do
        a.Layout(450,height)
        local h=r.bandHit; local scale=h:GetEffectiveScale()
        local x=(h:GetLeft()+h:GetWidth()*0.15)*scale
        local y=(h:GetTop()+h:GetBottom())*scale/2
        for _,order in ipairs({true,false}) do
          assert(PointerTarget(x,y,order)==h,"band local target")
          for _,role in ipairs({"min","mean","max"}) do
            local m=r.markerHit[role]; local s=m:GetEffectiveScale()
            assert(PointerTarget((m:GetLeft()+m:GetRight())*s/2,(m:GetTop()+m:GetBottom())*s/2,order)==m,"marker priority")
          end
          for i=3,5 do
            local f=a.buttons[i]; local s=f:GetEffectiveScale()
            assert(PointerTarget((f:GetLeft()+f:GetRight())*s/2,(f:GetTop()+f:GetBottom())*s/2,order)==f,"footer priority")
          end
        end
        assert(h:GetHeight()==r.trackHeight and h:GetWidth()<r.barWidth)
      end
    ''')

