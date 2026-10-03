"""Decorative, static fill-edge glow, not a performance recommendation."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_rating_target_ui import SETUP


@pytest.mark.parametrize('skin', ['default', 'flat'])
def test_static_fill_glow_inclusive_band_and_above_transitions(skin):
    lua = load_runtime()
    run(lua, SETUP + f'a.SetSkin("{skin}");' + '''
      assert(_VERSION=="Lua 5.1")
      for _,key in ipairs(a.statOrder) do payload.ratingTarget[key]=item end
      for _,value in ipairs({600,638,670,671,2000,2500,1e308,599,0}) do
        item.currentRating=value; render()
        for _,row in ipairs(a.rows) do
          assert(row.fillGlowTop and row.fillGlowBottom, "static fill edge glow missing")
          for _,edge in ipairs({row.fillGlowTop,row.fillGlowBottom}) do
            assert(edge, "static fill edge glow missing")
            assert(edge.shown==(value>=600))
            assert(edge.layer=="ARTWORK" and edge.sublevel<row.band.sublevel)
            assert(edge.texture=="Interface\\\\Buttons\\\\WHITE8X8")
            assert(edge.color[1]==1 and edge.color[4]==1)
            assert(edge.gradient[1]=="VERTICAL")
            local first,last=edge.gradient[2],edge.gradient[3]
            assert(first.r==row.palette[1] and last.g==row.palette[2] and last.b==row.palette[3])
            assert(math.max(first.a,last.a)==0.65 and math.min(first.a,last.a)==0)
            if edge.shown then assert(edge.width==row.fill.width) end
          end
          if value>0 then assert(row.fill.width==row.barWidth*math.min(value/2000,1))
          else assert(not row.fill.shown) end
        end
      end
      item.currentRating=670; render()
      a.panel:SetScale(1.2); a.Layout(360,424)
      assert(r.fillGlowTop.height==r.markerInset)
      assert(r.fillGlowTop.width==r.fill.width)
      assert(r.fillGlowTop.point[1]=="BOTTOMLEFT" and r.fillGlowTop.point[3]=="TOPLEFT")
      assert(r.fillGlowBottom.point[1]=="TOPLEFT" and r.fillGlowBottom.point[3]=="BOTTOMLEFT")
      a.SetSkin("default"); a.SetSkin("flat")
      assert(r.fillGlowTop.shown and r.fillGlowBottom.shown)
    ''')


@pytest.mark.parametrize('mutation', [
    'item.lowRating=nil', 'item.highRating={secret=true}', 'item.lowRating=700',
    'item.sourceStatus="unavailable"', 'item.targetRating=0/0',
    'item.currentRating=nil', 'item.currentRating={secret=true}',
    'item.currentRating=0; item.targetRating=0; item.lowRating=0; item.highRating=0',
])
def test_invalid_or_zero_transition_clears_all_glow(mutation):
    lua = load_runtime()
    run(lua, SETUP + '''
      item.currentRating=670; render()
      assert(r.fillGlowTop and r.fillGlowTop.shown, "glow missing before transition")
    ''' + mutation + '''; render()
      for _,part in ipairs(r.fillGlowParts) do assert(not part.shown) end
      a.ApplySkin(); a.Layout(360,424)
      for _,part in ipairs(r.fillGlowParts) do assert(not part.shown) end
    ''')
