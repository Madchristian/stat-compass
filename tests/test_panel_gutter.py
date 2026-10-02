"""Physical ten-pixel owner gutter, independently of virtual viewport/scale."""
import pytest
from tests.test_addon import load_runtime, run


@pytest.mark.parametrize("physical", [1080, 1440, 2160])
@pytest.mark.parametrize("root_scale,owner_scale", [(0.64, 1), (0.8, 0.8), (1, 0.75)])
@pytest.mark.parametrize("side", ["right", "left", "fallback", "tight"])
def test_gutter_and_bounds(physical, root_scale, owner_scale, side):
    lua = load_runtime(f'''
      UIParent.scale={root_scale}; UIParent.top=768/{root_scale}
      UIParent.right=(768*16/9)/{root_scale}
      GetPhysicalScreenSize=function() return {physical}*16/9,{physical} end
      CharacterFrame:SetScale({owner_scale})
      local density={physical}/768
      local os=CharacterFrame:GetEffectiveScale()*density
      local screen={physical}*16/9
      local left,right=30,430
      if "{side}"=="left" then left,right=screen-430,screen-30 end
      if "{side}"=="fallback" then left,right=30,screen-30 end
      if "{side}"=="tight" then
        -- Room for the 360px panel plus 5px gutter, not the preferred 10px.
        right=screen-8*{root_scale}*density-365; left=right-400
      end
      CharacterFrame:SetBounds(left/os,right/os,100/os,700/os)
    ''')
    run(lua, f'''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; local p=a.panel; assert(a.visible)
      local density={physical}/768
      local ps=p:GetEffectiveScale()*density
      local os=CharacterFrame:GetEffectiveScale()*density
      local gap
      if "{side}"=="right" or "{side}"=="tight" then
        assert(p.point[1]=="TOPLEFT" and p.point[2]==CharacterFrame)
        gap=p:GetLeft()*ps-CharacterFrame:GetRight()*os
      elseif "{side}"=="left" then
        assert(p.point[1]=="TOPRIGHT" and p.point[2]==CharacterFrame)
        gap=CharacterFrame:GetLeft()*os-p:GetRight()*ps
      else assert(p.point[2]==UIParent) end
      if gap then assert(math.abs(gap-("{side}"=="tight" and 5 or 10))<0.001,"incorrect physical gutter: "..gap) end
      assert(p:GetLeft()*ps>=-0.001)
      assert(p:GetRight()*ps<={physical}*16/9+0.001)
      assert(p:GetBottom()*ps>=-0.001 and p:GetTop()*ps<={physical}+0.001)
    ''')
