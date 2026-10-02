"""Real Lua 5.1, pinned Retail API names, synthetic widget geometry."""
from tests.test_addon import load_runtime, run
import pytest
from pathlib import Path


@pytest.mark.parametrize("locale", ["enUS", "deDE", "frFR"])
def test_controls_localized_tooltip_and_direct_category(locale):
    lua = load_runtime(CONTROLS_MOCK + f'GetLocale=function() return "{locale}" end')
    run(lua, '''
      Fire("ADDON_LOADED","StatCompass")
      local A=StatCompass
      -- Direct AddOns-list opening, no launcher or Character invocation first.
      Settings.OpenToCategory(A.settingsCategory:GetID())
      assert(not A.visible and not widgets.characterOpens)
      assert(A.options.skin.caption.text:find(A.Text("skin",GetLocale()),1,true))
      A.minimapButton.scripts.OnEnter(A.minimapButton)
      assert(GameTooltip.text==A.Text("title",GetLocale()).."\\n"..A.Text("minimapHelp",GetLocale()))
      A.minimapButton.scripts.OnLeave()
      assert(not GameTooltip.shown)
      A.SetMinimapShown(false)
      A.options.canvas:Hide(); A.options.canvas:SetParent(nil)
      Settings.OpenToCategory(123)
      assert(A.options.minimap.caption.text:find(A.Text("hidden",GetLocale()),1,true))
      assert(not A.options.canvas.scripts.OnUpdate)
    ''')



def test_controls_documentation_contract():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "There is no minimap button" not in readme
    assert "kein Minikartensymbol" not in readme
    for file in ["README.md", "StatCompass/README.txt", "StatCompass/README.de.txt"]:
        text = (root / file).read_text(encoding="utf-8")
        assert "AddOns" in text and ("Right-click" in text or "Rechtsklick" in text)
    assert "Controls.lua" in (root / "StatCompass/StatCompass.toc").read_text()



CONTROLS_MOCK = r'''
local frame = getmetatable(CharacterFrame).__index
function frame:RegisterForClicks(...) self.clicks={...} end
function frame:RegisterForDrag(...) self.drags={...} end
function frame:SetHighlightTexture(path) self.highlight=path end
function frame:SetParent(parent) self.parent=parent end
function frame:GetCenter() return self.cx or 100,self.cy or 100 end
local texture = getmetatable(CharacterFrame:CreateTexture()).__index
function texture:SetMask(path) self.mask=path end
Minimap=CreateFrame("Frame",nil,UIParent); Minimap:SetSize(140,140); Minimap:Show()
GetCursorPosition=function() return 100,200 end
function ToggleCharacter(tab,onlyShow)
  assert(tab=="PaperDollFrame" and onlyShow==true)
  widgets.characterOpens=(widgets.characterOpens or 0)+1
  CharacterFrame:Show(); PaperDollFrame:Show()
end
Settings={categories={}}
function Settings.RegisterCanvasLayoutCategory(canvas,name)
  assert(not canvas:IsShown())
  return {canvas=canvas,name=name,GetID=function() return 123 end}
end
function Settings.RegisterAddOnCategory(category) table.insert(Settings.categories,category) end
SettingsHost=CreateFrame("Frame",nil,UIParent); SettingsHost:Show()
function Settings.OpenToCategory(id)
  assert(id==123); widgets.categoryID=id
  local canvas=Settings.categories[1].canvas
  canvas:Hide(); canvas:SetParent(SettingsHost); canvas:ClearAllPoints()
  canvas:SetAllPoints(SettingsHost); canvas:Show()
end
'''


def test_registered_native_options_and_minimap_clicks():
    lua = load_runtime(CONTROLS_MOCK)
    run(lua, r'''
      local A=StatCompass
      assert(not A.minimapButton and #Settings.categories==0)
      Fire("ADDON_LOADED","OtherAddon")
      assert(not A.minimapButton and #Settings.categories==0)
      StatCompassDB={mode="mythic",skin="flat",minimapShown=true,minimapAngle=0}
      Fire("ADDON_LOADED","StatCompass")
      assert(#Settings.categories==1, "native category must register at own ADDON_LOADED")
      local canvas=Settings.categories[1].canvas
      assert(not canvas:IsShown() and not A.visible)
      local b=A.minimapButton
      assert(b and b:IsShown() and b.parent==Minimap)
      assert(b.clicks[1]=="LeftButtonUp" and b.clicks[2]=="RightButtonUp")
      assert(b.icon.texture==[[Interface\Icons\INV_Misc_Map_01]], "use the verified map icon name")
      assert(b.icon.mask==[[Interface\CharacterFrame\TempPortraitAlphaMask]])
      assert(math.abs(b.point[4]-86)<0.00001 and b.point[5]==0)
      b.scripts.OnClick(b,"LeftButton")
      assert(A.visible and widgets.characterOpens==1)
      b.scripts.OnClick(b,"LeftButton")
      assert(A.visible and widgets.characterOpens==2)
      b.scripts.OnClick(b,"RightButton")
      assert(widgets.categoryID==123 and canvas:IsShown() and canvas.parent==SettingsHost)
      assert(A.options.skin.caption.text:find(A.Text("flat","enUS"),1,true))
      A.options.skin.scripts.OnClick()
      assert(A.settings.skin=="default" and A.buttons[3].selected)
      A.buttons[4].scripts.OnClick()
      assert(A.settings.skin=="flat")
      canvas:Hide(); Settings.OpenToCategory(123)
      assert(A.options.skin.caption.text:find(A.Text("flat","enUS"),1,true))
      A.options.minimap.scripts.OnClick()
      assert(not b:IsShown() and StatCompassDB.minimapShown==false)
      A.options.reset.scripts.OnClick()
      assert(b:IsShown() and A.settings.skin=="default" and A.settings.mode=="mythic")
      local count=widgets.frames
      Fire("ADDON_LOADED","StatCompass"); Fire("PLAYER_LOGIN")
      assert(#Settings.categories==1 and widgets.frames==count)
      assert(not canvas.scripts.OnUpdate and not b.scripts.OnUpdate)
      assert(A.releaseData and A.GetTarget(71,"raid")==nil)
    ''')


def test_drag_scaled_geometry_cleanup_and_persistence():
    lua = load_runtime(CONTROLS_MOCK)
    run(lua, '''
      Fire("ADDON_LOADED","StatCompass")
      local A=StatCompass; local b=A.minimapButton
      assert(b.drags and b.drags[1]=="LeftButton", "launcher must support drag")
      Minimap:SetSize(180,180)
      assert(math.abs(math.sqrt(b.point[4]^2+b.point[5]^2)-106)<0.00001)
      Minimap:SetSize(0,0)
      assert(math.abs(math.sqrt(b.point[4]^2+b.point[5]^2)-86)<0.00001)
      Minimap:SetSize(140,140); Minimap:SetScale(0.5)
      GetCursorPosition=function() return 50,100 end
      b.scripts.OnDragStart(b)
      assert(b.scripts.OnUpdate)
      b.scripts.OnUpdate(b)
      assert(math.abs(StatCompassDB.minimapAngle-90)<0.00001)
      b.scripts.OnDragStop(b)
      assert(not b.scripts.OnUpdate)
      A.SaveSettings(StatCompassDB)
      assert(A.settings.minimapAngle==90)
      math.atan2=nil -- portable Lua 5.1 quadrant fallback
      GetCursorPosition=function() return 0,50 end
      b.scripts.OnDragStart(b); b.scripts.OnUpdate(b)
      assert(math.abs(A.settings.minimapAngle-180)<0.00001)
      GetCursorPosition=function() return 50,0 end
      b.scripts.OnUpdate(b)
      assert(math.abs(A.settings.minimapAngle-270)<0.00001)
      GetCursorPosition=function() return 50,50 end
      b.scripts.OnUpdate(b)
      assert(A.settings.minimapAngle==270) -- no direction at exact center
      GetCursorPosition=function() return {secret=true},0 end
      b.scripts.OnUpdate(b)
      assert(A.settings.minimapAngle==270)
      Minimap.scale=0; GetCursorPosition=function() return 50,100 end
      b.scripts.OnUpdate(b)
      assert(A.settings.minimapAngle==270)
      Minimap.scale=0.5
      b.scripts.OnEnter(b); assert(GameTooltip.shown)
      Minimap:Hide()
      assert(not b.scripts.OnUpdate and not GameTooltip.shown)
      Minimap:Show(); b.scripts.OnDragStart(b)
      A.SetMinimapShown(false)
      assert(not b.scripts.OnUpdate)
    ''')


def test_saved_variables_untouched_until_authoritative_event():
    lua = load_runtime(CONTROLS_MOCK + '''
      originalDB={mode="mythic",skin="flat",minimapShown=false,minimapAngle=450,legacy="keep until init"}
      StatCompassDB=originalDB
    ''')
    run(lua, '''
      assert(StatCompassDB==originalDB, "TOC execution must not overwrite SavedVariables")
      assert(not StatCompass.minimapButton)
      Fire("ADDON_LOADED","OtherAddon")
      assert(StatCompassDB==originalDB and #Settings.categories==0)
      Fire("ADDON_LOADED","StatCompass")
      assert(StatCompassDB~=originalDB and StatCompassDB.minimapAngle==90)
      assert(StatCompassDB.mode=="mythic" and StatCompassDB.skin=="flat")
      assert(not StatCompass.minimapButton:IsShown())
      assert(StatCompassDB.legacy==nil)
    ''')


def test_minimap_settings_survive_inline_changes():
    lua = load_runtime()
    run(lua, '''
      local A=StatCompass
      A.SaveSettings({mode="mythic",skin="flat",minimapShown=false,minimapAngle=-90})
      assert(A.settings.minimapShown==false, "minimap visibility must persist")
      assert(A.settings.minimapAngle==270)
      A.SetMode("raid"); A.SetSkin("default")
      assert(StatCompassDB.minimapShown==false and StatCompassDB.minimapAngle==270)
      for _,value in ipairs({math.huge,-math.huge,0/0,"bad",{secret=true}}) do
        assert(A.SanitizeSettings({minimapAngle=value}).minimapAngle==225)
      end
      assert(A.SanitizeSettings({minimapShown="false"}).minimapShown==true)
      A.SetMode("mythic"); A.ResetPresentation()
      assert(StatCompassDB.mode=="mythic" and StatCompassDB.skin=="default")
      assert(StatCompassDB.minimapShown and StatCompassDB.minimapAngle==225)
    ''')
