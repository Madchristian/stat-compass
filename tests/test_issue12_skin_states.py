"""Issue 12: rendered button surfaces in the Lua 5.1 widget runtime."""
from tests.test_addon import load_runtime, run
from tests.test_controls import CONTROLS_MOCK


def test_standard_and_flat_button_surfaces_round_trip():
    lua = load_runtime(CONTROLS_MOCK + r'''
      local frame=getmetatable(CharacterFrame).__index
      function frame:IsEnabled() return self.enabled~=false end
      function frame:Disable() self.enabled=false; if self.scripts.OnDisable then self.scripts.OnDisable(self) end end
      function frame:Enable() self.enabled=true; if self.scripts.OnEnable then self.scripts.OnEnable(self) end end
    ''')
    run(lua, r'''
      Fire("ADDON_LOADED","StatCompass")
      CharacterFrame:Show(); PaperDollFrame:Show()
      local A=StatCompass
      local panelButton=A.buttons[2]
      local settingsButton=A.options.skin
      local function color(t,r,g,b,a)
        assert(t.color and t.color[1]==r and t.color[2]==g and t.color[3]==b and t.color[4]==a)
      end
      local function state(b,selected,native)
        assert(b.bg and b.hover and b.selection)
        assert(b.bg.layer~="BACKGROUND", "surface must render over template chrome")
        assert(b.selection.layer=="OVERLAY" and b.selection.height>0 and b.selection.height< b:GetHeight())
        assert(b.selection.shown==(native and selected), "Standard-only selection mark")
        assert(b.hover.shown==false)
        if native then
          assert(b.bg.texture==[[Interface\Buttons\WHITE8X8]])
          if selected then color(b.bg,0.38,0.28,0.11,1) else color(b.bg,0.18,0.17,0.15,1) end
        else
          assert(b.bg.texture==[[Interface\Buttons\WHITE8X8]])
          if selected then color(b.bg,0.17,0.31,0.42,1) else color(b.bg,0.11,0.15,0.19,1) end
        end
      end
      local function all(native,mode,skin,shown)
        state(A.buttons[1],mode=="raid",native)
        state(A.buttons[2],mode=="mythic",native)
        state(A.buttons[3],skin=="default",native)
        state(A.buttons[4],skin=="flat",native)
        state(A.buttons[5],false,native)
        state(A.options.skin,false,native)
        state(A.options.minimap,shown,native)
        state(A.options.reset,false,native)
      end
      all(true,"raid","default",true)
      A.SetMode("mythic")
      all(true,"mythic","default",true)
      local other=A.buttons[1]
      other.scripts.OnEnter(other)
      assert(other.hover.shown and not other.selection.shown)
      assert(other.hover.layer=="BORDER" and other.hover.color[4]<0.5)
      other.scripts.OnLeave(other)
      assert(not other.hover.shown)
      local selected=A.buttons[2]
      selected.scripts.OnEnter(selected)
      assert(selected.selection.shown)
      selected.scripts.OnLeave(selected)
      assert(selected.selection.shown and not selected.hover.shown)
      selected:Disable()
      assert(not selected.selection.shown and not selected.hover.shown)
      color(selected.bg,0.11,0.11,0.11,1)
      selected.scripts.OnEnter(selected)
      assert(not selected.hover.shown and not selected.selection.shown)
      selected:Enable()
      assert(selected.selection.shown and not selected.hover.shown)
      A.options.skin.scripts.OnEnter(A.options.skin)
      assert(not A.options.skin.selection.shown)
      A.options.skin.scripts.OnLeave(A.options.skin)
      A.options.skin:Disable()
      assert(not A.options.skin.selection.shown and not A.options.skin.hover.shown)
      A.options.skin:Enable()
      assert(not A.options.skin.selection.shown)
      local reset=A.options.reset
      reset.scripts.OnEnter(reset)
      assert(reset.hover.shown and not reset.selection.shown)
      reset.scripts.OnLeave(reset)
      assert(not reset.hover.shown and not reset.selection.shown)
      reset:Disable()
      color(reset.bg,0.11,0.11,0.11,1)
      reset.scripts.OnEnter(reset)
      assert(not reset.hover.shown and not reset.selection.shown)
      reset:Enable()
      assert(not reset.hover.shown and not reset.selection.shown)
      local panelReset=A.buttons[5]
      panelReset.scripts.OnEnter(panelReset)
      assert(panelReset.hover.shown and not panelReset.selection.shown)
      panelReset.scripts.OnLeave(panelReset)
      assert(not panelReset.hover.shown and not panelReset.selection.shown)
      A.SetSkin("flat")
      all(false,"mythic","flat",true)
      A.SetMinimapShown(false)
      all(false,"mythic","flat",false)
      A.SetSkin("default")
      all(true,"mythic","default",false)
      assert(A.buttons[2]==panelButton and A.options.skin==settingsButton)
      A.SetSkin("flat")
      all(false,"mythic","flat",false)
      A.SetSkin("default")
      all(true,"mythic","default",false)
      A.options.reset.scripts.OnClick()
      all(true,"mythic","default",true)
      A.buttons[5].scripts.OnClick()
      all(true,"raid","default",true)
    ''')
