from pathlib import Path
from tests.test_addon import load_runtime, run


def test_value_hitboxes_fit_visible_text_not_empty_columns():
    lua = load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      a.Render({current={crit=12},ratingTarget={crit={currentRating=500,targetRating=600,targetPercent=20,personal=true,sampleCount=30,axisMaxRating=1000,
        axisVerified=true,axisProvenance="fixture",sourceStatus="verified",
        reference={minRating=400,meanRating=500,maxRating=600}}}})
      local r=a.rows[1]
      for role,font in pairs({current=r.current,target=r.target}) do
        assert(r.hit[role]:GetWidth()<=font:GetStringWidth()+2, "empty column hover: "..role)
      end
      assert(a.metadataHit:GetWidth()<=a.status:GetStringWidth()+2, "empty metadata hover")
    ''')


def test_native_hit_geometry_does_not_read_mock_font_fields():
    ui = (Path(__file__).resolve().parents[1] / 'StatCompass/UI.lua').read_text()
    assert 'font.point' not in ui
    assert 'font.width' not in ui
