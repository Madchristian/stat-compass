"""Flat skin remains unchanged while Standard alone gains an active marker."""
import pytest

from tests.test_addon import load_runtime, run
from tests.test_controls import CONTROLS_MOCK


@pytest.mark.parametrize("locale", ["enUS", "deDE"])
def test_flat_texture_order_and_round_trips_while_hovered_and_disabled(locale):
    lua = load_runtime(CONTROLS_MOCK + f'''
      GetLocale=function() return "{locale}" end
      local frame=getmetatable(CharacterFrame).__index
      local createFont=frame.CreateFontString
      function frame:CreateFontString(name,layer,template)
        local font=createFont(self,name,layer,template)
        font.layer=layer; font.sublevel=0
        return font
      end
      function frame:IsEnabled() return self.enabled~=false end
      function frame:Disable() self.enabled=false; if self.scripts.OnDisable then self.scripts.OnDisable(self) end end
      function frame:Enable() self.enabled=true; if self.scripts.OnEnable then self.scripts.OnEnable(self) end end
    ''')
    run(lua, r'''
      Fire("ADDON_LOADED","StatCompass")
      CharacterFrame:Show(); PaperDollFrame:Show()
      local A=StatCompass
      local flat=[[Interface\Buttons\WHITE8X8]]
      local layerRank={BACKGROUND=1,BORDER=2,ARTWORK=3,OVERLAY=4}
      local function color(t,r,g,b,a)
        assert(t.texture==flat and t.color[1]==r and t.color[2]==g and t.color[3]==b and t.color[4]==a)
      end
      local function order(b)
        assert(b.bg.layer=="BORDER" and b.bg.sublevel==-1)
        assert(b.hover.layer=="BORDER" and b.hover.sublevel==0)
        assert(b.caption.layer=="ARTWORK" and b.caption.sublevel==0)
        assert(b.selection.layer=="OVERLAY")
        assert(b.bg.sublevel<b.hover.sublevel and layerRank[b.hover.layer]<layerRank[b.caption.layer])
        assert(layerRank[b.caption.layer]<layerRank[b.selection.layer])
        assert(b.selection.point[1]=="BOTTOMLEFT" and b.selection.point[2]==b)
        assert(b.selection.point[4]==3 and b.selection.point[5]==2)
        assert(b.selection.width==b:GetWidth()-6 and b.selection.height==3)
      end
      local function flatState(b,selected)
        order(b)
        assert(not b.selection.shown, "Flat has no Standard-only underline")
        if selected then color(b.bg,0.17,0.31,0.42,1)
        else color(b.bg,0.11,0.15,0.19,1) end
        color(b.hover,0.28,0.43,0.52,0.65)
        assert(b.caption.color[1]==0.91 and b.caption.color[2]==0.95 and b.caption.color[3]==0.98)
      end
      local main=A.buttons[2]
      local skin=A.options.skin
      order(main); order(skin)
      assert(not skin.selection.shown and skin.selected==false, "skin-cycle button is an action")
      A.SetMode("mythic")
      A.SetSkin("flat")
      assert(A.buttons[2]==main and A.options.skin==skin)
      flatState(main,true)
      flatState(A.buttons[1],false)
      flatState(A.buttons[4],true)
      flatState(skin,false)
      assert(skin.caption.text==A.Text("skin",GetLocale())..": "..A.Text("flat",GetLocale()))
      main.scripts.OnEnter(main); skin.scripts.OnEnter(skin)
      assert(main.hover.shown and skin.hover.shown)
      A.SetSkin("default")
      assert(main.selection.shown and not skin.selection.shown)
      A.SetSkin("flat")
      assert(main.hover.shown and skin.hover.shown)
      flatState(main,true); flatState(skin,false)
      main:Disable(); skin:Disable()
      assert(not main.hover.shown and not main.selection.shown)
      assert(not skin.hover.shown and not skin.selection.shown)
      A.SetSkin("default")
      A.SetSkin("flat")
      assert(not main.hover.shown and not main.selection.shown)
      assert(not skin.hover.shown and not skin.selection.shown)
      main:Enable(); skin:Enable()
      flatState(main,true); flatState(skin,false)
      main.scripts.OnLeave(main); skin.scripts.OnLeave(skin)
      assert(not main.hover.shown and not skin.hover.shown)
      A.SetSkin("default")
      assert(main.selection.shown and not skin.selection.shown)
      local width=A.panel:GetWidth()
      local height=A.panel:GetHeight()
      local oldMarkerWidth=main.selection.width
      A.Layout(width-12,height)
      order(main); order(A.buttons[4]); order(skin)
      assert(main.selection.width<oldMarkerWidth)
      A.Layout(width,height)
      order(main); order(A.buttons[4]); order(skin)
      assert(main.selection.width==oldMarkerWidth)
      assert(A.buttons[2]==main and A.options.skin==skin)
    ''')
