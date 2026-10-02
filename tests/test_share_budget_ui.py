"""Synthetic-only share handoff; production Lua 5.1 Core and UI."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_followup import synthetic_manifest, NOW
from tests.test_tools import load_tool

SETUP = '''
Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
a=StatCompass; r=a.rows[1]
item={currentShare=35.9,axisMaxShare=55,axisVerified=true,
 axisProvenance="scale: max(EU top 30 maximum share, own share) + 10%",
 sourceStatus="verified",sampleCount=30,
 reference={minShare=20,lowShare=31.1,meanShare=36,highShare=43.3,maxShare=50}}
rating={currentRating=1014,axisMaxRating=1600,axisVerified=true,
 axisProvenance="observed rating scale",sourceStatus="verified",sampleCount=30,
 reference={minRating=500,meanRating=1100,maxRating=1500}}
function render() a.Render({specID=71,current={crit=99},shareComparison={crit=item},ratingComparison={crit=rating}}) end
render()
'''

def test_share_budget_primary_and_rating_tooltips():
    lua=load_runtime()
    run(lua, SETUP+'''
      assert(r.axis==55,"bars must consume shares, not ratings")
      assert(r.current.text=="36%", "main number is budget share")
      assert(r.band.shown and r.fill.shown)
      assert(r.fill.color[4]<0.5,"IQR band must remain the primary reference")
      assert(math.abs(r.fill.width/r.barWidth-35.9/55)<0.00001)
      assert(math.abs(r.band.width/(r.barWidth-2*r.markerInset)-(43.3-31.1)/55)<0.00001)
      assert(r.markerCurrent.width==5*r.markerInset/3) -- physical-pixel scaling preserved
      assert(r.tip.current:find("1014",1,true))
      assert(not r.tip.current:find("99",1,true))
      assert(r.tip.min:find("500",1,true) and r.tip.mean:find("1100",1,true) and r.tip.max:find("1500",1,true))
      assert(r.min.text=="Min 20.0%" and r.max.text=="Max 50.0%")
    ''')


def test_unavailable_hides_every_graphic_and_clears_owned_marker_tooltip():
    lua=load_runtime()
    run(lua, SETUP+'''
      r.markerHit.mean.scripts.OnEnter(r.markerHit.mean)
      item.sourceStatus="unavailable"; render()
      for _,t in ipairs({r.track,r.fill,r.band,r.bandCue,r.glow,r.markerCurrent,r.markerMin,r.markerMean,r.markerMax,r.outlineCurrent,r.outline.min,r.outline.mean,r.outline.max}) do assert(not t.shown) end
      for _,h in pairs(r.markerHit) do assert(not h:IsShown()) end
      assert(not r.bandHit:IsShown())
      assert(not GameTooltip.shown,"hidden marker must release its owned tooltip")
      assert(r.current.text=="36%" and r.axisStatus.text==a.Text("shareAxisUnavailable","enUS"))
      assert(r.tip.current:find("no comparison",1,true))
      assert(not r.tip.min:find("500",1,true))
    ''')
