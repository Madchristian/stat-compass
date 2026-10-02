"""Independent UI review regressions, exercised by the Lua 5.1 runtime."""
from tests.test_addon import load_runtime, run


def test_source_status_gates_reference_and_axis_secret_order():
    lua = load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      local item={currentShare=50,axisMaxShare=100,axisVerified=true,
        axisProvenance="synthetic",sourceStatus="verified",
        reference={minShare=40,meanShare=50,maxShare=60}}
      a.Render({shareComparison={crit=item}})
      local r=a.rows[1]
      assert(r.markerMean.shown and r.glow.shown and r.fill.color[1]~=r.neutralColor[1])
      for _,status in ipairs({"unverified","unavailable","invalid","bogus"}) do
        item.sourceStatus=status; a.Render({shareComparison={crit=item}})
        assert(not r.markerMin.shown and not r.markerMean.shown and not r.markerMax.shown)
        assert(not r.glow.shown and r.fill.color[1]==r.neutralColor[1])
      end
      item.sourceStatus=nil; a.Render({shareComparison={crit=item}})
      assert(not r.markerMean.shown and r.fill.color[1]==r.neutralColor[1])
      item.sourceStatus="verified"; item.axisVerified={secret=true}
      a.Render({shareComparison={crit=item}})
      assert(not r.fill.shown and r.axisStatus.text==a.Text("shareAxisUnavailable","enUS"))
    ''')


def test_row_hover_refreshes_and_three_labels_are_visible():
    # The shared mock retains ownership privately, not via a fictitious .owner field.
    lua = load_runtime()
    run(lua, '''
      CharacterFrame:SetBounds(20,380,0,424)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      local item={currentShare=50,axisMaxShare=100,axisVerified=true,
        axisProvenance="synthetic",sourceStatus="verified",
        reference={minShare=50,meanShare=50,maxShare=50}}
      a.Render({shareComparison={crit=item}})
      local r=a.rows[1]
      assert(r.target.shown~=false and r.target.text:find("Mean 50.0%",1,true))
      assert(r.min:GetStringWidth()<=r.min.width and r.target:GetStringWidth()<=r.target.width and r.max:GetStringWidth()<=r.max.width)
      assert(r.markerMean.point[1]==r.markerCurrent.point[1] and r.markerMean.point[4]==r.markerCurrent.point[4])
      r.hit.current.scripts.OnEnter(r.hit.current)
      item.currentShare=52; a.Render({shareComparison={crit=item}})
      assert(GameTooltip.text==r.tip.current and GameTooltip.text:find("52.0%",1,true))
      a.Render({})
      assert(r.axisStatus.shown and r.axisStatus.text==a.Text("shareAxisUnavailable","enUS"))
      assert(GameTooltip.text==r.tip.current)
    ''')
