"""Rating-target handoff, executed against TOC-loaded production Lua 5.1."""
import pytest
from tests.test_addon import load_runtime, run

SETUP = '''
Fire("PLAYER_LOGIN"); CharacterFrame:Show(); PaperDollFrame:Show()
a=StatCompass; r=a.rows[1]
item={currentRating=400,targetRating=638,lowRating=600,highRating=670,
 targetPercent=21.5,sampleCount=30,sourceStatus="verified"}
payload={specID=71,specName="Arms",ratingTarget={crit=item},
 target={priority={"haste","crit","mastery","versatility"}}}
function render() if payload.ratingTarget then payload.ratingTarget.crit=item end; a.Render(payload) end
render()
'''


@pytest.mark.parametrize("mutation", [
    'item.targetRating=nil', 'item.targetRating={secret=true}', 'item.targetRating=0/0',
    'item.targetRating=math.huge', 'item.targetRating=-1', 'item.targetRating="638"',
    'item.targetPercent={secret=true}', 'item.targetPercent=math.huge',
    'item.sampleCount=0', 'item.sampleCount={secret=true}', 'item.personal={secret=true}',
    'item.personal=0', 'item.personal="false"', 'item.personal={}',
    'item.sourceStatus={secret=true}', 'item.sourceStatus="unavailable"',
])
def test_malformed_target_preserves_only_readable_own(mutation):
    lua=load_runtime()
    run(lua, SETUP+mutation+''' ; render()
      assert(r.current.text=="400")
      assert(not r.track.shown and not r.fill.shown and not r.markerTarget.shown)
      assert(not r.band.shown and not r.bandHit:IsShown())
      assert(r.target.text=="" and r.status.text==a.Text("targetUnavailable","enUS"))
    ''')


def test_rating_target_primary_uses_rating_points_and_only_one_marker():
    lua=load_runtime()
    run(lua, SETUP+'''
      assert(r.current.text=="400", "own rating must be primary")
      assert(r.target.text=="Target 638")
      assert(r.current:GetStringHeight()>r.target:GetStringHeight())
      assert(r.markerTarget and r.markerTarget.shown)
      assert(r.markerMin==nil and r.markerMax==nil and r.markerCurrent==nil and r.glow==nil)
      assert(r.min==nil and r.max==nil)
      assert(r.band.shown and r.band.height<=3)
      assert(r.axis==2000)
      assert(math.abs(r.fill.width/r.barWidth-400/r.axis)<0.00001)
      assert(r.status.text=="too low")
    ''')


@pytest.mark.parametrize("locale,expected", [("deDE","Prio: Tempo > Crit > Meisterschaft > Vielseitigkeit"),
                                            ("enUS","Prio: Haste > Crit > Mastery > Versatility")])
def test_priority_and_target_details(locale, expected):
    lua=load_runtime('GetLocale=function() return "'+locale+'" end')
    run(lua, SETUP+'''
      assert(a.status.text=="'''+expected+'''")
      a.metadataHit.scripts.OnEnter(a.metadataHit)
      assert(GameTooltip.text:find(a.Text("priorityHelp","'''+locale+'''"),1,true))
      item.personal=false; payload.ratingTarget.totals={targetRating=3000,ownRating=2800}; render()
      for _,role in ipairs({"current","target"}) do
        r.hit[role].scripts.OnEnter(r.hit[role])
        assert(GameTooltip.text==r.tip[role])
        assert(GameTooltip.text:find("21.5%",1,true))
        assert(GameTooltip.text:find(a.Text("targetFallback","'''+locale+'''"),1,true))
        assert(GameTooltip.text:find(string.format(a.Text("budgetWarning","'''+locale+'''"),"200"),1,true))
      end
      payload.ratingTarget.totals.ownRating=3000; render()
      assert(not r.tip.target:find(string.format(a.Text("budgetWarning","'''+locale+'''"),"200"),1,true))
    ''')


@pytest.mark.parametrize("value,state", [(599,"too low"),(600,"fits"),(638,"fits"),(670,"fits"),(671,"above")])
def test_inclusive_thresholds(value,state):
    lua=load_runtime()
    run(lua, SETUP+f'''
      item.currentRating={value}; render()
      assert(r.status.text=="{state}")
    ''')


@pytest.mark.parametrize("priority", [
    '{"haste","haste","crit","mastery"}', '{"haste","crit","mastery"}',
    '{"haste","crit","mastery","versatility","crit"}',
    '{"haste","crit","mastery",{secret=true}}',
    '{"haste","crit","mastery","|Tbad|t"}', '{secret=true}',
    'setmetatable({},{__index=function() error("hostile priority") end})',
])
def test_malformed_priority_never_invents_an_order(priority):
    lua=load_runtime()
    run(lua,SETUP+'payload.target.priority='+priority+'''; render()
      assert(a.status.text==a.Text("priorityUnavailable","enUS"))
      assert(r.target.text=="Target 638")
    ''')


@pytest.mark.parametrize("container", [
    'setmetatable({},{__index=function() error("hostile snapshot") end})',
    '{target=setmetatable({},{__index=function() error("hostile metadata") end})}',
    '{specID={secret=true},specName={secret=true},target={secret=true}}',
])
def test_hostile_snapshot_and_metadata_are_not_indexed(container):
    lua=load_runtime()
    run(lua,SETUP+'a.Render('+container+''')
      assert(r.current.text=="Unknown" and r.target.text=="")
      assert(not r.markerTarget.shown and not r.band.shown)
    ''')


def test_no_obsolete_hidden_share_widgets():
    lua=load_runtime()
    run(lua,SETUP+'''
      assert(a.headers==nil, "do not retain phantom share headings")
      assert(r.min==nil and r.max==nil and r.axisStatus==nil)
    ''')


def test_current_design_contract_documents_rating_target():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    contract=(root/'docs/secondary-budget-shares.md').read_text(encoding='utf-8')
    assert 'snapshot.ratingTarget[stat]' in contract
    assert 'targetRating' in contract and 'P40' in contract and 'P60' in contract
    assert 'Only `snapshot.shareComparison[stat]` drives' not in contract
    acceptance=(root/'docs/acceptance.md').read_text(encoding='utf-8')
    assert 'P40' in acceptance and 'Prio' in acceptance
    for name in ['README.md','StatCompass/README.txt','StatCompass/README.de.txt']:
        doc=(root/name).read_text(encoding='utf-8')
        assert 'ratingTarget' in doc
        assert 'P40' in doc and 'P60' in doc


def test_unavailable_metadata_uses_rating_target_copy():
    lua=load_runtime()
    run(lua,SETUP+'''
      a.Render({})
      assert(a.metadataText:find(a.Text("targetUnavailable","enUS"),1,true))
      assert(not a.metadataText:find("share reference",1,true))
      assert(a.Text("priorityHelp","deDE")=="Reihenfolge danach, wie viel ihres Sekundär-Budgets die Top-Spieler in den Wert stecken. Kein simulierter Wert.")
    ''')


@pytest.mark.parametrize("value", ['nil','{secret=true}','0/0','math.huge','-1','"3000"'])
def test_bad_totals_do_not_invent_budget_warning(value):
    lua=load_runtime()
    run(lua,SETUP+'payload.ratingTarget.totals={targetRating='+value+',ownRating=0}; render()'+'''
      assert(not r.tip.target:find("exceed",1,true))
      assert(r.target.text=="Target 638")
    ''')
