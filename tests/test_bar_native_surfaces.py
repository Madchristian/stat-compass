from tests.test_addon import load_runtime, run

def test_target_marker_does_not_depend_on_mock_only_shown_field():
    lua=load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local A=StatCompass; local r=A.rows[1]
      r.markerTarget.Show=function(self) self.actualShown=true end
      r.markerTarget.shown=nil
      A.Render({ratingTarget={crit={currentRating=50,targetRating=50,targetPercent=20,personal=true,sampleCount=30,axisMaxShare=100,axisVerified=true,
        axisProvenance="synthetic",sourceStatus="verified",reference={minShare=40,meanShare=50,maxShare=60}}}})
      assert(r.markerTarget.actualShown and r.outlineTarget.shown, "native textures have no shown field")
    ''')

def test_stat_color_does_not_imply_mean_proximity_quality():
    lua=load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local A=StatCompass
      for i,key in ipairs(A.statOrder) do
        local item={currentRating=45,targetRating=50,lowRating=40,highRating=60,targetPercent=20,personal=true,sampleCount=30,
          sourceStatus="verified",reference={minShare=40,meanShare=50,maxShare=60}}
        local payload={ratingTarget={[key]=item}}
        A.Render(payload); assert(A.rows[i].fill.shown); local c=A.rows[i].fill.color
        local far=.2126*c[1]+.7152*c[2]+.0722*c[3]
        item.currentRating=50; A.Render(payload); c=A.rows[i].fill.color
        local near=.2126*c[1]+.7152*c[2]+.0722*c[3]
        assert(near==far, key.." retains its identity near the mean")
      end
    ''')
