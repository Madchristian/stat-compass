"""Physical marker and small tooltip regressions, on the Lua 5.1 mock."""
from tests.test_addon import load_runtime, run
from tests.test_footer_pointer import POINTER


def test_white_through_markers_and_static_glow():
    lua = load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      local item={currentShare=50,axisMaxShare=100,axisVerified=true,
        axisProvenance="observed scale",sourceStatus="verified",sampleCount=27,
        reference={minShare=40,meanShare=50,maxShare=60}}
      a.Render({shareComparison={crit=item}})
      local r=a.rows[1]
      for _,m in ipairs({r.markerMin,r.markerMean,r.markerMax}) do
        assert(m.shown and m.point[1]=="CENTER" and m.point[3]=="LEFT")
        assert(math.abs(m.height-(r.track.height+8/a.panel:GetEffectiveScale()))<0.001)
        assert(m.color[1]==1 and m.color[2]==1 and m.color[3]==1)
      end
      assert(r.markerMean.width>r.markerMin.width)
      assert(r.markerMin.point[4]<r.markerMean.point[4] and r.markerMean.point[4]<r.markerMax.point[4])
      assert(r.glow.shown and r.glow.color[4]>0)
      local near=r.glow.color[4]
      item.currentShare=55; a.Render({shareComparison={crit=item}})
      assert(r.glow.color[4]<near)
      item.currentShare=45; a.Render({shareComparison={crit=item}})
      assert(math.abs(r.glow.color[4]-(near*0.5))<0.01)
      item.reference={minShare=50,meanShare=50,maxShare=50}
      item.currentShare=50; a.Render({shareComparison={crit=item}})
      assert(not r.glow.shown)
    ''')


def test_small_independent_value_targets_and_metadata():
    lua = load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      a.Render({current={crit=21},shareComparison={crit={currentShare=50,
        axisMaxShare=100,axisVerified=true,axisProvenance="scale",sourceStatus="verified",
        reference={minShare=40,meanShare=50,maxShare=60},sampleCount=27}}})
      local r=a.rows[1]
      assert(not a.panel.scripts.OnEnter and not r.hoverFrame.mouseEnabled)
      for _,role in ipairs({"current","min","mean","max"}) do
        local h=r.hit[role]
        assert(h and h.mouseEnabled and h.width>0 and h.width<r.barWidth)
        h.scripts.OnEnter(h)
        assert(GameTooltip.shown and GameTooltip.text==r.tip[role])
        h.scripts.OnLeave(h)
      end
      assert(r.tip.current:find("50.0%%") and not r.tip.current:find("21.0%%"))
      assert(r.tip.mean:find("Unknown") and not r.tip.mean:find("Sample"))
      assert(r.tip.max:find("Unknown") and not r.tip.max:find("cap"))
      assert(a.metadataHit and a.metadataHit.mouseEnabled)
    ''')


def test_actual_pointer_targets_and_physical_marker_matrix():
    lua = load_runtime(POINTER)
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      a.Render({shareComparison={crit={currentShare=50,axisMaxShare=100,
        axisVerified=true,axisProvenance="scale",sourceStatus="verified",
        reference={minShare=40,meanShare=50,maxShare=60}}}})
      for _,role in ipairs({"current","min","mean","max"}) do
        local h=a.rows[1].hit[role]
        local s=h:GetEffectiveScale()
        local x=(h:GetLeft()+h:GetRight())*s/2
        local y=(h:GetTop()+h:GetBottom())*s/2
        assert(PointerTarget(x,y,true)==h,role)
        assert(PointerTarget(x,y,false)==h,role)
      end
      for _,role in ipairs({"min","max"}) do
        local h=a.rows[1].markerHit[role]
        local s=h:GetEffectiveScale()
        local x=(h:GetLeft()+h:GetRight())*s/2
        local y=(h:GetTop()+h:GetBottom())*s/2
        assert(PointerTarget(x,y,true)==h,role)
        assert(PointerTarget(x,y,false)==h,role)
      end
      for _,scale in ipairs({0.8,1,1.25}) do
        a.panel:SetScale(scale); a.Layout(450,530)
        local r=a.rows[1]
        for _,m in ipairs({r.markerMin,r.markerMean,r.markerMax}) do
          assert(math.abs((m.height-r.track.height)*a.panel:GetEffectiveScale()*(a.pixelDensity or 1)-8)<0.001)
          assert(m.point[4]>=r.markerInset and m.point[4]<=r.barWidth-r.markerInset)
        end
      end
    ''')


def test_yellow_outline_survives_skin_roundtrip_and_missing_mean_has_no_glow():
    lua=load_runtime()
    run(lua, '''
      Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
      local a=StatCompass
      local item={currentShare=50,axisMaxShare=100,axisVerified=true,
        axisProvenance="scale",sourceStatus="verified",
        reference={minShare=40,meanShare=50,maxShare=60}}
      for _,skin in ipairs({"default","flat","default"}) do
        a.SetSkin(skin); a.Render({shareComparison={mastery=item}})
        local r=a.rows[3]
        assert(r.fill.color[1]>r.fill.color[3])
        for _,role in ipairs({"min","mean","max"}) do
          local mark=r["marker"..string.upper(string.sub(role,1,1))..string.sub(role,2)]
          assert(mark.color[1]==1 and mark.color[2]==1 and mark.color[3]==1)
          assert(r.outline[role].color[1]<0.05 and r.outline[role].width>mark.width)
        end
      end
      item.reference={minShare=40,maxShare=60}
      a.Render({shareComparison={mastery=item}})
      assert(not a.rows[3].glow.shown and not a.rows[3].markerMean.shown)
    ''')
