from tests.test_addon import load_runtime, run

def test_mean_marker_does_not_depend_on_mock_only_shown_field():
    lua=load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local A=StatCompass; local r=A.rows[1]
      r.markerMean.Show=function(self) self.actualShown=true end
      r.markerMean.shown=nil
      A.Render({ratingComparison={crit={currentRating=500,axisMaxRating=1000,axisVerified=true,
        axisProvenance="synthetic",sourceStatus="verified",reference={minRating=400,meanRating=500,maxRating=600}}}})
      assert(r.markerMean.actualShown and r.outline.mean.shown, "native textures have no shown field")
    ''')

def test_nearer_mean_increases_luminance_for_each_stat():
    lua=load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local A=StatCompass
      for i,key in ipairs(A.statOrder) do
        local item={currentRating=450,axisMaxRating=1000,axisVerified=true,axisProvenance="synthetic",
          sourceStatus="verified",reference={minRating=400,meanRating=500,maxRating=600}}
        local payload={ratingComparison={[key]=item}}
        A.Render(payload); local c=A.rows[i].fill.color
        local far=.2126*c[1]+.7152*c[2]+.0722*c[3]
        item.currentRating=500; A.Render(payload); c=A.rows[i].fill.color
        local near=.2126*c[1]+.7152*c[2]+.0722*c[3]
        assert(near>far, key.." must brighten near mean")
      end
    ''')
