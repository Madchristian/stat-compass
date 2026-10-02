"""Combined-candidate verification; real Lua 5.1, synthetic client lifecycle."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_controls import CONTROLS_MOCK


@pytest.mark.parametrize("initialize_event", ["ADDON_LOADED", "PLAYER_LOGIN"])
def test_controls_initialize_before_lazy_character_and_after_savedvariables(initialize_event):
    lua = load_runtime(CONTROLS_MOCK + '''
      savedCharacter, savedPaperDoll = CharacterFrame, PaperDollFrame
      CharacterFrame, PaperDollFrame = nil, nil
    ''')
    run(lua, f'''
      -- Model SavedVariables becoming authoritative after TOC execution.
      StatCompassDB={{mode="mythic",skin="flat",minimapShown=false,minimapAngle=450}}
      Fire("{initialize_event}","StatCompass")
      local A=StatCompass
      assert(not A.panel and A.minimapButton and #Settings.categories==1)
      assert(not A.minimapButton:IsShown() and A.settings.minimapAngle==90)
      Settings.OpenToCategory(A.settingsCategory:GetID())
      A.options.skin.scripts.OnClick()
      assert(A.settings.skin=="default" and A.settings.mode=="mythic")
      A.options.minimap.scripts.OnClick()
      assert(A.minimapButton:IsShown())
      CharacterFrame, PaperDollFrame = savedCharacter, savedPaperDoll
      Fire("ADDON_LOADED","Blizzard_CharacterUI")
      assert(A.panel and not A.visible)
      A.minimapButton.scripts.OnClick(A.minimapButton,"LeftButton")
      assert(A.visible and A.buttons[2].selected and A.buttons[3].selected)
      assert(A.rows[1].current.text=="Unknown")
      assert(A.GetTarget(71,"mythic")==nil)
      local frames=widgets.frames
      Fire("PLAYER_LOGIN")
      assert(#Settings.categories==1 and widgets.frames==frames)
      assert(StatCompassDB.minimapAngle==90 and StatCompassDB.mode=="mythic")
    ''')


@pytest.mark.parametrize("physical_height", [1080, 1440, 2160])
def test_minimap_opens_preserved_virtual_coordinate_panel(physical_height):
    lua = load_runtime(CONTROLS_MOCK + f'''
      UIParent.scale=0.64
      UIParent.top=768/UIParent.scale
      UIParent.right=(768*16/9)/UIParent.scale
      function GetPhysicalScreenSize() return {physical_height}*16/9,{physical_height} end
      CharacterFrame:SetBounds(20,420,100,524)
    ''')
    run(lua, '''
      Fire("ADDON_LOADED","StatCompass")
      local A=StatCompass
      A.minimapButton.scripts.OnClick(A.minimapButton,"LeftButton")
      assert(A.visible and A.panel:IsVisible())
      local _,ph=GetPhysicalScreenSize()
      local function px(frame,method)
        return frame[method](frame)*frame:GetEffectiveScale()*ph/768
      end
      assert(math.abs(px(A.panel,"GetTop")-px(CharacterFrame,"GetTop"))<0.01)
      assert(math.abs(px(A.panel,"GetBottom")-px(CharacterFrame,"GetBottom"))<0.01)
      assert(px(A.panel,"GetLeft")>=0 and px(A.panel,"GetRight")<=ph*16/9)
      A.minimapButton.scripts.OnClick(A.minimapButton,"RightButton")
      A.options.skin.scripts.OnClick()
      assert(A.settings.skin=="flat" and A.buttons[4].selected and A.visible)
      assert(A.rows[1].min.text==A.Text("unknown","enUS"))
    ''')
