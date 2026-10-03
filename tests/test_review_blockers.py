"""Independent-review blockers; synthetic cohorts only."""
import pytest

from tests.test_addon import load_runtime, run
from tests.test_followup import runtime_with_data


@pytest.mark.parametrize("root_scale,owner_scale", [(1, 1.76), (0.8, 1.76), (0.8, 0.8), (1, 1), (1.76, 1.76)])
def test_native_424_height_stays_attached(root_scale, owner_scale):
    lua = runtime_with_data("deDE")
    run(lua, f'''
      UIParent.scale={root_scale}
      UIParent.right=1659/{root_scale}; UIParent.top=777/{root_scale}
      -- This legacy fixture uses a 1:1 virtual/pixel screen; real 768-high
      -- virtual-screen coverage lives in test_virtual_screen_geometry.py.
      function GetPhysicalScreenSize() return 1659,777 end
      CharacterFrame.scale={owner_scale}/{root_scale}
      local bottom=3/{owner_scale}
      CharacterFrame:SetBounds(10/{owner_scale},962/{owner_scale},bottom,bottom+424)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local p=StatCompass.panel
      assert(StatCompass.visible, "424 native unit CharacterFrame must show")
      local ps=p:GetEffectiveScale()
      assert(math.abs(p:GetTop()*ps-CharacterFrame:GetTop()*CharacterFrame:GetEffectiveScale())<0.01)
      assert(math.abs(p:GetBottom()*ps-CharacterFrame:GetBottom()*CharacterFrame:GetEffectiveScale())<0.01)
      assert(p:GetLeft()*ps>=0 and p:GetRight()*ps<=1659)
      assert(p:GetWidth()*ps<=math.max(500,424*{owner_scale}*0.7))
      assert(p:GetWidth()*ps>=350)
      assert(p.point[2]==CharacterFrame)
    ''')


def test_bar_geometry_repaints_without_stat_reads():
    lua = runtime_with_data()
    run(lua, '''
      local reads=0
      GetHaste=function() reads=reads+1; return 6.8 end
      CharacterFrame:SetBounds(200,600,30,780)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      StatCompass.Render({ratingTarget={haste={currentRating=68,targetRating=68,lowRating=68,highRating=68,targetPercent=20,personal=true,sampleCount=30,axisMaxShare=100,axisVerified=true,axisProvenance="synthetic scale",sourceStatus="verified"}}})
      local row=StatCompass.rows[2]
      local fraction=row.fill.width/row.barWidth
      local firstWidth=row.barWidth
      UIParent.right=980
      UIParent:SetSize(980,1080)
      assert(StatCompass.visible and reads==1)
      assert(row.barWidth~=firstWidth)
      assert(math.abs(row.fill.width/row.barWidth-fraction)<0.001)
      assert(math.abs((row.markerTarget.point[4]-row.markerInset)/(row.barWidth-2*row.markerInset)-fraction)<0.001)
      CharacterFrame:SetBounds(200,600,30,560)
      assert(StatCompass.visible and reads==1)
      assert(math.abs(row.fill.width/row.barWidth-fraction)<0.001)
    ''')


def test_small_stat_keeps_fixed_axis_and_unknown_fill_hidden():
    lua = runtime_with_data()
    run(lua, '''
      GetHaste=function() return 6.8 end
      local rows=StatCompass.releaseData.cohorts[71].raid.observations
      for i=1,50 do rows[i].haste=7.1; rows[i].versatility=0 end
      GetCombatRatingBonus=function() return 0 end
      GetVersatilityBonus=function() return 0 end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local haste=StatCompass.rows[2]
      assert(haste.axis==2000 and not haste.fill.shown)
      local zero=StatCompass.rows[4]
      assert(zero.axis==2000 and not zero.fill.shown)
    ''')


def test_coincident_ticks_have_separate_vertical_extent():
    lua = runtime_with_data()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      StatCompass.Render({ratingTarget={haste={currentRating=50,targetRating=50,lowRating=50,highRating=50,
        targetPercent=20,personal=true,sampleCount=30,sourceStatus="verified"}}})
      local row=StatCompass.rows[2]
      assert(row.markerTarget.shown and row.bandCue.shown)
      assert(row.hit.current~=row.hit.target)
      assert(row.current.text=="50" and row.target.text=="Target 50")
    ''')


def test_german_and_english_text_fit_and_header_alignment_at_minimum_width():
    for locale in ("deDE", "enUS"):
        lua = runtime_with_data(locale)
        run(lua, '''
          UIParent.right=850
          CharacterFrame:SetBounds(20,420,0,424)
          Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
          local a=StatCompass
          assert(a.visible)
          local p=a.panel
          assert(a.rows[1].label.point[4]==a.rows[1].current.point[4])
          assert(a.rows[1].target.point[4]>a.rows[1].current.point[4])
          for _,font in ipairs({a.title,a.spec,a.status}) do
            assert(font:GetStringWidth()<=font.width, font.text)
          end
          for _,button in ipairs(a.buttons) do
            assert(button.caption:GetStringWidth()<=button.width-12, button.caption.text)
          end
          for i,row in ipairs(a.rows) do
            for _,font in ipairs({row.label,row.current,row.status,row.target}) do
              assert(font:GetStringWidth()<=font.width, font.text)
            end
          end
          local last=a.rows[4]
          assert(-last.status.point[5]+last.status:GetStringHeight() <= -a.status.point[5]-8)
          assert(-a.status.point[5]+a.status:GetStringHeight() <= -a.buttons[1].point[5]-8)
          assert(p.base.layer=="BACKGROUND" and p.bg.layer=="BACKGROUND")
          assert(p.base.sublevel<p.bg.sublevel)
        ''')


def test_bottom_zero_and_offscreen_host_uses_viewport_fallback():
    lua = runtime_with_data()
    run(lua, '''
      UIParent.right=1659; UIParent.top=777
      CharacterFrame.scale=1.76
      CharacterFrame:SetBounds(10,545,0,424)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local p=StatCompass.panel
      assert(StatCompass.visible)
      assert(math.abs(p:GetBottom()*p:GetEffectiveScale())<0.01)
      local reads=0
      GetHaste=function() reads=reads+1; return 15 end
      CharacterFrame:SetBounds(-20,1000,0,424)
      assert(StatCompass.visible and p.point[2]==UIParent)
      assert(p:GetLeft()*p:GetEffectiveScale()>=0)
      assert(p:GetRight()*p:GetEffectiveScale()<=1659)
      assert(math.abs(p:GetBottom()*p:GetEffectiveScale())<0.01)
      assert(reads==0)
    ''')
