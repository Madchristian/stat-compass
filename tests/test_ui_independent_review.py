"""Independent UI review regressions, exercised by the Lua 5.1 runtime."""
from tests.test_addon import load_runtime, run


def test_source_status_gates_reference_and_axis_secret_order():
    lua = load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      local item={currentRating=50,targetRating=50,lowRating=50,highRating=50,targetPercent=20,personal=true,sampleCount=30,axisVerified=true,
        axisProvenance="synthetic",sourceStatus="verified",
        reference={minShare=40,meanShare=50,maxShare=60}}
      a.Render({ratingTarget={crit=item}})
      local r=a.rows[1]
      assert(r.markerTarget.shown and r.glow==nil and r.fill.color[1]~=r.neutralColor[1])
      for _,status in ipairs({"unverified","unavailable","invalid","bogus"}) do
        item.sourceStatus=status; a.Render({ratingTarget={crit=item}})
        assert(not r.markerTarget.shown)
        assert(r.glow==nil and r.fill.color[1]==r.palette[1])
      end
      item.sourceStatus=nil; a.Render({ratingTarget={crit=item}})
      assert(not r.markerTarget.shown and r.fill.color[1]==r.palette[1])
      item.sourceStatus="verified"; item.targetRating={secret=true}
      a.Render({ratingTarget={crit=item}})
      assert(not r.fill.shown and r.status.text==a.Text("targetUnavailable","enUS"))
    ''')


def test_row_hover_refreshes_and_three_labels_are_visible():
    # The shared mock retains ownership privately, not via a fictitious .owner field.
    lua = load_runtime()
    run(lua, '''
      CharacterFrame:SetBounds(20,380,0,424)
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      local item={currentRating=50,targetRating=50,lowRating=50,highRating=50,targetPercent=20,personal=true,sampleCount=30,axisVerified=true,
        axisProvenance="synthetic",sourceStatus="verified",
        reference={minShare=50,meanShare=50,maxShare=50}}
      a.Render({ratingTarget={crit=item}})
      local r=a.rows[1]
      assert(r.target.shown~=false and r.target.text:find("Target 50",1,true))
      assert(r.current:GetStringWidth()<=r.current.width and r.target:GetStringWidth()<=r.target.width)
      assert(r.markerTarget.shown and r.bandCue.shown)
      r.hit.current.scripts.OnEnter(r.hit.current)
      item.currentRating=52; a.Render({ratingTarget={crit=item}})
      assert(GameTooltip.text==r.tip.current and GameTooltip.text:find("52",1,true))
      a.Render({})
      assert(r.status.shown~=false and r.status.text==a.Text("targetUnavailable","enUS"))
      assert(GameTooltip.text==r.tip.current)
    ''')
