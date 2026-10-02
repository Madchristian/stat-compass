"""Physical containment regressions; mock geometry, no recommendation data."""
import pytest

from tests.test_addon import load_runtime, run


@pytest.mark.parametrize("left,right", [(300, 700), (-450, -50), (1970, 2370)])
def test_reproduced_offscreen_owner_horizontal_containment(left, right):
    lua = load_runtime()
    run(lua, f'''
      CharacterFrame:SetBounds({left},{right},30,780)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local p=StatCompass.panel
      assert(StatCompass.visible)
      local s=p:GetEffectiveScale()
      assert(p:GetLeft()*s>=0, "panel clipped at left")
      assert(p:GetRight()*s<=1920, "panel clipped at right")
      assert(math.abs(p:GetHeight()*s-750)<0.01)
      assert(math.abs(p:GetTop()*s-780)<0.01)
      assert(p.point[2]==({left}==300 and CharacterFrame or UIParent))
    ''')


@pytest.mark.parametrize(
    "root_scale,owner_scale,root_left,root_bottom,root_width,root_height,native_height",
    [
        (1, 1, 0, 0, 1920, 1080, 750),
        (0.8, 1.76, 120, 45, 1659, 777, 424),
        (1.76, 0.8, -120, -45, 1920, 1080, 424),
        (1, 1.76, 0, 0, 1659, 777, 424),
        (0.8, 1, -120, 45, 1920, 1080, 750),
    ],
)
def test_offscreen_owner_grid_preserves_height_and_skips_hidden_work(
    root_scale, owner_scale, root_left, root_bottom, root_width, root_height, native_height
):
    lua = load_runtime()
    run(lua, f'''
      local rs,os={root_scale},{owner_scale}
      local sl,sb,sw,sh={root_left},{root_bottom},{root_width},{root_height}
      local height={native_height}*os
      UIParent.scale=rs
      UIParent.left=sl/rs; UIParent.right=(sl+sw)/rs
      UIParent.bottom=sb/rs; UIParent.top=(sb+sh)/rs
      CharacterFrame.scale=os/rs
      local reads,renders=0,0
      GetHaste=function() reads=reads+1; return 15 end
      local render=StatCompass.Render
      StatCompass.Render=function(snapshot) renders=renders+1; return render(snapshot) end
      CharacterFrame:SetBounds((sl+300)/os,(sl+700)/os,sb/os,(sb+height)/os)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(reads==1 and renders==1)
      local p=StatCompass.panel
      local intervals={{{{-450,-50}},{{-200,200}},{{0,400}},{{300,700}},
        {{sw-400,sw}},{{sw-200,sw+200}},{{sw+50,sw+450}},{{-50,sw+50}}}}
      for _,interval in ipairs(intervals) do
        for _,bottom in ipairs({{sb,sb-80,sb+sh-50}}) do
          CharacterFrame:SetBounds((sl+interval[1])/os,(sl+interval[2])/os,bottom/os,(bottom+height)/os)
          assert(StatCompass.visible and p:IsVisible(), "fitting panel must stay visible")
          local ps=p:GetEffectiveScale()
          assert(p:GetLeft()*ps>=sl-0.01, "panel clipped at left")
          assert(p:GetRight()*ps<=sl+sw+0.01, "panel clipped at right")
          assert(p:GetBottom()*ps>=sb-0.01, "panel clipped at bottom")
          assert(p:GetTop()*ps<=sb+sh+0.01, "panel clipped at top")
          assert(math.abs(p:GetHeight()*ps-height)<0.01, "physical owner height changed")
          assert(reads==1 and renders==1, "geometry must not resnapshot or render")
        end
      end
      UIParent:Hide()
      for _,interval in ipairs(intervals) do
        CharacterFrame:SetBounds((sl+interval[1])/os,(sl+interval[2])/os,sb/os,(sb+height)/os)
        Fire("COMBAT_RATING_UPDATE")
        RunCallbacks()
        assert(not StatCompass.visible and not p:IsVisible())
        assert(reads==1 and renders==1, "hidden owner must not perform stat work")
      end
    ''')
