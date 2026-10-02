"""Marker ink stays between the row heading and numeric endpoint labels."""
import pytest
from tests.test_addon import run
from tests.test_followup import runtime_with_data


@pytest.mark.parametrize('height', [424, 530, 750])
def test_marker_vertical_clearance(height):
    lua = runtime_with_data('deDE')
    run(lua, f'''
      CharacterFrame:SetBounds(20,420,0,{height})
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.visible)
      for _,row in ipairs(StatCompass.rows) do
        local trackTop=-row.track.point[5]
        local trackBottom=trackTop+row.track.height
        local headingBottom=-row.label.point[5]+row.label:GetStringHeight()
        local numbersTop=-row.min.point[5]
        local minTop=trackTop+(row.track.height-row.markerMin.height)/2
        local maxBottom=trackTop+(row.track.height+row.markerMax.height)/2
        local ownTop=trackTop+(row.track.height-row.markerCurrent.height)/2
        local ownBottom=trackBottom+(row.markerCurrent.height-row.track.height)/2
        assert(minTop>=headingBottom+2, "min marker crosses heading")
        assert(ownTop>=headingBottom+2, "current marker crosses heading")
        assert(maxBottom<=numbersTop-2, "max marker crosses endpoint text")
        assert(ownBottom<=numbersTop-2, "current marker crosses endpoint text")
      end
    ''')
