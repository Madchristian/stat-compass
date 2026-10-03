"""UI-only provider low/high handoff, executed with actual Lua 5.1."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_footer_pointer import POINTER

INVALID = [
    'item.lowRating=nil; item.highRating=nil',
    'item.lowRating=nil', 'item.highRating=nil',
    'item.lowRating=false', 'item.highRating="70"',
    'item.lowRating=70.1', 'item.lowRating=-1',
    'item.highRating=49', 'item.lowRating=math.huge',
    'item.highRating=-math.huge', 'item.lowRating=0/0',
    'item.highRating=0/0', 'item.lowRating={secret=true}',
    'item.highRating={secret=true}',
    'item.lowRating=setmetatable({},{__lt=function() error("unsafe scalar") end})',
]


SETUP = '''
Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
a=StatCompass; r=a.rows[1]
item={currentRating=95,targetRating=50,lowRating=30,highRating=70,
 targetPercent=20,personal=true,sampleCount=27,sourceStatus="verified"}
function render() a.Render({ratingTarget={crit=item}}) end
render()
'''


def test_consumes_provider_middle50_with_subtle_overlay_strip():
    lua=load_runtime()
    run(lua, SETUP+'''
      assert(r.cachedTarget.low==30 and r.cachedTarget.high==70,"provider band not consumed")
      assert(r.band.shown and r.bandHit:IsShown())
      local span=r.barWidth-2*r.markerInset
      assert(math.abs(r.band.width-span*40/r.axis)<0.001)
      assert(math.abs(r.band.point[4]-(r.markerInset+span*30/r.axis))<0.001)
      assert(r.band.layer=="ARTWORK" and r.band.sublevel>r.fill.sublevel)
      assert(r.markerTarget.layer=="OVERLAY")
      assert(r.fill.color[4]==1 and r.band.height==2,"thin overlay preserves the solid own fill")
      assert(r.markerTarget.shown)
      r.bandHit.scripts.OnEnter(r.bandHit)
      assert(GameTooltip.text=="Target band (P40–P60): 30 – 70 rating")
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
      assert(r.cachedTarget.low==nil and r.cachedTarget.high==nil)
      assert(r.markerTarget.shown)
      assert(r.fill.color[4]==1 and not GameTooltip.shown)
      assert(not a.tooltipOpen)
    ''')


@pytest.mark.parametrize('mutation', [
    'item.sourceStatus=false', 'item.sourceStatus="unverified"',
    'item.sourceStatus={secret=true}', 'item.targetRating=nil',
    'item.targetRating={secret=true}', 'item.targetRating=-1',
    'item.targetRating=math.huge', 'item.targetRating=0/0',
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
      item.lowRating={low}; item.highRating={high}; item.targetRating=({low}+{high})/2; render()
      local expected=(r.barWidth-2*r.markerInset)*({high}/r.axis-{low}/r.axis)
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
    run(lua, SETUP+'a.Render({ratingTarget='+container+'})'+'''
      assert(not r.band.shown and not r.bandHit:IsShown())
    ''')


def test_band_not_derived_from_target_and_inherited_endpoints_rejected():
    lua=load_runtime()
    run(lua, SETUP+'''
      item.lowRating=nil; item.highRating=nil; render()
      assert(not r.band.shown and r.markerTarget.shown)
      setmetatable(item,{__index={lowRating=30,highRating=70}}); render()
      assert(not r.band.shown and r.markerTarget.shown)
      item=setmetatable({secret=true},{__index=function() error("secret ref") end})
      render(); assert(not r.band.shown)
    ''')


def test_band_does_not_change_glow_proximity_or_palette():
    lua=load_runtime()
    run(lua, SETUP+'''
      item.currentRating=55; render()
      local red=r.fill.color[1]
      item.lowRating=65; item.highRating=80; render()
      assert(r.glow==nil and r.fill.color[1]==red)
      item.highRating=nil; render()
      assert(r.glow==nil and r.fill.color[1]==red)
    ''')


def test_german_tooltip_refresh_skin_and_foreign_ownership():
    lua=load_runtime('GetLocale=function() return "deDE" end')
    run(lua, SETUP+'''
      for _,skin in ipairs({"flat","default","flat"}) do
        a.SetSkin(skin); render()
        assert(r.band.color[4]>0 and r.band.shown)
        r.bandHit.scripts.OnEnter(r.bandHit)
        assert(GameTooltip.text=="Zielspanne (P40–P60): 30 – 70 Wertung")
        item.highRating=80; render()
        assert(GameTooltip.text=="Zielspanne (P40–P60): 30 – 80 Wertung")
        item.highRating=70; render()
      end
      local foreign=CreateFrame("Frame"); GameTooltip:SetOwner(foreign); GameTooltip:SetText("foreign")
      item.highRating=nil; render()
      assert(GameTooltip.text=="foreign" and GameTooltip.shown)
    ''')


def test_band_footer_and_marker_pointer_targets_with_valid_band():
    lua=load_runtime(POINTER)
    run(lua, SETUP+'''
      item.lowRating=300; item.targetRating=500; item.highRating=700
      a.Render({ratingTarget={crit=item,haste=item,mastery=item,versatility=item}})
      for _,height in ipairs({424,530,750,1080}) do
        a.Layout(450,height)
        local h=r.bandHit; local scale=h:GetEffectiveScale()
        -- Noncoincident interior; narrow/coincident bands use target tooltip.
        local x=(h:GetLeft()+h:GetWidth()*0.15)*scale
        local y=(h:GetTop()+h:GetBottom())*scale/2
        for _,order in ipairs({true,false}) do
          assert(PointerTarget(x,y,order)==h,"band local target")
          for _,role in ipairs({"target"}) do
            local m=r.markerHit[role]; local s=m:GetEffectiveScale()
            assert(PointerTarget((m:GetLeft()+m:GetRight())*s/2,(m:GetTop()+m:GetBottom())*s/2,order)==m,"marker priority")
          end
          for i=1,3 do
            local f=a.buttons[i]; local s=f:GetEffectiveScale()
            assert(PointerTarget((f:GetLeft()+f:GetRight())*s/2,(f:GetTop()+f:GetBottom())*s/2,order)==f,"footer priority")
          end
        end
        assert(h:GetHeight()==r.trackHeight and h:GetWidth()<r.barWidth)
      end
    ''')

