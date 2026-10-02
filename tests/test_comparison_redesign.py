"""Synthetic budget-share presentation regressions."""
from tests.test_addon import load_runtime, run


def test_rating_axis_and_percent_fallback():
    lua = load_runtime()
    run(lua, r'''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      assert(a.rows[1].current.text=="Unknown" and not a.rows[1].fill.shown)
      a.Render({current={crit=21},shareComparison={crit={currentShare=40,
        axisMaxShare=100,axisProvenance="verified synthetic cap",axisVerified=true,
        reference={minShare=15,meanShare=30,maxShare=35},sampleCount=27,sourceStatus="verified"}}})
      local r=a.rows[1]
      assert(r.axis==100 and r.current.text=="40%")
      assert(r.fill.shown and r.markerCurrent.shown and r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      assert(math.abs(r.fill.width/r.barWidth-0.4)<0.001)
      assert(r.markerCurrent.point[4]>r.markerMax.point[4])
      assert(r.fill.color[1]==r.neutralColor[1])
      assert(r.glow.shown and r.glow.color[4]>0)
      assert(a.metadataText:find(a.Text("shareReferenceUnavailable","enUS"),1,true))
      r.hit.mean.scripts.OnEnter(r.hit.mean)
      assert(GameTooltip.text:find("Cohort average") and GameTooltip.text:find("Unknown"))
      a.SetSkin("flat"); a.SetSkin("default")
      assert(r.markerMean.shown and r.fill.shown and r.fill.texture==[[Interface\Buttons\WHITE8X8]])
    ''')


def test_invalid_axis_partial_and_symmetric_color():
    lua = load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      for _,item in ipairs({
        {currentShare=50,axisMaxShare=100,axisVerified=false,axisProvenance="x"},
        {currentShare=50,axisMaxShare=100,axisVerified=true},
        {currentShare=101,axisMaxShare=100,axisVerified=true,axisProvenance="x"},
        {currentShare={secret=true},axisMaxShare=100,axisVerified=true,axisProvenance="x"},
        {currentShare=50,axisMaxShare=0/0,axisVerified=true,axisProvenance="x"}}) do
        a.Render({current={crit=21},shareComparison={crit=item}})
        assert(not a.rows[1].fill.shown and not a.rows[1].markerCurrent.shown)
      end
      local item={currentShare=25,axisMaxShare=1000,axisVerified=true,axisProvenance="x",sourceStatus="verified",
        reference={minShare=20,meanShare=25,maxShare=30},sampleCount=13}
      a.Render({shareComparison={crit=item}})
      local r=a.rows[1]; local center=r.fill.color[1]
      item.currentShare=22.5; a.Render({shareComparison={crit=item}}); local left=r.fill.color[1]
      item.currentShare=27.5; a.Render({shareComparison={crit=item}}); local right=r.fill.color[1]
      assert(center>left and math.abs(left-right)<0.0001)
      item.reference={minShare=25,meanShare=25,maxShare=25}; item.currentShare=25
      a.Render({shareComparison={crit=item}})
      assert(r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      assert(r.markerMin.point[1]==r.markerMean.point[1] and r.markerMin.point[4]==r.markerMean.point[4])
      assert(not r.glow.shown)
      item.reference={minShare=5,meanShare=25}; a.Render({shareComparison={crit=item}})
      assert(r.markerMin.shown and r.markerMean.shown and not r.markerMax.shown and not r.glow.shown)
    ''')


def test_extreme_rating_labels_and_missing_cap_in_both_locales():
    for locale in ('enUS', 'deDE'):
        lua = load_runtime('GetLocale=function() return "deDE" end' if locale == 'deDE' else '')
        run(lua, '''
          CharacterFrame:SetBounds(20,380,0,420)
          Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
          local a=StatCompass
          local item={currentShare=100,axisMaxShare=1e308,axisVerified=true,sourceStatus="verified",
            axisProvenance="synthetic cap",reference={minShare=1e-308,meanShare=50,maxShare=100}}
          a.Render({shareComparison={mastery=item}})
          local r=a.rows[3]
          assert(r.axis==1e308 and r.fill.shown and r.fill.width<=r.barWidth)
          assert(r.target.shown~=false and r.target.text:find("50.0%",1,true))
          for _,font in ipairs({r.label,r.current,r.min,r.target,r.max}) do
            assert(font:GetStringWidth()<=font.width,font.text)
          end
          for _,mark in ipairs({r.markerCurrent,r.markerMin,r.markerMean,r.markerMax}) do
            assert(mark.point[4]>=1.5 and mark.point[4]<=r.barWidth-1.5)
          end
          item.axisVerified=false
          a.Render({shareComparison={mastery=item}})
          assert(not r.fill.shown and not r.markerMin.shown and not r.markerMean.shown)
          assert(r.min.text==a.Text("unknown","deDE") or r.min.text==a.Text("unknown","enUS"))
        ''')
