"""Synthetic geometry against the real Lua 5.1 controls, including texture bounds."""
import math

import pytest

from tests.test_addon import load_runtime, run
from tests.test_controls import CONTROLS_MOCK


# Rounded quadrants in the public GetMinimapShape convention (screen directions).
ROUNDED = {
    "ROUND": {"NE", "NW", "SE", "SW"},
    "SQUARE": set(),
    "CORNER-TOPLEFT": {"NW"},
    "CORNER-TOPRIGHT": {"NE"},
    "CORNER-BOTTOMLEFT": {"SW"},
    "CORNER-BOTTOMRIGHT": {"SE"},
    "SIDE-LEFT": {"NW", "SW"},
    "SIDE-RIGHT": {"NE", "SE"},
    "SIDE-TOP": {"NW", "NE"},
    "SIDE-BOTTOM": {"SW", "SE"},
    "TRICORNER-TOPLEFT": {"NE", "NW", "SW"},
    "TRICORNER-TOPRIGHT": {"NE", "NW", "SE"},
    "TRICORNER-BOTTOMLEFT": {"NW", "SW", "SE"},
    "TRICORNER-BOTTOMRIGHT": {"NE", "SW", "SE"},
}

CAPTURE_TEXTURES = '''
local frame=getmetatable(Minimap).__index
local create=frame.CreateTexture
function frame:CreateTexture(...)
  local texture=create(self,...)
  self.textures=self.textures or {}
  table.insert(self.textures,texture)
  return texture
end
'''


def runtime(shape):
    lua = load_runtime(CONTROLS_MOCK + CAPTURE_TEXTURES)
    if shape is not None:
        lua.globals().shape = shape
        run(lua, 'GetMinimapShape=function() return shape end')
    run(lua, 'Fire("ADDON_LOADED","StatCompass")')
    return lua


def bounds(lua):
    """Read production anchors, not the positioning algorithm's constants."""
    b = lua.globals().StatCompass.minimapButton
    scale = b.GetEffectiveScale(b) / lua.globals().Minimap.GetEffectiveScale(lua.globals().Minimap)
    x, y = b.point[4] * scale, b.point[5] * scale
    left, right = -b.width / 2, b.width / 2
    bottom, top = -b.height / 2, b.height / 2
    border = b.textures[2]
    assert border.point[1] == "TOPLEFT" and border.point[3] == "TOPLEFT"
    left = min(left, -b.width / 2 + border.point[4])
    right = max(right, -b.width / 2 + border.point[4] + border.width)
    top = max(top, b.height / 2 + border.point[5])
    bottom = min(bottom, b.height / 2 + border.point[5] - border.height)
    return x, y, (x + left * scale, x + right * scale,
                  y + bottom * scale, y + top * scale)


def assert_clear(lua, shape, width, height):
    x, y, (left, right, bottom, top) = bounds(lua)
    # Inflate the complete texture rectangle by a small required clearance.
    gap = 2 * lua.globals().StatCompass.minimapButton.GetEffectiveScale(
        lua.globals().StatCompass.minimapButton
    ) / lua.globals().Minimap.GetEffectiveScale(lua.globals().Minimap)
    left, right, bottom, top = left - gap, right + gap, bottom - gap, top + gap
    for quadrant, sx, sy in [("NE", 1, 1), ("NW", -1, 1), ("SE", 1, -1), ("SW", -1, -1)]:
        qleft, qright = (0, width / 2) if sx > 0 else (-width / 2, 0)
        qbottom, qtop = (0, height / 2) if sy > 0 else (-height / 2, 0)
        lo_x, hi_x = max(left, qleft), min(right, qright)
        lo_y, hi_y = max(bottom, qbottom), min(top, qtop)
        if lo_x >= hi_x or lo_y >= hi_y:
            continue
        assert quadrant in ROUNDED[shape], (shape, x, y, quadrant, "square overlap")
        near_x = max(lo_x, min(0, hi_x))
        near_y = max(lo_y, min(0, hi_y))
        assert (near_x / (width / 2)) ** 2 + (near_y / (height / 2)) ** 2 >= 1 - 1e-7, (
            shape, x, y, quadrant, "round overlap"
        )


@pytest.mark.parametrize("shape", ["ROUND", "SQUARE"])
@pytest.mark.parametrize("size", [(140, 140), (240, 140), (140, 240)])
def test_full_texture_envelope_clears_map_and_preserves_angle(shape, size):
    lua = runtime(shape)
    run(lua, f'Minimap:SetSize({size[0]},{size[1]})')
    for angle in range(0, 360, 15):
        run(lua, f'StatCompass.SetMinimapAngle({angle})')
        assert_clear(lua, shape, *size)
        x, y, _ = bounds(lua)
        actual = math.degrees(math.atan2(y, x)) % 360
        assert abs((actual - angle + 180) % 360 - 180) < 1e-7
        assert lua.globals().StatCompassDB.minimapAngle == angle


@pytest.mark.parametrize("shape", list(ROUNDED))
def test_mixed_quadrants_and_drag_follow_outer_contour(shape):
    lua = runtime(shape)
    run(lua, 'Minimap:SetSize(180,140); Minimap:SetScale(0.65)')
    for angle in range(360):
        radians = math.radians(angle)
        cx = (100 + 200 * math.cos(radians)) * 0.65
        cy = (100 + 200 * math.sin(radians)) * 0.65
        run(lua, f'''
          GetCursorPosition=function() return {cx},{cy} end
          local b=StatCompass.minimapButton
          b.scripts.OnDragStart(b); b.scripts.OnUpdate(b); b.scripts.OnDragStop(b)
          assert(not b.scripts.OnUpdate)
        ''')
        assert_clear(lua, shape, 180, 140)
        assert abs((lua.globals().StatCompassDB.minimapAngle - angle + 180) % 360 - 180) < 1e-7


@pytest.mark.parametrize("shape", [None, "UNKNOWN", "ROUND", "SQUARE"])
def test_resize_scale_and_shape_refresh_without_changing_saved_angle(shape):
    lua = runtime(shape)
    run(lua, 'StatCompass.SetMinimapAngle(225)')
    for command, size in [
        ('Minimap:SetSize(240,180)', (240, 180)),
        ('Minimap:SetScale(0.6)', (240, 180)),
        ('StatCompass.minimapButton:SetScale(1.8)', (240, 180)),
        ('Minimap:SetSize(0,0)', (140, 140)),
    ]:
        run(lua, command)
        assert_clear(lua, shape if shape in ROUNDED else "ROUND", *size)
        assert lua.globals().StatCompassDB.minimapAngle == 225
    run(lua, '''
      Minimap:SetSize(140,140)
      GetMinimapShape=function() return "SQUARE" end
      Minimap:Hide(); Minimap:Show()
    ''')
    assert_clear(lua, "SQUARE", 140, 140)


def test_independent_button_scale_repositions_immediately():
    lua = runtime("ROUND")
    run(lua, 'StatCompass.SetMinimapAngle(0); StatCompass.minimapButton:SetScale(0.5)')
    assert_clear(lua, "ROUND", 140, 140)
    x, _, _ = bounds(lua)
    assert x == pytest.approx(79.5)
