"""Width fitting with native FontString metrics and actual placement clamp."""
import pytest
from tests.test_addon import load_runtime, run


def runtime(locale="deDE", fallback=False):
    return load_runtime('''
      GetLocale=function() return "%s" end
      -- FontString exposes these methods natively; no frame-wide fake fitter.
      local probe=CreateFrame("Frame",nil,CharacterFrame):CreateFontString(nil,"OVERLAY")
      local font=getmetatable(probe).__index
      function font:GetStringWidth()
        widthReads=(widthReads or 0)+1
        local _,size=self:GetFont()
        return #(self.text or "")*size*0.55
      end
      host=CreateFrame("Frame","EUI_CharSheet_StatsPanel",CharacterFrame)
      host:SetScale(2); host:Show()
      local f=host:CreateFontString(nil,"OVERLAY")
      f:SetText("%s"); f:SetFont("external",12,"")
      %s
    ''' % (locale, "Tempo" if locale == "deDE" else "Haste",
           'EUI_CharSheet_StatsPanel=nil' if fallback else ''))


CHECK = '''
  local fonts={a.title,a.spec,a.status}
  for _,b in ipairs(a.buttons) do table.insert(fonts,b.caption) end
  for _,r in ipairs(a.rows) do
    for _,f in ipairs({r.label,r.current,r.target,r.status}) do
      table.insert(fonts,f)
    end
  end
  for _,f in ipairs(fonts) do
    assert(f:GetStringWidth()<=f:GetWidth()+0.01,
      (f.text or "")..": "..f:GetStringWidth()..">"..f:GetWidth())
  end
'''


def test_actual_clamp_narrow_german_large_host():
    lua = runtime()
    run(lua, '''
      CharacterFrame:SetBounds(1152,1552,150,900)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      assert(a.panel:GetWidth()==360 and a.panel:GetHeight()==750)
      a.Render({specID=105,specName="Wiederherstellung",ratingTarget={haste={currentRating=19,targetRating=638,lowRating=600,highRating=670,targetPercent=20,personal=true,sampleCount=30,sourceStatus="verified"}}})
    ''' + CHECK + '''
      local _,size=a.rows[2].current:GetFont(); assert(size==24,"keep enlarged short labels")
      PaperDollFrame:Hide(); local count=widthReads
      a.Render({specID=105,specName="Hidden"})
      CharacterFrame:SetScale(1.1)
      assert(widthReads==count,"hidden fitting work")
    ''')


@pytest.mark.parametrize("locale", ["deDE", "enUS"])
@pytest.mark.parametrize("skin", ["default", "flat"])
@pytest.mark.parametrize("fallback", [False, True])
def test_width_matrix_dynamic_text_and_enlarged_targets(locale, skin, fallback):
    lua = runtime(locale, fallback)
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; a.SetSkin("%s")
      for _,width in ipairs({360,380,420,450,500}) do
        for _,height in ipairs({420,424,430,440,530,750,1080}) do
          a.Layout(width,height)
          for _,name in ipairs({"Wiederherstellung", "Very long dynamic specialization name", "X"}) do
            a.Render({specID=105,specName=name,ratingTarget={haste={currentRating=19,targetRating=638,lowRating=600,highRating=670,targetPercent=20,personal=true,sampleCount=30,sourceStatus="verified"}}})
    ''' % skin + CHECK + '''
          end
          local specBottom=-a.spec.point[5]+a.spec:GetStringHeight()
          assert(-a.rows[1].label.point[5]>=specBottom+3,"header padding")
          local _,size=a.rows[2].current:GetFont()
          assert(size>=20,"short labels retain enlargement")
        end
      end
    ''')
