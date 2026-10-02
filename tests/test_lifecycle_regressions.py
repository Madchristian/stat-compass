"""Orchestrator regression probes; synthetic WoW objects only."""
from tests.test_addon import load_runtime, run


def test_saved_variables_restored_at_addon_loaded():
    lua = load_runtime()
    run(lua, '''
      -- WoW makes the persisted table authoritative at ADDON_LOADED.
      StatCompassDB={mode="mythic",skin="flat"}
      Fire("ADDON_LOADED", "StatCompass")
      assert(StatCompass.settings.mode=="mythic")
      assert(StatCompass.settings.skin=="flat")
      Fire("PLAYER_LOGIN")
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.buttons[2].selected)
    ''')


def test_border_is_edges_not_opaque_panel_overlay():
    lua = load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN")
      assert(StatCompass.panel.borders and #StatCompass.panel.borders==4)
      CharacterFrame:Show(); PaperDollFrame:Show()
      StatCompass.SetSkin("flat")
      for _,edge in ipairs(StatCompass.panel.borders) do
            assert(not edge.allPoints and (edge.width==3 or edge.height==3))
      end
    ''')
