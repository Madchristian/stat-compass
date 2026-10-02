"""UI-only provider low/high handoff, executed with actual Lua 5.1."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_footer_pointer import POINTER

INVALID = [
    'item.reference.lowRating=nil; item.reference.highRating=nil',
    'item.reference.lowRating=nil', 'item.reference.highRating=nil',
    'item.reference.lowRating=false', 'item.reference.highRating="700"',
    'item.reference.lowRating=701', 'item.reference.lowRating=-1',
    'item.reference.highRating=1001', 'item.reference.lowRating=math.huge',
    'item.reference.highRating=-math.huge', 'item.reference.lowRating=0/0',
    'item.reference.highRating=0/0', 'item.reference.lowRating={secret=true}',
    'item.reference.highRating={secret=true}',
    'item.reference.lowRating=setmetatable({},{__lt=function() error("unsafe scalar") end})',
]


SETUP = '''
Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
a=StatCompass; r=a.rows[1]
item={currentRating=950,axisMaxRating=1000,axisVerified=true,
 axisProvenance="observed scale",sourceStatus="verified",sampleCount=27,
 reference={minRating=100,meanRating=500,maxRating=900,lowRating=300,highRating=700}}
function render() a.Render({ratingComparison={crit=item}}) end
render()
'''


def test_consumes_provider_middle50_with_real_behind_layer():
    lua=load_runtime()
    run(lua, SETUP+'''
      assert(r.cachedRating.bounds.low==300 and r.cachedRating.bounds.high==700,"provider band not consumed")
      assert(r.band.shown and r.bandHit:IsShown())
      local span=r.barWidth-2*r.markerInset
      assert(math.abs(r.band.width-span*0.4)<0.001)
      assert(math.abs(r.band.point[4]-(r.markerInset+span*0.3))<0.001)
      assert(r.band.layer=="ARTWORK" and r.band.sublevel<r.fill.sublevel)
      assert(r.markerMean.layer=="OVERLAY")
      assert(r.fill.color[4]<1,"opaque own fill hides underlying band")
      assert(r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      r.bandHit.scripts.OnEnter(r.bandHit)
      assert(GameTooltip.text=="Middle 50 % of top players: 300 – 700")
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
      assert(r.cachedRating.bounds.low==nil and r.cachedRating.bounds.high==nil)
      assert(r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      assert(r.fill.color[4]==1 and not GameTooltip.shown)
      assert(not a.tooltipOpen)
    ''')


@pytest.mark.parametrize('mutation', [
    'item.sourceStatus=false', 'item.sourceStatus="unverified"',
    'item.sourceStatus={secret=true}', 'item.axisVerified=false',
    'item.axisVerified={secret=true}', 'item.axisMaxRating=0',
    'item.axisMaxRating=-1', 'item.axisMaxRating=math.huge',
    'item.axisMaxRating=0/0', 'item.axisMaxRating={secret=true}',
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


@pytest.mark.parametrize('low,high', [(0,1000),(0,0),(1000,1000),(500,500)])
def test_axis_endpoints_and_zero_width_are_truthful(low,high):
    lua=load_runtime()
    run(lua, SETUP+f'''
      item.reference.lowRating={low}; item.reference.highRating={high}; render()
      local expected=(r.barWidth-2*r.markerInset)*({high}/1000-{low}/1000)
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
    run(lua, SETUP+'a.Render({ratingComparison='+container+'})'+'''
      assert(not r.band.shown and not r.bandHit:IsShown())
    ''')


def test_band_not_derived_from_markers_and_inherited_quartiles_rejected():
    lua=load_runtime()
    run(lua, SETUP+'''
      item.reference={lowRating=300,highRating=700}; render()
      assert(r.band.shown and not r.markerMean.shown and not r.markerMin.shown and not r.markerMax.shown)
      item.reference=setmetatable({minRating=100,meanRating=500,maxRating=900},
        {__index={lowRating=300,highRating=700}})
      render()
      assert(not r.band.shown and r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      item.reference=setmetatable({secret=true},{__index=function() error("secret ref") end})
      render(); assert(not r.band.shown)
    ''')


def test_band_does_not_change_glow_proximity_or_palette():
    lua=load_runtime()
    run(lua, SETUP+'''
      item.currentRating=550; render()
      local alpha=r.glow.color[4]; local red=r.fill.color[1]
      item.reference.lowRating=650; item.reference.highRating=800; render()
      assert(r.glow.color[4]==alpha and r.fill.color[1]==red)
      item.reference.highRating=nil; render()
      assert(r.glow.color[4]==alpha and r.fill.color[1]==red)
    ''')


def test_german_tooltip_refresh_skin_and_foreign_ownership():
    lua=load_runtime('GetLocale=function() return "deDE" end')
    run(lua, SETUP+'''
      for _,skin in ipairs({"flat","default","flat"}) do
        a.SetSkin(skin); render()
        assert(r.band.color[4]>0 and r.band.shown)
        r.bandHit.scripts.OnEnter(r.bandHit)
        assert(GameTooltip.text=="Mittlere 50 % der Top-Spieler: 300 – 700")
        item.reference.highRating=800; render()
        assert(GameTooltip.text=="Mittlere 50 % der Top-Spieler: 300 – 800")
        item.reference.highRating=700; render()
      end
      local foreign=CreateFrame("Frame"); GameTooltip:SetOwner(foreign); GameTooltip:SetText("foreign")
      item.reference.highRating=nil; render()
      assert(GameTooltip.text=="foreign" and GameTooltip.shown)
    ''')


def test_band_footer_and_marker_pointer_targets_with_valid_band():
    lua=load_runtime(POINTER)
    run(lua, SETUP+'''
      a.Render({ratingComparison={crit=item,haste=item,mastery=item,versatility=item}})
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

