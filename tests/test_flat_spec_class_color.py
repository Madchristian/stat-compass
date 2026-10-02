"""Flat-only specialization color; execute real UI with the Lua 5.1 backend."""
import pytest
from tests.test_addon import load_runtime, run


SETUP = r'''
  local frame=getmetatable(CharacterFrame).__index
  local create=frame.CreateFontString
  function frame:CreateFontString(...)
    local font=create(self,...)
    font.color={0.91,0.92,0.93,1}
    function font:GetTextColor() return unpack(self.color) end
    return font
  end
  classCalls=0
  UnitClass=function(unit)
    assert(unit=="player"); classCalls=classCalls+1
    return "Localized mage", "MAGE", 8
  end
  RAID_CLASS_COLORS={MAGE={r=0.25,g=0.78,b=0.92}}
'''
CHECK = r'''
  function checkColor(r,g,b)
    local c=StatCompass.spec.color
    assert(c and c[1]==r and c[2]==g and c[3]==b and c[4]==1,
      "specialization label color mismatch")
  end
  Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
'''


@pytest.mark.parametrize("initial", ["default", "flat"])
def test_spec_color_both_skin_roundtrips_render_and_hidden(initial):
    lua = load_runtime(SETUP + f' StatCompassDB={{skin="{initial}"}}')
    assert lua.eval('_VERSION') == 'Lua 5.1'
    run(lua, CHECK + r'''
      local A=StatCompass
      local spec=A.spec
      local titleColor=A.title.color
      local rowColor=A.rows[1].label.color
      for i=1,2 do
        A.SetSkin("default"); checkColor(0.91,0.92,0.93)
        local calls=classCalls
        A.Render({}); assert(classCalls==calls, "Standard must not query class")
        A.SetSkin("flat"); checkColor(0.25,0.78,0.92)
        RAID_CLASS_COLORS.MAGE={r=0.1,g=0.2,b=0.3}
        A.Render({}); checkColor(0.1,0.2,0.3)
        RAID_CLASS_COLORS.MAGE={r=0.25,g=0.78,b=0.92}
        A.SetSkin("default"); checkColor(0.91,0.92,0.93)
        A.SetSkin("flat"); checkColor(0.25,0.78,0.92)
      end
      assert(A.spec==spec and A.title.color==titleColor and A.rows[1].label.color==rowColor)
      CharacterFrame:Hide()
      local calls=classCalls
      A.ReadStats=function() error("hidden stat read") end
      A.SetSkin("default"); A.SetSkin("flat"); A.Render({}); A.ApplySkin()
      assert(classCalls==calls, "hidden UI must not query class")
    ''')


@pytest.mark.parametrize("invalid", [
    'UnitClass=nil',
    'UnitClass=secret',
    'UnitClass=function() error("unavailable") end',
    'UnitClass=function() return "Mage", nil end',
    'UnitClass=function() return "Mage", 8 end',
    'UnitClass=function() return "Mage", secret end',
    'UnitClass=function() return "Mage", "UNKNOWN" end',
    'RAID_CLASS_COLORS=nil',
    'RAID_CLASS_COLORS=false',
    'RAID_CLASS_COLORS=secret',
    'RAID_CLASS_COLORS.MAGE=nil',
    'RAID_CLASS_COLORS.MAGE=42',
    'RAID_CLASS_COLORS.MAGE=secret',
    'RAID_CLASS_COLORS.MAGE.r=secret',
    'RAID_CLASS_COLORS.MAGE.g=nil',
    'RAID_CLASS_COLORS.MAGE.b="blue"',
    'RAID_CLASS_COLORS.MAGE.r=0/0',
    'RAID_CLASS_COLORS.MAGE.g=math.huge',
    'RAID_CLASS_COLORS.MAGE.b=-0.1',
    'RAID_CLASS_COLORS.MAGE.r=1.1',
])
def test_unreadable_class_colors_restore_original_text_color(invalid):
    lua = load_runtime(SETUP)
    run(lua, CHECK + r'''
      local A=StatCompass
      A.SetSkin("flat"); checkColor(0.25,0.78,0.92)
      secret=setmetatable({}, {__index=function() error("indexed secret") end})
      local original=issecretvalue
      issecretvalue=function(value) return rawequal(value,secret) or original(value) end
    ''' + invalid + r'''
      A.Render({}); checkColor(0.91,0.92,0.93)
      A.SetSkin("default"); checkColor(0.91,0.92,0.93)
      A.SetSkin("flat"); checkColor(0.91,0.92,0.93)
    ''')
