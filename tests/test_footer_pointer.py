"""Pointer regression: geometry, visibility, mouse enablement and frame levels.

WoW's native hit tester is not executable here. Model its relevant constraints:
mouse-enabled Frames consume input even without OnClick, textures/fonts do not,
and higher frame levels win. Equal-level sibling order is not a safe contract;
exercise both orders instead of blessing the current creation order.
"""
import pytest
from tests.test_addon import load_runtime, run

POINTER = r'''
local originalCreateFrame=CreateFrame
pointerFrames={}
function CreateFrame(kind,name,parent,...)
  local f=originalCreateFrame(kind,name,parent,...)
  -- Native frames start shown; Buttons start mouse-enabled.
  f.shown=true
  f.mouseEnabled=(kind=="Button")
  f.level=(parent and parent.level or 0)+1
  function f:GetFrameLevel() return self.level end
  function f:SetFrameLevel(level) self.level=level end
  table.insert(pointerFrames,f)
  return f
end
function PointerTarget(x,y,earlierFirst)
  local best
  for _,f in ipairs(pointerFrames) do
    local s=f:GetEffectiveScale()
    if f.mouseEnabled and f:IsVisible() and f.width and f.height
      and x>=f:GetLeft()*s and x<=f:GetRight()*s
      and y>=f:GetBottom()*s and y<=f:GetTop()*s then
      if not best or f.level>best.level or (f.level==best.level and not earlierFirst) then best=f end
    end
  end
  return best
end
function PointerClickCenter(button,earlierFirst)
  local s=button:GetEffectiveScale()
  local x=(button:GetLeft()+button:GetRight())*s/2
  local y=(button:GetBottom()+button:GetTop())*s/2
  local target=PointerTarget(x,y,earlierFirst)
  -- Dispatch only the actual hit target, never the requested button directly.
  if target and target.scripts.OnEnter then target.scripts.OnEnter(target) end
  if target and target.scripts.OnClick then target.scripts.OnClick(target,"LeftButton",false) end
  return target
end
'''


@pytest.mark.parametrize("height", [420, 530, 750, 900, 1080])
@pytest.mark.parametrize("earlier_first", [True, False])
@pytest.mark.parametrize("index", [1, 2, 3])
def test_footer_pointer_reaches_each_action(height, earlier_first, index):
    lua = load_runtime(POINTER)
    run(lua, f'''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      a.panel:SetSize(450,{height}); a.Layout(450,{height})
      a.SetSkin({index}==1 and "flat" or "default"); a.SetMode("mythic")
      local target=PointerClickCenter(a.buttons[{index}],{str(earlier_first).lower()})
      assert(target==a.buttons[{index}],"footer pointer intercepted by another mouse-enabled frame")
      assert(a.settings.skin==({index}==2 and "flat" or "default"),"skin action not delivered")
      if {index}==3 then assert(a.settings.mode=="mythic","reset action not delivered") end
    ''')


@pytest.mark.parametrize("height", [420, 530, 750, 900, 1080])
def test_value_hit_rectangles_end_before_status(height):
    lua = load_runtime(POINTER)
    run(lua, f'''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; a.Layout(450,{height})
      for i,row in ipairs(a.rows) do
        assert(not row.hoverFrame.mouseEnabled)
        local hit=row.hit.current
        local bottom=-hit.point[5]+hit:GetHeight()
        assert(bottom>=-row.current.point[5]+row.current:GetStringHeight()-0.001,"endpoint lacks hover")
        local nextTop=a.rows[i+1] and -a.rows[i+1].label.point[5] or -a.status.point[5]
        assert(bottom<=nextTop-2+0.001,"value target extends into next row/status/footer")
      end
      local last=a.rows[4]; local f=last.hit.current; local s=f:GetEffectiveScale()
      local x=(f:GetLeft()+f:GetRight())*s/2
      local y=(f:GetTop()+f:GetBottom())*s/2
      assert(PointerTarget(x,y,true)==f,"last endpoint cannot be hovered")
      f.scripts.OnEnter(f)
      assert(a.TooltipIsOwned(f) and GameTooltip.shown)
    ''')


def test_pointer_negative_control_overlay_consumes_click_without_handler():
    lua = load_runtime(POINTER)
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; local b=a.buttons[2]
      local cover=CreateFrame("Frame",nil,a.panel)
      cover:SetPoint(unpack(b.point)); cover:SetSize(b:GetWidth(),b:GetHeight())
      cover:EnableMouse(true); cover:SetFrameLevel(b:GetFrameLevel()+1)
      a.SetSkin("default")
      assert(PointerClickCenter(b,false)==cover)
      assert(a.settings.skin=="default","hit testing bypassed overlay")
      cover:EnableMouse(false)
      assert(PointerClickCenter(b,false)==b and a.settings.skin=="flat")
    ''')
