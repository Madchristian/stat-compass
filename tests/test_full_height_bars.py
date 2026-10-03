"""Screenshot-directed geometry and distribution bar regressions (synthetic data)."""
from tests.test_addon import load_runtime, run
from tests.test_followup import runtime_with_data


def test_exact_cohort_extrema_and_large_mastery():
    lua = runtime_with_data()
    run(lua, '''
      local rows=StatCompass.releaseData.cohorts[71].mythic.observations
      rows[1].crit=4; rows[50].crit=81
      rows[1].mastery=150; rows[50].mastery=320
      local target=StatCompass.GetTarget(71,"mythic")
      assert(target.range.crit.min==4 and target.range.crit.max==81)
      assert(target.range.mastery.min==150 and target.range.mastery.max==320)
      assert(target.sample==50)
    ''')


def test_full_height_and_four_native_bars_in_both_skins():
    lua = runtime_with_data()
    run(lua, r'''
      CharacterFrame:SetBounds(300,700,24,774)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local p=StatCompass.panel
      assert(math.abs(p:GetTop()*p:GetEffectiveScale()-CharacterFrame:GetTop()*CharacterFrame:GetEffectiveScale())<0.01)
      assert(math.abs(p:GetBottom()*p:GetEffectiveScale()-CharacterFrame:GetBottom()*CharacterFrame:GetEffectiveScale())<0.01)
      assert(p:GetWidth()>=420 and p:GetWidth()<=500)
      assert(#StatCompass.rows==4)
      for i=1,4 do
        local r=StatCompass.rows[i]
        assert(r.track and r.fill and r.markerTarget and r.band)
        assert(r.target.text:find("%d"))          -- cohort rating range from Core
        assert(r.current.text=="Unknown" and not r.fill.shown)            -- no own rating in this mock
        assert(not r.fill.shown and r.markerTarget.shown)
        assert(r.track.width>200)
      end
      assert(p.bg.color[4]>=0.97)
      assert(p.base.texture==[[Interface\Buttons\WHITE8X8]] and p.base.color[4]==1)
      StatCompass.SetSkin("flat")
      assert(p.bg.color[4]>=0.97 and p.base.color[4]==1 and p.borders[1].width>=2)
      StatCompass.SetSkin("default")
      assert(p.bg.color[4]>=0.97 and p.base.color[4]==1 and p.borders[1].width>=2)
      assert(StatCompass.buttons[1].height>=30 and StatCompass.buttons[3].height>=30)
    ''')


def test_unknown_current_and_unavailable_cohort_hide_marks():
    lua = load_runtime()
    run(lua, '''
      GetHaste=function() return {secret=true} end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      for i=1,4 do
        local r=StatCompass.rows[i]
        assert(not r.markerTarget.shown)
        assert(r.target.text=="")
        assert(r.status.text==StatCompass.Text("targetUnavailable","enUS"))
      end
      local r=StatCompass.rows[2]
      assert(r.current.text=="Unknown")
      assert(not r.fill.shown and not r.markerTarget.shown)
    ''')


def test_endpoint_coincidence_and_current_outside_cohort_are_numbered():
    lua = runtime_with_data()
    run(lua, '''
      local rows=StatCompass.releaseData.cohorts[71].mythic.observations
      for i=1,50 do rows[i].crit=25 end
      GetCritChance=function() return 90 end
      GetRangedCritChance=function() return 90 end
      GetSpellCritChance=function() return 90 end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local r=StatCompass.rows[1]
      assert(r.target.text=="Target 900" and r.bandCue.shown)          -- coincident cohort endpoints
      assert(r.current.text=="Unknown")
      assert(r.markerTarget.shown and not r.fill.shown)
    ''')


def test_movement_resize_scale_and_viewport_reflow_without_stat_reads():
    lua = runtime_with_data("deDE")
    run(lua, '''
      local reads=0
      GetHaste=function() reads=reads+1; return 30 end
      CharacterFrame:SetBounds(300,700,24,774)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(reads==1)
      local p=StatCompass.panel
      local function matched()
        assert(math.abs(p:GetTop()*p:GetEffectiveScale()-CharacterFrame:GetTop()*CharacterFrame:GetEffectiveScale())<0.01)
        assert(math.abs(p:GetBottom()*p:GetEffectiveScale()-CharacterFrame:GetBottom()*CharacterFrame:GetEffectiveScale())<0.01)
        assert(p:GetLeft()*p:GetEffectiveScale()>=UIParent:GetLeft()*UIParent:GetEffectiveScale())
        assert(p:GetRight()*p:GetEffectiveScale()<=UIParent:GetRight()*UIParent:GetEffectiveScale())
      end
      matched()
      CharacterFrame:SetBounds(1400,1800,50,800)
      matched(); assert(p.point[1]=="TOPRIGHT")
      CharacterFrame:SetBounds(300,700,100,700)
      matched(); assert(math.abs(p:GetHeight()*p:GetEffectiveScale()-600)<0.01)
      CharacterFrame:SetScale(0.8)
      matched()
      UIParent:SetScale(0.9)
      matched()
      assert(reads==1)
      assert(StatCompass.rows[2].label.text=="Tempo")
      UIParent.right=740
      UIParent:SetSize(740,1080)
      matched()
      assert(p:GetWidth()<=740-16)
      assert(reads==1)
    ''')


def test_unfit_viewport_hides_panel_and_no_read():
    lua = load_runtime()
    run(lua, '''
      local reads=0
      GetHaste=function() reads=reads+1; return 15 end
      UIParent.right=280
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      assert(not StatCompass.visible and not StatCompass.panel:IsVisible())
      assert(reads==0)
    ''')


def test_large_finite_axis_and_marker_bounds():
    lua = runtime_with_data()
    run(lua, '''
      local rows=StatCompass.releaseData.cohorts[71].mythic.observations
      rows[1].mastery=1e-308; rows[50].mastery=1e308
      GetMasteryEffect=function() return 1e308 end
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local r=StatCompass.rows[3]
      assert(r.axis==2000) -- fixed rating axis, unaffected by extreme percentages
      assert(r.current.text=="Unknown")
      assert(r.target.text=="Target 800")
      assert(not r.fill.shown)
      for i=1,4 do
        local row=StatCompass.rows[i]
        assert(row.label:GetStringWidth()<=row.label.width)
        assert(row.current:GetStringWidth()<=row.current.width)
        assert(row.target:GetStringWidth()<=row.target.width)
        assert(row.status:GetStringWidth()<=row.status.width)
      end
    ''')
