from tests.test_addon import load_runtime, run

def test_mean_marker_does_not_depend_on_mock_only_shown_field():
    lua=load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local A=StatCompass; local r=A.rows[1]
      r.markerMean.Show=function(self) self.actualShown=true end
      r.markerMean.shown=nil
      A.Render({shareComparison={crit={currentShare=50,axisMaxShare=100,axisVerified=true,
        axisProvenance="synthetic",sourceStatus="verified",reference={minShare=40,meanShare=50,maxShare=60}}}})
      assert(r.markerMean.actualShown and r.outline.mean.shown, "native textures have no shown field")
    ''')

def test_nearer_mean_increases_luminance_for_each_stat():
    lua=load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local A=StatCompass
      for i,key in ipairs(A.statOrder) do
        local item={currentShare=45,axisMaxShare=100,axisVerified=true,axisProvenance="synthetic",
          sourceStatus="verified",reference={minShare=40,meanShare=50,maxShare=60}}
        local payload={shareComparison={[key]=item}}
        A.Render(payload); local c=A.rows[i].fill.color
        local far=.2126*c[1]+.7152*c[2]+.0722*c[3]
        item.currentShare=50; A.Render(payload); c=A.rows[i].fill.color
        local near=.2126*c[1]+.7152*c[2]+.0722*c[3]
        assert(near>far, key.." must brighten near mean")
      end
    ''')
