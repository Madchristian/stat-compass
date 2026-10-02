"""Synthetic raw-rating presentation regressions."""
from tests.test_addon import load_runtime, run


def test_rating_axis_and_percent_fallback():
    lua = load_runtime()
    run(lua, r'''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      assert(a.rows[1].current.text:find("%%") and not a.rows[1].fill.shown)
      a.Render({current={crit=21},ratingComparison={crit={currentRating=800,
        axisMaxRating=2000,axisProvenance="verified synthetic cap",axisVerified=true,
        reference={minRating=300,meanRating=600,maxRating=700},sampleCount=27,sourceStatus="verified"}}})
      local r=a.rows[1]
      assert(r.axis==2000 and r.current.text:find("800") and not r.current.text:find("%%"))
      assert(r.fill.shown and r.markerCurrent.shown and r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      assert(math.abs(r.fill.width/r.barWidth-0.4)<0.001)
      assert(r.markerCurrent.point[4]>r.markerMax.point[4])
      assert(r.fill.color[1]==r.neutralColor[1])
      assert(r.interval.shown and r.interval.layer=="BORDER")
      assert(a.status.text:find("27") and not a.status.text:find("50"))
      r.hoverFrame.scripts.OnEnter(r.hoverFrame)
      assert(GameTooltip.text:find("arithmetic mean") and GameTooltip.text:find("27"))
      assert(GameTooltip.text:find("verified synthetic cap"))
      a.SetSkin("flat"); a.SetSkin("default")
      assert(r.markerMean.shown and r.fill.shown and r.fill.texture==[[Interface\Buttons\WHITE8X8]])
    ''')


def test_invalid_axis_partial_and_symmetric_color():
    lua = load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      for _,item in ipairs({
        {currentRating=50,axisMaxRating=100,axisVerified=false,axisProvenance="x"},
        {currentRating=50,axisMaxRating=100,axisVerified=true},
        {currentRating=101,axisMaxRating=100,axisVerified=true,axisProvenance="x"},
        {currentRating={secret=true},axisMaxRating=100,axisVerified=true,axisProvenance="x"},
        {currentRating=50,axisMaxRating=0/0,axisVerified=true,axisProvenance="x"}}) do
        a.Render({current={crit=21},ratingComparison={crit=item}})
        assert(not a.rows[1].fill.shown and not a.rows[1].markerCurrent.shown)
      end
      local item={currentRating=500,axisMaxRating=1000,axisVerified=true,axisProvenance="x",sourceStatus="verified",
        reference={minRating=400,meanRating=500,maxRating=600},sampleCount=13}
      a.Render({ratingComparison={crit=item}})
      local r=a.rows[1]; local center=r.fill.color[1]
      item.currentRating=450; a.Render({ratingComparison={crit=item}}); local left=r.fill.color[1]
      item.currentRating=550; a.Render({ratingComparison={crit=item}}); local right=r.fill.color[1]
      assert(center>left and math.abs(left-right)<0.0001)
      item.reference={minRating=500,meanRating=500,maxRating=500}; item.currentRating=500
      a.Render({ratingComparison={crit=item}})
      assert(r.markerMin.shown and r.markerMean.shown and r.markerMax.shown)
      assert(r.markerMin.point[1]~=r.markerMean.point[1])
      item.reference={minRating=100,meanRating=500}; a.Render({ratingComparison={crit=item}})
      assert(r.markerMin.shown and r.markerMean.shown and not r.markerMax.shown and not r.interval.shown)
    ''')


def test_extreme_rating_labels_and_missing_cap_in_both_locales():
    for locale in ('enUS', 'deDE'):
        lua = load_runtime('GetLocale=function() return "deDE" end' if locale == 'deDE' else '')
        run(lua, '''
          CharacterFrame:SetBounds(20,380,0,420)
          Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
          local a=StatCompass
          local item={currentRating=1e308,axisMaxRating=1e308,axisVerified=true,sourceStatus="verified",
            axisProvenance="synthetic cap",reference={minRating=1e-308,meanRating=1e308,maxRating=1e308}}
          a.Render({ratingComparison={mastery=item}})
          local r=a.rows[3]
          assert(r.axis==1e308 and r.fill.shown and r.fill.width<=r.barWidth)
          assert(r.target.shown~=false and r.target.text:find("1.0e+308",1,true))
          for _,font in ipairs({r.label,r.current,r.min,r.target,r.max}) do
            assert(font:GetStringWidth()<=font.width,font.text)
          end
          for _,mark in ipairs({r.markerCurrent,r.markerMin,r.markerMean,r.markerMax}) do
            assert(mark.point[4]>=1.5 and mark.point[4]<=r.barWidth-1.5)
          end
          item.axisVerified=false
          a.Render({ratingComparison={mastery=item}})
          assert(not r.fill.shown and not r.markerMin.shown and not r.markerMean.shown)
          assert(r.min.text==a.Text("unknown","deDE") or r.min.text==a.Text("unknown","enUS"))
        ''')
