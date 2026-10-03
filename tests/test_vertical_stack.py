"""Complete vertical layout contract, including minimum and host-max fonts."""
import pytest
from tests.test_addon import load_runtime, run

CHECK = '''
 local function top(f) return -f.point[5] end
 local function bottom(f) return top(f)+(f.GetStringHeight and f:GetStringHeight() or f:GetHeight()) end
 local function gap(before,after,n,section)
   assert(top(after)+0.001>=bottom(before)+n,section..": "..bottom(before).." -> "..top(after))
 end
 assert(top(a.title)>=4)
 gap(a.title,a.spec,4,"title/spec")
 gap(a.spec,a.rows[1].label,4,"spec/row")
 assert(#a.buttons==3)
 for i,r in ipairs(a.rows) do
   local trackTop=top(r.track)
   gap(r.label,r.current,2,"stat/own")
   for _,f in ipairs({r.current,r.target}) do
     assert(trackTop+(r.track.height-r.outlineTarget.height)/2>=bottom(f)+2-0.001,"heading/through marker")
   end
   for _,f in ipairs({r.status}) do
     assert(top(f)>=trackTop+(r.track.height+r.outlineTarget.height)/2+2-0.001,"marker/endpoint")
     if a.rows[i+1] then
       for _,next in ipairs({a.rows[i+1].label,a.rows[i+1].current}) do gap(f,next,2,"endpoint/next row") end
     else gap(f,a.status,4,"last endpoint/footer") end
   end
 end
 for i=1,3 do
   gap(a.status,a.buttons[i],4,"status/footer button")
   assert(bottom(a.buttons[i])<=height-4+0.001,"footer/panel")
 end
'''

@pytest.mark.parametrize("locale", ["deDE", "enUS"])
@pytest.mark.parametrize("skin", ["default", "flat"])
@pytest.mark.parametrize("host", [False, True])
def test_complete_vertical_stack(locale, skin, host):
    lua = load_runtime('GetLocale=function() return "%s" end' % locale + ('''
      host=CreateFrame("Frame","EUI_CharSheet_StatsPanel",CharacterFrame); host:Show()
      f=host:CreateFontString(nil,"OVERLAY"); f:SetText("%s"); f:SetFont("external",100,"")
    ''' % ("Tempo" if locale == "deDE" else "Haste") if host else ''))
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass; a.SetSkin("%s")
      for _,width in ipairs({360,380,420,450,500}) do
        for height=420,1080 do
          a.Layout(width,height)
    ''' % skin + CHECK + '''
        end
      end
      -- Exercise the actual clamp and both attachment sides, not just Layout.
      for _,left in ipairs({20,1400}) do
        for _,ownerHeight in ipairs({336,424,530,750,1080}) do
          CharacterFrame:SetBounds(left,left+400,0,ownerHeight)
          assert(a.visible)
          local height=a.panel:GetHeight()
    ''' + CHECK + '''
        end
      end
    ''')
