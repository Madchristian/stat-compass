"""WoW effective scale maps to a 768-high virtual screen, not pixels.

Installed EllesmereUI_Popups.lua:57-59 documents this boundary and
EllesmereUI_Startup.lua:59-71 sets UIParent scales as low as 768/1440.
"""
import pytest
from tests.test_addon import load_runtime, run


@pytest.mark.parametrize("physical_height,root_scale", [
    (1080, 0.64), (1440, 0.64), (2160, 0.64),
    (1080, 768/1080), (1440, 768/1440), (2160, 0.4),
])
def test_native_character_panel_visible_in_virtual_screen(physical_height, root_scale):
    lua = load_runtime(f'''
      UIParent.scale={root_scale}
      UIParent.top=768/UIParent.scale
      UIParent.right=(768*16/9)/UIParent.scale
      function GetPhysicalScreenSize() return {physical_height}*16/9,{physical_height} end
      CharacterFrame:SetBounds(20,420,100,524)
    ''')
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.visible and StatCompass.panel:IsVisible(),
        "native 424-unit character panel must not disappear at real WoW UI scale")
      local p=StatCompass.panel
      local _,ph=GetPhysicalScreenSize()
      local density=ph/768
      local function px(frame,method) return frame[method](frame)*frame:GetEffectiveScale()*density end
      assert(math.abs(px(p,"GetTop")-px(CharacterFrame,"GetTop"))<0.01)
      assert(math.abs(px(p,"GetBottom")-px(CharacterFrame,"GetBottom"))<0.01)
      assert(px(p,"GetLeft")>=0 and px(p,"GetRight")<=ph*16/9)
      local width=p:GetWidth()*p:GetEffectiveScale()*density
      assert(width>=360 and width<=500)
      assert(p:GetHeight()>=420)
    ''')
