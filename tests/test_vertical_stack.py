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
 for _,b in ipairs({a.buttons[1],a.buttons[2]}) do
   gap(a.spec,b,4,"spec/mode")
   for _,h in pairs(a.headers) do
     gap(b,h,4,"mode/header")
     for _,f in ipairs({a.rows[1].label,a.rows[1].current}) do gap(h,f,4,"header/row") end
   end
 end
 for i,r in ipairs(a.rows) do
   local trackTop=top(r.track)
   for _,f in ipairs({r.label,r.current}) do
     assert(trackTop+(r.track.height-r.markerCurrent.height)/2>=bottom(f)+2-0.001,"heading/through marker")
   end
   for _,f in ipairs({r.min,r.target,r.max}) do
     assert(top(f)>=trackTop+(r.track.height+r.markerMax.height)/2+2-0.001,"marker/endpoint")
     if a.rows[i+1] then
       for _,next in ipairs({a.rows[i+1].label,a.rows[i+1].current}) do gap(f,next,2,"endpoint/next row") end
     else gap(f,a.status,4,"last endpoint/footer") end
   end
 end
 for i=3,5 do
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
