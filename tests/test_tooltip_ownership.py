"""Ownership boundary regressions; real Lua 5.1, private tooltip owner."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_controls import CONTROLS_MOCK

OWNERSHIP = '''
local owner
function GameTooltip:SetOwner(value, anchor) owner=value; self.anchor=anchor end
function GameTooltip:IsOwned(value) return owner==value end
'''


def shown():
    lua = load_runtime(CONTROLS_MOCK + OWNERSHIP)
    run(lua, 'Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()')
    return lua


@pytest.mark.parametrize("owner", ["a.rows[1].hoverFrame", "a.panel"])
@pytest.mark.parametrize("action", ["a.Flush()", "frame.scripts.OnLeave(frame)", "PaperDollFrame:Hide()"])
def test_foreign_tooltip_survives_cached_hover(owner, action):
    run(shown(), f'''
      local a=StatCompass; local frame={owner}
      frame.scripts.OnEnter(frame)
      local other=CreateFrame("Frame",nil,UIParent)
      GameTooltip:SetOwner(other,"ANCHOR_RIGHT")
      GameTooltip:SetText("foreign tooltip"); GameTooltip:Show()
      {action}
      assert(GameTooltip.text=="foreign tooltip" and GameTooltip.shown,
        "foreign tooltip mutated after ownership transfer")
      assert(not a.tooltipOpen and a.tooltipOwner==nil, "stale hover state retained")
    ''')


def test_parent_hide_without_hover_preserves_foreign_tooltip():
    run(shown(), '''
      GameTooltip:SetOwner(UIParent,"ANCHOR_RIGHT")
      GameTooltip:SetText("foreign tooltip"); GameTooltip:Show()
      PaperDollFrame:Hide()
      assert(GameTooltip.shown and GameTooltip.text=="foreign tooltip")
    ''')


@pytest.mark.parametrize("action", ["b.scripts.OnLeave(b)", "b.scripts.OnDragStart(b)", "a.SetMinimapShown(false)"])
def test_minimap_preserves_foreign_tooltip(action):
    run(shown(), f'''
      local a=StatCompass; local b=a.minimapButton
      b.scripts.OnEnter(b)
      GameTooltip:SetOwner(UIParent,"ANCHOR_RIGHT")
      GameTooltip:SetText("foreign tooltip"); GameTooltip:Show()
      {action}
      assert(GameTooltip.shown and GameTooltip.text=="foreign tooltip")
    ''')


@pytest.mark.parametrize("owner", ["a.rows[1].hoverFrame", "a.panel"])
def test_owned_tooltip_refreshes_and_hides(owner):
    run(shown(), f'''
      local a=StatCompass; local frame={owner}
      frame.scripts.OnEnter(frame)
      GameTooltip:SetText("old owned text")
      a.Flush()
      assert(GameTooltip.text~="old owned text" and GameTooltip.shown)
      PaperDollFrame:Hide()
      assert(not GameTooltip.shown and not a.tooltipOpen and a.tooltipOwner==nil)
    ''')


@pytest.mark.parametrize("result", ["return {secret=true}", "error('unreadable owner')", "return nil"])
def test_unreadable_ownership_fails_closed(result):
    run(shown(), f'''
      local a=StatCompass; local frame=a.rows[1].hoverFrame
      frame.scripts.OnEnter(frame)
      GameTooltip.IsOwned=function() {result} end
      GameTooltip:SetText("untouched")
      a.Flush()
      frame.scripts.OnLeave(frame); PaperDollFrame:Hide()
      assert(GameTooltip.shown and GameTooltip.text=="untouched")
      assert(not a.tooltipOpen and a.tooltipOwner==nil)
    ''')
