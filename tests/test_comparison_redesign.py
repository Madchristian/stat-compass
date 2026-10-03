"""Rating display scale, palette and extreme typography regressions."""
from tests.test_addon import load_runtime, run
from tests.test_rating_target_ui import SETUP


def test_rating_axis_and_percent_fallback():
    lua=load_runtime()
    run(lua, SETUP+'''
      assert(r.axis==2000 and r.current.text=="400")
      assert(r.fill.shown and r.markerTarget.shown)
      assert(math.abs(r.fill.width/r.barWidth-400/2000)<0.001)
      item.currentRating=900; render()
      assert(r.axis==2000 and r.fill.width/r.barWidth>638/r.axis)
      assert(r.fill.color[1]==r.palette[1] and r.glow==nil)
      r.hit.target.scripts.OnEnter(r.hit.target)
      assert(GameTooltip.text:find("21.5%",1,true))
      a.SetSkin("flat"); a.SetSkin("default")
      assert(r.markerTarget.shown and r.fill.shown)
    ''')


def test_invalid_target_and_symmetric_color():
    lua=load_runtime()
    run(lua, SETUP+'''
      local center=r.fill.color[1]
      for _,value in ipairs({500,638,800}) do
        item.currentRating=value; render()
        assert(r.fill.color[1]==center and r.glow==nil)
      end
      item.lowRating=638; item.highRating=638; item.currentRating=638; render()
      assert(r.bandCue.shown and r.status.text=="fits")
      item.targetRating=nil; render()
      assert(not r.fill.shown and not r.markerTarget.shown and r.current.text=="638")
    ''')


def test_extreme_rating_labels_and_missing_target_in_both_locales():
    for locale in ('enUS', 'deDE'):
        lua=load_runtime('GetLocale=function() return "'+locale+'" end')
        run(lua, SETUP+'''
          CharacterFrame:SetBounds(20,380,0,420)
          item.currentRating=1e308; item.targetRating=1e308; item.highRating=1e308; render()
          assert(r.axis<math.huge and r.fill.shown and r.fill.width<=r.barWidth)
          for _,font in ipairs({r.label,r.current,r.target,r.status}) do
            assert(font:GetStringWidth()<=font.width,font.text)
          end
          assert(r.markerTarget.point[4]>=r.markerInset and r.markerTarget.point[4]<=r.barWidth-r.markerInset)
          item.sourceStatus="unavailable"; render()
          assert(not r.fill.shown and not r.markerTarget.shown and r.target.text=="")
        ''')
