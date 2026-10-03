"""Fixed display axis and separate build/level-bound DR guides (Lua 5.1)."""
import pytest
from tests.test_addon import load_runtime, run
from tests.test_rating_target_ui import SETUP
from tests.test_footer_pointer import POINTER


@pytest.mark.parametrize("value", [2001, 2500, 1e308])
def test_offscale_ratings_keep_numbers_and_explicit_overflow(value):
    lua=load_runtime()
    run(lua, SETUP + f'''
      item.currentRating={value}; item.targetRating={value}
      item.lowRating={value}; item.highRating={value}; render()
      assert(r.current.text:find(" >",1,true), "own overflow must be visible")
      assert(r.target.text:find(" >",1,true), "target overflow must be visible")
      assert(r.status.text:find(a.Text("bandOverflow","enUS"),1,true), "band overflow must be visible")
      assert(r.fill.width==r.barWidth and r.axis==2000)
      assert(r.tip.current:find(string.format("%.17g",{value}),1,true))
      assert(r.tip.target:find(string.format("%.17g",{value}),1,true))
      assert(r.bandTip:find(string.format("%.17g",{value}),1,true))
      assert(r.bandTip:find(a.Text("axisOverflow","enUS"),1,true))
      item.currentRating=2000; item.targetRating=2000
      item.lowRating=1800; item.highRating=2000; render()
      assert(not r.current.text:find(" >",1,true))
      assert(not r.target.text:find(" >",1,true))
      assert(not r.status.text:find(a.Text("bandOverflow","enUS"),1,true))
      item.sourceStatus="unavailable"; item.currentRating={value}; render()
      assert(r.current.text:find(" >",1,true))
      assert(not r.track.shown and not r.band.shown)
    ''')

SUPPORTED = '''
WOW_PROJECT_ID=1; WOW_PROJECT_MAINLINE=1
GetBuildInfo=function() return "12.1.0","69814","",120100 end
UnitLevel=function() return 90 end
'''


@pytest.mark.parametrize("locale", ["enUS", "deDE"])
@pytest.mark.parametrize("earlier", ["true", "false"])
def test_separate_dr_guides_and_coincident_target_remain_accessible(locale, earlier):
    lua=load_runtime(POINTER+SUPPORTED+f'GetLocale=function() return "{locale}" end')
    run(lua, SETUP+'''
      for _,key in ipairs(a.statOrder) do payload.ratingTarget[key]=item end
      render()
      local expected={1380,1320,1380,1620}
      for i,row in ipairs(a.rows) do
        assert(row.dr and row.dr.text=="DR "..expected[i], "separate DR label missing")
        assert(row.markerDR==nil and row.outlineDR==nil and row.markerHit.dr==nil, "no DR stroke or phantom hit")
        assert(row.tip.dr:find(a.Text("drHelp","'''+locale+'''"),1,true))
      end
      item.targetRating=1380; item.lowRating=1300; item.highRating=1450; render()
      assert(r.markerTarget.shown)
      for _,hit in ipairs({r.hit.dr,r.hit.target,r.markerHit.target}) do
        local s=hit:GetEffectiveScale()
        local picked=PointerTarget((hit:GetLeft()+hit:GetRight())*s/2,(hit:GetBottom()+hit:GetTop())*s/2,'''+earlier+''')
        assert(picked==hit, "coincident references must remain independently accessible")
        picked.scripts.OnEnter(picked)
        assert(a.TooltipIsOwned(hit))
      end
      r.hit.dr.scripts.OnEnter(r.hit.dr)
      item.sourceStatus="unavailable"; render()
      assert(r.markerDR==nil and r.dr.text=="" and not r.hit.dr:IsShown())
      assert(not GameTooltip.shown)
    ''')


@pytest.mark.parametrize("mutation", [
    'UnitLevel=function() return 89 end',
    'UnitLevel=function() return {secret=true} end',
    'UnitLevel=function() error("unreadable") end', 'UnitLevel=nil',
    'GetBuildInfo=function() return "x","1","",120000 end',
    'GetBuildInfo=function() return "x","1","",{secret=true} end',
    'GetBuildInfo=function() error("unreadable") end', 'GetBuildInfo=nil',
    'WOW_PROJECT_ID=2', 'WOW_PROJECT_ID={secret=true}', 'WOW_PROJECT_MAINLINE=nil',
    'UnitLevel={secret=true}', 'GetBuildInfo={secret=true}',
    'UnitLevel=function() return "90" end',
    'GetBuildInfo=function() return "x","1","","120100" end',
])
def test_unsupported_dr_context_fails_closed_without_removing_target(mutation):
    lua=load_runtime(SUPPORTED)
    run(lua, SETUP+mutation+'''; render()
      assert(r.markerDR==nil and r.outlineDR==nil and r.markerHit.dr==nil)
      assert(not r.hit.dr:IsShown() and r.dr.text=="")
      assert(r.markerTarget.shown and r.axis==2000 and r.target.text=="Target 638")
    ''')


def test_all_rating_axes_are_fixed_across_values_and_specs():
    lua = load_runtime()
    run(lua, SETUP + '''
      assert(_VERSION=="Lua 5.1")
      for _,value in ipairs({0,400,2000,2500,1e308}) do
        item.currentRating=value
        payload.specID=72
        for _,key in ipairs(a.statOrder) do payload.ratingTarget[key]=item end
        render()
        for _,row in ipairs(a.rows) do
          assert(row.axis==2000, "display scale must stay fixed")
          assert(row.axisLow.text=="0" and row.axisHigh.text=="2000")
          assert(row.axisLow.shown and row.axisHigh.shown)
          if value==0 then assert(not row.fill.shown)
          else assert(math.abs(row.fill.width/row.barWidth-math.min(value/2000,1))<0.00001) end
        end
      end
      item.targetRating=0; item.lowRating=0; item.highRating=0; render()
      assert(r.axis==2000)
      item.targetRating=2000; item.highRating=2000; render()
      assert(r.axis==2000)
      item.sourceStatus="unavailable"; render()
      assert(not r.track.shown and not r.axisLow.shown and not r.axisHigh.shown)
    ''')


@pytest.mark.parametrize("low,target,high", [(630,638,650),(638,638,638),(1900,2100,2500),(2100,2300,2500)])
def test_compressed_and_offscale_band_values_reachable_on_target_label(low,target,high):
    lua=load_runtime(POINTER+SUPPORTED)
    run(lua, SETUP+f'''
      item.lowRating={low}; item.targetRating={target}; item.highRating={high}; render()
      local hit=r.hit.target; local s=hit:GetEffectiveScale()
      for _,order in ipairs({{true,false}}) do
        local picked=PointerTarget((hit:GetLeft()+hit:GetRight())*s/2,(hit:GetBottom()+hit:GetTop())*s/2,order)
        assert(picked==hit)
        picked.scripts.OnEnter(picked)
        assert(GameTooltip.text:find(r.bandTip,1,true), "target tooltip must expose compressed band")
      end
    ''')


@pytest.mark.parametrize("locale", ["enUS", "deDE"])
@pytest.mark.parametrize("skin", ["default", "flat"])
def test_axis_dr_geometry_and_pointer_matrix(locale,skin):
    lua=load_runtime(POINTER+SUPPORTED+f'GetLocale=function() return "{locale}" end')
    run(lua, SETUP+f'a.SetSkin("{skin}");'+'''
      for _,key in ipairs(a.statOrder) do payload.ratingTarget[key]=item end
      for _,width in ipairs({360,450,500}) do
        for _,height in ipairs({424,530,750,1080}) do
          for _,scale in ipairs({0.8,1,1.2}) do
            a.panel:SetScale(scale); a.panel:SetSize(width,height); a.Layout(width,height)
            for _,value in ipairs({0,1380,2000,2001,1.79e308}) do
              item.currentRating=value; item.targetRating=value
              item.lowRating=value; item.highRating=value; render()
              for _,row in ipairs(a.rows) do
                assert(row.axis==2000 and row.markerDR==nil)
                for _,font in ipairs({row.dr,row.label,row.current,row.target,row.status,row.axisLow,row.axisHigh}) do
                  assert(font:GetStringWidth()<=font:GetWidth()+0.01, "text must fit allocated width")
                  assert(font.point[4]>=16 and font.point[4]+font:GetWidth()<=width-16+0.01)
                end
                assert(row.label.point[4]+row.label:GetWidth()<row.dr.point[4])
                assert(row.axisLow.point[4]+row.axisLow:GetWidth()<row.status.point[4])
                assert(row.status.point[4]+row.status:GetWidth()<row.axisHigh.point[4])
                assert(row.dr.point[5]-row.dr:GetStringHeight()>row.current.point[5])
                local x=row.markerTarget.point[4]
                local expected=math.min(value/2000,1)
                assert(math.abs((x-row.markerInset)/(row.barWidth-2*row.markerInset)-expected)<0.00001)
                assert(x-row.outlineTarget.width/2>=0 and x+row.outlineTarget.width/2<=row.barWidth)
              end
              for _,order in ipairs({true,false}) do
                for _,hit in ipairs({r.hit.dr,r.hit.current,r.hit.target,a.buttons[1],a.buttons[2],a.buttons[3]}) do
                  local s=hit:GetEffectiveScale()
                  assert(PointerTarget((hit:GetLeft()+hit:GetRight())*s/2,(hit:GetBottom()+hit:GetTop())*s/2,order)==hit)
                end
              end
            end
          end
        end
      end
    ''')


def test_dr_tooltip_refresh_foreign_ownership_and_collapse_no_reads():
    lua=load_runtime(SUPPORTED)
    run(lua, SETUP+'local hit=r.hit.dr;'+'''
      hit.scripts.OnEnter(hit)
      assert(a.TooltipIsOwned(hit))
      local foreign=CreateFrame("Frame"); GameTooltip:SetOwner(foreign); GameTooltip:SetText("foreign"); GameTooltip:Show()
      UnitLevel=function() return 89 end; render()
      assert(GameTooltip.shown and GameTooltip.text=="foreign")
      local reads=0
      UnitLevel=function() reads=reads+1; return 90 end
      GetBuildInfo=function() reads=reads+1; return "12.1.0","69814","",120100 end
      a.SetCollapsed(true)
      local before=reads
      render(); a.QueueRefresh(); RunCallbacks()
      assert(reads==before, "collapsed render must not read DR context")
      a.SetCollapsed(false); render()
      assert(r.dr.text=="DR 1380")
      hit.scripts.OnEnter(hit)
      UnitLevel=function() return 89 end; render()
      assert(not GameTooltip.shown and not hit:IsShown())
    ''')


def test_dr_and_axis_localization_contract():
    import re
    from pathlib import Path
    lua=load_runtime()
    en=lua.globals().StatCompass.locale.enUS
    de=lua.globals().StatCompass.locale.deDE
    assert set(en)==set(de)
    for key in ('targetHelp','axisOverflow','bandOverflow','drHelp'):
        assert re.findall(r'%[sd]',en[key])==re.findall(r'%[sd]',de[key])
        assert re.findall(r'\d+(?:\.\d+)?',en[key])==re.findall(r'\d+(?:\.\d+)?',de[key])
    for text, phrases in [(en.drHelp, ['First diminishing-return','still works','less benefit','Percentage buffs','Not a cap','User-supplied']),
                          (de.drHelp, ['ersten abnehmenden','wirkt weiterhin','weniger pro Punkt','Prozentuale Buffs','Keine Grenze','Nutzervorgabe'])]:
        for phrase in phrases:
            assert phrase in text
    root=Path(__file__).resolve().parents[1]
    for name in ('README.md','StatCompass/README.txt','StatCompass/README.de.txt','docs/secondary-budget-shares.md'):
        text=(root/name).read_text(encoding='utf-8')
        assert '0–2000' in text and '120100' in text and '1380' in text and '1320' in text and '1620' in text
        assert 'scale has headroom' not in text and '1.1 times' not in text

