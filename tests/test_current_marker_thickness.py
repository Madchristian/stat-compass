"""Current ink is wider, not taller; reference geometry stays unchanged."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_footer_pointer import POINTER


@pytest.mark.parametrize("skin", ["default", "flat"])
@pytest.mark.parametrize("physical_height", [1080, 1440, 2160])
def test_current_thickness_without_vertical_reflow(skin, physical_height):
    lua = load_runtime(POINTER + f'''
      UIParent.scale=0.64
      UIParent.top=768/UIParent.scale
      UIParent.right=(768*16/9)/UIParent.scale
      function GetPhysicalScreenSize() return {physical_height}*16/9,{physical_height} end
    ''')
    run(lua, f'''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      a.SetSkin("{skin}")
      local function near(x,y) assert(math.abs(x-y)<0.00001, tostring(x).." != "..tostring(y)) end
      for _,height in ipairs({{420,424,530,750}}) do
        for _,scale in ipairs({{0.8,1,1.25}}) do
          a.panel:SetScale(scale); a.Layout(450,height)
          local r=a.rows[1]
          local physical=a.panel:GetEffectiveScale()*{physical_height}/768
          local headingY=r.label.point[5]
          local trackY=r.track.point[5]
          local labelY=r.status.point[5]
          for _,value in ipairs({{0,50,100}}) do
            local item={{currentRating=value,targetRating=value,lowRating=value,highRating=value,
              targetPercent=20,personal=true,sampleCount=30,sourceStatus="verified"}}
            a.Render({{ratingTarget={{crit=item}}}})
            local mark,outline=r.markerTarget,r.outlineTarget
            near(mark.width*physical,3); near(outline.width*physical,5)
            assert(mark.shown and outline.shown)
            near((mark.height-r.track.height)*physical,8)
            near((outline.height-r.track.height)*physical,10)
            near(r.markerHit.target.height,mark.height)
            near(r.markerHit.target.width*physical,12)
            near(mark.point[4],r.markerInset+(r.barWidth-2*r.markerInset)*value/r.axis)
            near(mark.point[5],0); near(outline.point[4],mark.point[4])
            for k=1,3 do assert(mark.color[k]==1) end
            assert(outline.color[1]<0.05 and outline.width>mark.width)
            for _,role in ipairs({{"current","target"}}) do
              local hit=r.hit[role]; local scale=hit:GetEffectiveScale()
              local x=(hit:GetLeft()+hit:GetRight())*scale/2
              local y=(hit:GetTop()+hit:GetBottom())*scale/2
              assert(PointerTarget(x,y,true)==hit,role)
              assert(PointerTarget(x,y,false)==hit,role)
            end
            near(r.label.point[5],headingY); near(r.track.point[5],trackY); near(r.status.point[5],labelY)
          end
        end
      end
    ''')
