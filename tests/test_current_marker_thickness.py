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
          local labelY=r.min.point[5]
          for _,value in ipairs({{0,50,100}}) do
            local item={{currentShare=value,axisMaxShare=100,axisVerified=true,
              axisProvenance="scale",sourceStatus="verified",
              reference={{minShare=value,meanShare=value,maxShare=value}}}}
            a.Render({{shareComparison={{crit=item}}}})
            near(r.markerCurrent.width*physical,5)
            near(r.markerMean.width*physical,3)
            near(r.markerMin.width*physical,2)
            near(r.markerMax.width*physical,2)
            near(r.outlineCurrent.width*physical,7)
            for _,role in ipairs({{"current","min","mean","max"}}) do
              local mark=r["marker"..role:sub(1,1):upper()..role:sub(2)]
              local outline=r.outline[role]
              assert(mark.shown and outline.shown)
              near((mark.height-r.track.height)*physical,8)
              near((outline.height-r.track.height)*physical,10)
              near(r.markerHit[role].height,mark.height)
              near(r.markerHit[role].width*physical,8)
              near(mark.point[4],r.markerInset+(r.barWidth-2*r.markerInset)*value/100)
              near(mark.point[5],0)
              near(outline.point[4],mark.point[4]); near(outline.point[5],0)
              assert(mark.color[1]==1 and mark.color[2]==1 and mark.color[3]==1 and mark.color[4]==1)
              assert(outline.color[1]<0.05 and outline.color[2]<0.05 and outline.color[3]<0.05 and outline.color[4]==1)
              assert(mark.layer=="OVERLAY" and outline.layer=="OVERLAY")
              if role~="current" then
                assert(r.outlineCurrent.sublevel>mark.sublevel,"current outline must cover coincident references")
              end
              -- The independent numeric labels remain pointer-accessible.
              local hit=r.hit[role]
              local s=hit:GetEffectiveScale()
              local x=(hit:GetLeft()+hit:GetRight())*s/2
              local y=(hit:GetTop()+hit:GetBottom())*s/2
              assert(PointerTarget(x,y,true)==hit,role)
              assert(PointerTarget(x,y,false)==hit,role)
            end
            assert(r.markerCurrent.sublevel>r.outlineCurrent.sublevel)
            near(r.label.point[5],headingY); near(r.track.point[5],trackY); near(r.min.point[5],labelY)
          end
        end
      end
    ''')
