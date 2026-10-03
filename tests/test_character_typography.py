"""Perceived character-stat sizes; real Lua 5.1, no external font copying."""
import pytest
from tests.test_addon import load_runtime, run


@pytest.mark.parametrize("host_scale", [1, 2])
@pytest.mark.parametrize("physical,scale", [(1080, .64), (1440, .64), (2160, .64), (1440, 768/1440)])
def test_host_font_uses_effective_scale_not_nominal_ten(physical, scale, host_scale):
    lua = load_runtime(f'''
      GetLocale=function() return "deDE" end
      UIParent.scale={scale}; UIParent.top=768/UIParent.scale
      UIParent.right=(768*16/9)/UIParent.scale
      GetPhysicalScreenSize=function() return {physical}*16/9,{physical} end
      CharacterFrame:SetBounds(20,420,100,524)
      host=CreateFrame("Frame","EUI_CharSheet_StatsPanel",CharacterFrame)
      section=CreateFrame("Frame",nil,host)
      host:SetScale({host_scale})
      host:Show(); section:Show()
      hostLabel=section:CreateFontString(nil,"OVERLAY")
      hostLabel:SetFont("external-font-do-not-copy",10,"")
      hostLabel:SetText("Tempo")
    ''')
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      a.Render({ratingTarget={haste={currentRating=19,targetRating=638,lowRating=600,highRating=670,targetPercent=20,personal=true,sampleCount=30,sourceStatus="verified"}}})
      local path,size=a.rows[2].current:GetFont()
      local wanted=10*hostLabel:GetEffectiveScale()/a.panel:GetEffectiveScale()
      -- Bounded to readable default and available row clearance.
      local d=math.max(0,math.min(1,(a.panel:GetHeight()-424)/326))
      assert(math.abs(size-math.max(20,math.min(21+3*d,wanted)))<0.01,"host apparent font size")
      assert(path~="external-font-do-not-copy")
      assert(a.rows[2].label:GetStringHeight()<size)
      assert(a.rows[4].label:GetStringWidth()<=a.rows[4].label:GetWidth())
      assert(math.abs(a.panel:GetHeight()*a.panel:GetEffectiveScale()-424*CharacterFrame:GetEffectiveScale())<0.01)
      -- Cached region: repeated shown geometry does not enumerate the host again.
      host.GetChildren=function() error("repeat traversal") end
      host.GetRegions=function() error("repeat traversal") end
      CharacterFrame:SetScale(1.01)
      PaperDollFrame:Hide()
      CharacterFrame:SetScale(1)
      assert(not a.visible and not a.panel.scripts.OnUpdate)
    ''')


def test_fallback_is_modestly_larger_and_keeps_dense_geometry():
    lua = load_runtime('GetLocale=function() return "deDE" end')
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      a.Layout(450,424)
      local _,size=a.rows[1].current:GetFont()
      assert(size==20,"fallback larger than old 18")
      assert(-a.rows[1].label.point[5]>=-a.spec.point[5]+a.spec:GetStringHeight()+4)
      local row=a.rows[1]
      local inkTop=-row.track.point[5]+(row.track.height-row.outlineTarget.height)/2
      assert(inkTop>=-row.current.point[5]+row.current:GetStringHeight()+2-0.001)
      for _,row in ipairs(a.rows) do
        assert(row.label:GetStringHeight()<=21)
        for _,f in ipairs({row.label,row.current,row.target,row.status}) do
          assert(f:GetStringWidth()<=f:GetWidth(),f.text)
        end
      end
      for _,b in ipairs(a.buttons) do
        local _,s=b.caption:GetFont(); assert(s>=14)
        assert(b.caption:GetStringWidth()<=b.caption:GetWidth(),b.caption.text)
      end
      local _,s=a.status:GetFont(); assert(s>=14)
      assert(a.status:GetStringWidth()<=a.status:GetWidth())
    ''')


@pytest.mark.parametrize("height", [424, 530, 750])
def test_largest_host_size_keeps_markers_german_labels_and_source_clear(height):
    lua = load_runtime('''
      GetLocale=function() return "deDE" end
      host=CreateFrame("Frame","EUI_CharSheet_StatsPanel",CharacterFrame)
      host:Show()
      f=host:CreateFontString(nil,"OVERLAY"); f:SetText("Tempo"); f:SetFont("external",100,"")
    ''')
    run(lua, f'''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; a.Layout(450,{height})
      local item={{currentRating=999999,targetRating=1e308,lowRating=1e-308,highRating=1e308,targetPercent=200,personal=false,
        sampleCount=1000000,sourceStatus="verified",reference={{minRating=1e-308,meanRating=1e308,maxRating=1e308}}}}
      a.Render({{specID=268,specName="Braumeister",target={{observedAt=1799999000}},
        ratingTarget={{crit=item,haste=item,mastery=item,versatility=item}}}})
      for _,r in ipairs(a.rows) do
        local headingBottom=-r.label.point[5]+r.label:GetStringHeight()
        local trackTop=-r.track.point[5]
        assert(trackTop+(r.track.height-r.outlineTarget.height)/2>=headingBottom+2)
        assert(-r.status.point[5]+r.status:GetStringHeight()<=-r.label.point[5]+r.hoverFrame.height+2)
        for _,font in ipairs({{r.label,r.current,r.target,r.status}}) do
          assert(font:GetStringWidth()<=font:GetWidth(),font.text)
        end
      end
      for _,font in ipairs({{a.title,a.spec,a.status}}) do
        assert(font:GetStringWidth()<=font:GetWidth(),font.text)
      end
      assert(-a.status.point[5]+a.status:GetStringHeight() < -a.buttons[1].point[5])
    ''')


@pytest.mark.parametrize("value", ['42', '{secret=true}', '{IsVisible=function() error("unavailable") end}'])
def test_unreadable_host_has_readable_fallback(value):
    lua = load_runtime('EUI_CharSheet_StatsPanel='+value)
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local _,size=StatCompass.rows[1].current:GetFont(); assert(size==20)
    ''')
