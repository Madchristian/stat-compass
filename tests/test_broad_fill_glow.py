"""Physical halo footprint; geometry proxies do not replace native acceptance."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_rating_target_ui import SETUP


@pytest.mark.parametrize('scale', [0.64, 0.8, 1, 1.2])
@pytest.mark.parametrize('density', [1, 1080 / 768, 2160 / 768])
def test_broad_halo_physical_falloff_corners_and_clearance(scale, density):
    lua = load_runtime()
    run(lua, SETUP + f'a.panel:SetScale({scale}); a.pixelDensity={density};' + '''
      item.currentRating=670; render()
      local physical=a.panel:GetEffectiveScale()*a.pixelDensity
      for _,height in ipairs({420,424,530,750,1080}) do
        a.Layout(360,height)
        local radius=r.fillGlowTop.height
        if height>=750 then
          assert(radius*physical>=8 and radius*physical<=10,"halo still only a thin outline")
        else assert(radius*physical>=3-0.00001) end
        assert(r.fillGlowLeft.width==radius and r.fillGlowRight.width==radius)
        assert(r.fillGlowLeft.height==r.track.height and r.fillGlowRight.height==r.track.height)
        assert(r.fillGlowTop.width==r.fill.width and r.fillGlowBottom.width==r.fill.width)
        assert(#r.fillGlowCorners==24)
        for i,corner in ipairs(r.fillGlowCorners) do
          assert(math.abs(corner.width*6-radius)<0.00001 and corner.height==radius)
          assert(corner.shown and corner.sublevel<r.fill.sublevel)
          assert(corner.gradient[1]=="VERTICAL")
          assert(math.min(corner.gradient[2].a,corner.gradient[3].a)==0)
          local peak=math.max(corner.gradient[2].a,corner.gradient[3].a)
          assert(peak<0.65)
          local slice=(i-1)%6+1
          assert(math.abs(peak-0.65*(1-(slice-0.5)/6))<0.00001)
          assert(corner.point[2]==r.fill and corner.point[3]==corner.fillAnchor)
          assert(math.abs(corner.point[4]-corner.direction*(slice-1)*radius/6)<0.00001)
          assert(corner.point[5]==0)
          local upper=i<=12
          assert((corner.gradient[2].a>0)==upper)
        end
        local trackTop=-r.track.point[5]
        assert(trackTop-radius>=-r.current.point[5]+r.current:GetStringHeight()+2-0.00001)
        assert(-r.status.point[5]>=trackTop+r.track.height+radius+2-0.00001)
        for i,row in ipairs(a.rows) do
          if a.rows[i+1] then
            assert(-a.rows[i+1].label.point[5]>=-row.status.point[5]+row.status:GetStringHeight()+2-0.00001)
          end
        end
      end
      for _,value in ipairs({600,670,671,2000,2500,599,0}) do
        item.currentRating=value; render()
        for _,part in ipairs(r.fillGlowParts) do assert(part.shown==(value>=600)) end
      end
      item.currentRating=650; render(); item.highRating=nil; render()
      for _,part in ipairs(r.fillGlowParts) do assert(not part.shown) end
    ''')
