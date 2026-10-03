"""Rating targets replace share-primary display; synthetic payload only."""
from tests.test_addon import load_runtime, run
from tests.test_rating_target_ui import SETUP


def test_rating_primary_never_falls_back_to_shares_or_effect_percent():
    lua=load_runtime()
    run(lua, SETUP+'''
      payload.current={crit=99}; payload.shareComparison={crit={currentShare=35.9}}
      payload.ratingComparison={crit={currentRating=1014}}; render()
      assert(r.current.text=="400" and r.target.text=="Target 638")
      payload.ratingTarget=nil; render()
      assert(r.current.text=="Unknown" and r.target.text=="")
      assert(not r.track.shown and not r.markerTarget.shown)
    ''')


def test_unavailable_hides_every_graphic_and_clears_owned_marker_tooltip():
    lua=load_runtime()
    run(lua, SETUP+'''
      r.markerHit.target.scripts.OnEnter(r.markerHit.target)
      item.sourceStatus="unavailable"; render()
      for _,t in ipairs({r.track,r.fill,r.band,r.bandCue,r.markerTarget,r.outlineTarget}) do assert(not t.shown) end
      for _,h in pairs(r.markerHit) do assert(not h:IsShown()) end
      assert(not r.bandHit:IsShown() and not r.hit.target:IsShown())
      assert(not GameTooltip.shown)
      assert(r.current.text=="400" and r.target.text=="")
      assert(r.status.text==a.Text("targetUnavailable","enUS"))
    ''')
