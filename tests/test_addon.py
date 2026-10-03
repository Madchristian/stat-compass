from pathlib import Path
import pytest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1] / "StatCompass"

MOCK = r'''
widgets = {frames=0, textures=0, fonts=0, callbacks={}, timers={}}
local Texture = {}
Texture.__index = Texture
function Texture:SetAllPoints() self.allPoints=true end
function Texture:SetPoint(...) self.point={...} end
function Texture:SetSize(w,h) self.width=w; self.height=h end
function Texture:SetWidth(w) self.width=w end
function Texture:SetHeight(h) self.height=h end
function Texture:ClearAllPoints() self.point=nil end
function Texture:SetTexture(value) self.texture=value end
function Texture:SetGradient(orientation, startColor, endColor)
  self.gradient={orientation,startColor,endColor}
end
function CreateColor(r,g,b,a) return {r=r,g=g,b=b,a=a} end
function Texture:SetVertexColor(...) self.color={...} end
function Texture:Show() self.shown=true end
function Texture:Hide() self.shown=false end
local Font = {}
Font.__index = Font
function Font:SetPoint(...) self.point={...} end
function Font:ClearAllPoints() self.point=nil end
function Font:SetWidth(value) self.width=value end
function Font:GetWidth() return self.width end
function Font:SetJustifyH(value) self.justify=value end
function Font:SetText(value) self.text=value end
function Font:SetTextColor(...) self.color={...} end
function Font:GetTextColor() return unpack(self.color or {1,0.82,0,1}) end
function Font:Show() self.shown=true end
function Font:Hide() self.shown=false end
function Font:GetFont() return self.fontPath or "Fonts\\FRIZQT__.TTF", self.fontSize or (self.template=="GameFontNormalLarge" and 18 or 12), self.fontFlags or "" end
function Font:SetFont(path,size,flags) self.fontPath=path; self.fontSize=size; self.fontFlags=flags; return true end
function Font:GetText() return self.text end
function Font:GetEffectiveScale() return self.parent:GetEffectiveScale() end
function Font:IsVisible() return self.shown~=false and self.parent:IsVisible() end
function Font:GetStringWidth()
  local _,continuations=string.gsub(self.text or "","[\128-\191]","")
  local _,size=self:GetFont()
  return (#(self.text or "")-continuations)*size*0.55
end
function Font:GetStringHeight() local _,size=self:GetFont(); return size end
local Frame = {}
Frame.__index = Frame
function Frame:SetSize(w,h)
  self.width=w; self.height=h
  if self.hooks and self.hooks.OnSizeChanged then self.hooks.OnSizeChanged(self,w,h) end
end
function Frame:SetWidth(w) self.width=w end
function Frame:SetHeight(h) self.height=h end
function Frame:EnableMouse(value) self.mouseEnabled=value end
function Frame:SetPoint(...) self.point={...} end
function Frame:SetAllPoints(...) self.point={"ALL",...} end
function Frame:ClearAllPoints() self.point=nil end
function Frame:StopMovingOrSizing() self.stopped=true end
function Frame:GetWidth() return self.width end
local function anchor(self)
  if not self.point or not self.parent then return nil end
  local p=self.point
  local ref=p[2] or self.parent
  local rs=ref:GetEffectiveScale()
  local s=self:GetEffectiveScale()
  local x=((p[3]=="TOPRIGHT") and ref:GetRight() or ref:GetLeft())*rs
  local y=ref:GetTop()*rs
  local left=(x+(p[4] or 0)*s)/s
  if p[1]=="TOPRIGHT" then left=left-(self.width or 0) end
  return left,(y+(p[5] or 0)*s)/s
end
function Frame:GetLeft() if self.left then return self.left end; local x=anchor(self); return x or 300 end
function Frame:GetRight() if self.right then return self.right end; return self:GetLeft()+(self.width or 300) end
function Frame:GetTop() if self.top then return self.top end; local _,y=anchor(self); return y or 900 end
function Frame:GetBottom() if self.bottom then return self.bottom end; return self:GetTop()-(self.height or 600) end
function Frame:GetHeight() return self.height end
function Frame:GetFrameLevel() return self.frameLevel or (self.parent and self.parent.GetFrameLevel and self.parent:GetFrameLevel()+1) or 0 end
function Frame:SetFrameLevel(level) self.frameLevel=level end
function Frame:GetEffectiveScale() return (self.scale or 1)*((self.parent and self.parent:GetEffectiveScale()) or 1) end
function Frame:SetScale(scale) self.scale=scale end
function Frame:SetBounds(left,right,bottom,top)
  self.left,self.right,self.bottom,self.top=left,right,bottom,top
  self:SetPoint("TOPLEFT",self.parent,"TOPLEFT",left,top)
end
function Frame:CreateTexture(_,layer,_,sublevel)
  widgets.textures=widgets.textures+1
  return setmetatable({layer=layer,sublevel=sublevel or 0}, Texture)
end
function Frame:CreateFontString(_,_,template)
  widgets.fonts=widgets.fonts+1
  local font=setmetatable({template=template,parent=self}, Font)
  self.regions=self.regions or {}; table.insert(self.regions,font)
  return font
end
function Frame:GetRegions() return unpack(self.regions or {}) end
function Frame:GetChildren() return unpack(self.children or {}) end
function Frame:SetScript(name,fn) self.scripts[name]=fn end
function Frame:HookScript(name,fn) self.hooks[name]=fn end
function Frame:RegisterEvent(name) self.events[name]=true end
function Frame:IsShown() return self.shown end
function Frame:IsVisible() return self.shown and (not self.parent or self.parent:IsVisible()) end
local function visibilityChanged(frame, states)
  local before=states[frame]
  local after=frame:IsVisible()
  if before ~= after then
    local event=after and "OnShow" or "OnHide"
    if frame.scripts[event] then frame.scripts[event](frame) end
    if frame.hooks[event] then frame.hooks[event](frame) end
  end
  for _,child in ipairs(frame.children or {}) do
    visibilityChanged(child, states)
  end
end
local function remember(frame, states)
  states=states or {}
  states[frame]=frame:IsVisible()
  for _,child in ipairs(frame.children or {}) do remember(child,states) end
  return states
end
function Frame:Show()
  if self.shown then return end
  local states=remember(self)
  self.shown=true
  visibilityChanged(self,states)
end
function Frame:Hide()
  if not self.shown then return end
  local states=remember(self)
  self.shown=false
  visibilityChanged(self,states)
end
function CreateFrame(kind,name,parent)
  assert(kind=="Frame" or kind=="Button")
  widgets.frames=widgets.frames+1
  local frame=setmetatable({scripts={},hooks={},events={},shown=false,parent=parent,kind=kind},Frame)
  if parent then parent.children=parent.children or {}; table.insert(parent.children,frame) end
  if name then _G[name]=frame end
  return frame
end
function hooksecurefunc(target,method,after)
  local before=target[method]
  assert(type(before)=="function")
  target[method]=function(self,...)
    local result=before(self,...)
    after(self,...)
    return result
  end
end
UIParent={shown=true,children={},GetRight=function(self) return self.right or 1920 end,GetLeft=function(self) return self.left or 0 end,
  GetTop=function(self) return self.top or 1080 end,GetBottom=function(self) return self.bottom or 0 end,
  GetEffectiveScale=function(self) return self.scale or 1 end}
UIParent.SetScale=Frame.SetScale
UIParent.SetSize=Frame.SetSize
UIParent.HookScript=Frame.HookScript
UIParent.hooks={}
function UIParent:IsVisible() return self.shown end
function UIParent:Hide() if not self.shown then return end; local states=remember(self); self.shown=false; for _,child in ipairs(self.children) do visibilityChanged(child,states) end end
function UIParent:Show() if self.shown then return end; local states=remember(self); self.shown=true; for _,child in ipairs(self.children) do visibilityChanged(child,states) end end
CharacterFrame=CreateFrame("Frame","CharacterFrame",UIParent)
PaperDollFrame=CreateFrame("Frame","PaperDollFrame",CharacterFrame)
local tooltipOwner
GameTooltip={SetOwner=function(self,owner,anchor) tooltipOwner=owner; self.anchor=anchor end,
  IsOwned=function(self,owner) return tooltipOwner==owner end,
  SetText=function(self,value) self.text=value end,Show=function(self) self.shown=true end,
  Hide=function(self) self.shown=false end}
function GetLocale() return "enUS" end
function GetPhysicalScreenSize() return 1920,1080 end
function GetBuildInfo() return "12.1.0","69933","Oct 2 2026",120100 end
function UnitLevel(unit) assert(unit=="player"); return 90 end
function InCombatLockdown() return false end
function GetServerTime() return 1800000000 end
function GetCritChance() return 20 end
function GetRangedCritChance() return 19 end
function GetSpellCritChance(school) assert(school>=2 and school<=7); return 21 end
function GetHaste() return 15 end
function GetMasteryEffect() return 32 end
function GetCombatRatingBonus(rating) assert(rating==29); return 10 end
function GetVersatilityBonus(rating) assert(rating==29); return 2 end
C_SpecializationInfo={GetSpecialization=function() return 1 end,GetSpecializationInfo=function(index) assert(index==1); return 71 end}
C_Timer={After=function(delay,fn) assert(type(delay)=="number" and delay>=0); table.insert(delay==0 and widgets.callbacks or widgets.timers,{delay=delay,fn=fn}) end}
function issecretvalue(value) return type(value)=="table" and rawget(value,"secret") == true end
function Fire(event,arg) StatCompass.EventFrame.scripts.OnEvent(StatCompass.EventFrame,event,arg) end
function RunCallbacks()
  local callbacks=widgets.callbacks
  widgets.callbacks={}
  for _,entry in ipairs(callbacks) do entry.fn() end
end
'''

def load_runtime(preload=""):
    runtime = LuaRuntime(unpack_returned_tuples=True)
    assert runtime.eval("_VERSION") == "Lua 5.1"
    runtime.execute(MOCK)
    if preload:
        runtime.execute(preload)
    toc = (ROOT / "StatCompass.toc").read_text(encoding="utf-8")
    for line in toc.splitlines():
        if line and not line.startswith("##"):
            runtime.execute((ROOT / line).read_text(encoding="utf-8"))
    return runtime


@pytest.fixture
def lua():
    return load_runtime()

def run(lua, code):
    lua.execute(code)

def test_toc_load_order_and_initial_show(lua):
    run(lua, '''
      assert(StatCompass.statOrder[1]=="crit" and StatCompass.statOrder[2]=="haste")
      assert(StatCompass.statOrder[3]=="mastery" and StatCompass.statOrder[4]=="versatility")
      Fire("PLAYER_LOGIN")
      assert(StatCompass.panel and not StatCompass.visible)
      CharacterFrame:Show()
      assert(not StatCompass.visible)
      PaperDollFrame:Show()
      assert(StatCompass.visible)
      assert(StatCompass.rows[1].current.text=="Unknown")
      assert(StatCompass.rows[3].current.text=="Unknown")
      assert(StatCompass.rows[4].current.text=="Unknown")
      assert(StatCompass.status.text==StatCompass.Text("targetUnavailable","enUS"))
    ''')

def test_hidden_events_and_visible_burst(lua):
    run(lua, '''
      local reads=0
      GetHaste=function() reads=reads+1; return 15 end
      Fire("PLAYER_LOGIN")
      for i=1,10 do Fire("COMBAT_RATING_UPDATE") end
      assert(reads==0 and #widgets.callbacks==0)
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(reads==1)
      for i=1,10 do Fire("COMBAT_RATING_UPDATE") end
      assert(#widgets.callbacks==1 and reads==1)
      RunCallbacks()
      assert(reads==2)
      PaperDollFrame:Hide()
      Fire("PLAYER_EQUIPMENT_CHANGED")
      assert(reads==2 and #widgets.callbacks==0)
    ''')

def test_pending_callback_hide_reopen(lua):
    run(lua, '''
      local reads=0
      GetHaste=function() reads=reads+1; return 15 end
      Fire("PLAYER_LOGIN")
      CharacterFrame:Show(); PaperDollFrame:Show()
      Fire("COMBAT_RATING_UPDATE")
      PaperDollFrame:Hide(); PaperDollFrame:Show()
      assert(reads==2)
      RunCallbacks()
      assert(reads==2)
      assert(widgets.frames==33) -- four DR label hits retained, no DR graphic hits or reopen allocation
    ''')

def test_settings_and_skins(lua):
    run(lua, r'''
      StatCompassDB={mode="bad",skin="evil",extra="discard"}
      Fire("PLAYER_LOGIN")
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.settings.mode=="mythic")
      StatCompass.SetMode("mythic")
      StatCompass.SetSkin("flat")
      assert(StatCompassDB.mode=="mythic" and StatCompassDB.skin=="flat")
      assert(StatCompass.panel.bg.texture==[[Interface\Buttons\WHITE8X8]])
      StatCompass.SetSkin("default")
      assert(StatCompass.panel.bg.texture==[[Interface\DialogFrame\UI-DialogBox-Background]])
      StatCompass.SetSkin("flat")
      assert(StatCompass.panel.bg.texture==[[Interface\Buttons\WHITE8X8]])
      StatCompass.ResetSettings()
      assert(StatCompassDB.mode=="mythic" and StatCompassDB.skin=="default")
    ''')

def test_secret_and_missing_api(lua):
    run(lua, '''
      local secret=setmetatable({secret=true},{__eq=function() error("secret equality") end,__index=function() error("secret index") end})
      StatCompassDB={mode=secret,skin=secret}
      assert(StatCompass.SanitizeSettings(StatCompassDB).mode=="mythic")
      C_SpecializationInfo=secret
      assert(StatCompass.ReadSpec()==nil)
      GetMasteryEffect=function() return secret end
      GetHaste=nil
      local stats=StatCompass.ReadStats()
      assert(stats.mastery==nil and stats.haste==nil)
      GetBuildInfo=function() return nil,nil,nil,secret end
      assert(StatCompass.GetTarget(71,"mythic")==nil)
    ''')

def test_dataset_contract_synthetic_nonshipping(lua):
    run(lua, '''
      local data={schema=3,interface=120100,clientBuild=69933,level=90,collectedAt=1800000000,observedAt=1799999000,expiresAt=1800001000,sourceURL="https://example.invalid/synthetic-test-only",rawSHA256=string.rep("a",64),permission="synthetic-test-only",cohorts={}}
      local cohort={region="EU",mode="mythic",specID=71,interface=120100,clientBuild=69933,level=90,unit="percentPoints",semanticKind="masteryEffectPercent",season="synthetic",rankingMetric="synthetic",difficulty="synthetic",partition="synthetic",observedAt=1799999000,selectedCount=50,validCount=50,observations={}}
      for i=1,50 do cohort.observations[i]={rank=i,id="test-"..i,region="EU",mode="mythic",specID=71,interface=120100,clientBuild=69933,level=90,unit="percentPoints",semanticKind="masteryEffectPercent",observedAt=1799999000,crit=20,haste=15,mastery=32,versatility=12,critRating=900,hasteRating=700,masteryRating=800,versatilityRating=400} end
      data.cohorts[71]={mythic=cohort}
      assert(StatCompass.ValidateDataset(data,120100,69933,90,1800000000))
      StatCompass.releaseData=data
      local target=StatCompass.GetTarget(71,"mythic")
      assert(target.crit==20 and target.mastery==32 and target.sample==50)
      assert(target.band.crit.low==20 and target.band.crit.high==20)
      assert(target.rating.crit.mean==900 and target.rating.haste.min==700 and target.rating.versatility.max==400)
      cohort.observations[2].masteryRating=-1
      assert(not StatCompass.ValidateDataset(data,120100,69933,90,1800000000))
      cohort.observations[2].masteryRating=800
      for i=31,50 do cohort.observations[i]=nil end
      cohort.selectedCount=30; cohort.validCount=30
      assert(StatCompass.ValidateDataset(data,120100,69933,90,1800000000))
      assert(StatCompass.GetTarget(71,"mythic").sample==30)
      for i=20,30 do cohort.observations[i]=nil end
      cohort.selectedCount=19; cohort.validCount=19
      assert(not StatCompass.ValidateDataset(data,120100,69933,90,1800000000))
      for i=19,50 do cohort.observations[i]={} for k,v in pairs(cohort.observations[1]) do cohort.observations[i][k]=v end cohort.observations[i].rank=i cohort.observations[i].id="test-"..i end
      cohort.selectedCount=50; cohort.validCount=50
      assert(StatCompass.GetTarget(71,"raid")==nil)        -- Mythic+ is the only mode
      cohort.unit="rating"
      assert(not StatCompass.ValidateDataset(data,120100,69933,90,1800000000))
      cohort.unit="percentPoints"
      cohort.observations[1].crit=101
      assert(not StatCompass.ValidateDataset(data,120100,69933,90,1800000000))
      cohort.observations[1].crit=20
      assert(not StatCompass.ValidateDataset(data,120101,69933,90,1800000000))
      assert(not StatCompass.ValidateDataset(data,120100,69933,91,1800000000))
    ''')

def test_locale_parity_and_fallback(lua):
    run(lua, '''
      for key,value in pairs(StatCompass.locale.enUS) do
        assert(type(value)=="string" and type(StatCompass.locale.deDE[key])=="string")
      end
      for key in pairs(StatCompass.locale.deDE) do assert(StatCompass.locale.enUS[key]) end
      assert(StatCompass.Text("noData","frFR")==StatCompass.locale.enUS.noData)
    ''')

def test_spec_event_and_mode_switch(lua):
    run(lua, '''
      local spec=71
      C_SpecializationInfo.GetSpecializationInfo=function(index) return spec end
      Fire("PLAYER_LOGIN")
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.Snapshot().specID==71)
      spec=72
      Fire("PLAYER_SPECIALIZATION_CHANGED","target")
      assert(#widgets.callbacks==0)
      Fire("PLAYER_SPECIALIZATION_CHANGED","player")
      assert(#widgets.callbacks==1)
      RunCallbacks()
      assert(StatCompass.Snapshot().specID==72)
      StatCompass.SetMode("mythic")
      assert(StatCompassDB.mode=="mythic" and #widgets.callbacks==0)
      RunCallbacks()
      assert(#StatCompass.buttons==3 and StatCompass.buttons[2].caption.text=="Flat dark")
      PaperDollFrame:Hide()
      local count=widgets.frames
      for i=1,4 do PaperDollFrame:Show(); PaperDollFrame:Hide() end
      assert(widgets.frames==count)
    ''')

def test_secret_nested_dataset_and_nil_functions(lua):
    run(lua, '''
      local secret=setmetatable({secret=true},{__index=function() error("secret indexed") end,__eq=function() error("secret compared") end})
      local data={schema=3,interface=120100,clientBuild=69933,level=90,collectedAt=1800000000,observedAt=1799999000,expiresAt=1800001000,sourceURL="https://example.invalid/synthetic",rawSHA256=string.rep("a",64),permission="synthetic",cohorts=secret}
      assert(not StatCompass.ValidateDataset(data,120100,69933,90,1800000000))
      data.cohorts={}
      data.sourceURL=secret
      assert(not StatCompass.ValidateDataset(data,120100,69933,90,1800000000))
      data.sourceURL="https://example.invalid/synthetic"
      C_Timer=secret
      StatCompass.SetVisible(true)
      StatCompass.QueueRefresh() -- missing/secret timer falls back safely
      assert(not StatCompass.pending)
    ''')


def test_hostile_saved_variables_on_real_load():
    lua = load_runtime('''
      local secret=setmetatable({secret=true},{__index=function() error("indexed") end})
      StatCompassDB={mode=secret,skin="flat",unknown="discard"}
    ''')
    run(lua, r'''
      Fire("ADDON_LOADED","StatCompass")
      assert(StatCompassDB.mode=="mythic" and StatCompassDB.skin=="flat")
      assert(StatCompassDB.unknown==nil)
      Fire("PLAYER_LOGIN")
      CharacterFrame:Show(); PaperDollFrame:Show()
      assert(StatCompass.panel.bg.texture==[[Interface\Buttons\WHITE8X8]])
    ''')


def test_secret_event_to_render_unknown(lua):
    run(lua, '''
      local secret={secret=true}
      Fire("PLAYER_LOGIN")
      CharacterFrame:Show(); PaperDollFrame:Show()
      GetHaste=function() return secret end
      Fire("UNIT_SPELL_HASTE","player")
      RunCallbacks()
      assert(StatCompass.rows[2].current.text:find("Unknown"))
      assert(not StatCompass.rows[2].current.text:find("0.0%%"))
    ''')


def test_secret_visibility_result_is_gated(lua):
    run(lua, '''
      local secret=setmetatable({secret=true},{__eq=function() error("secret compared") end})
      local renders=0
      local original=StatCompass.Render
      StatCompass.Render=function(snapshot) renders=renders+1; original(snapshot) end
      CharacterFrame.shown=true; PaperDollFrame.shown=true
      local visible=CharacterFrame.IsVisible
      CharacterFrame.IsVisible=function() return secret end
      Fire("PLAYER_LOGIN")
      assert(not StatCompass.visible and renders==0)
      CharacterFrame.IsVisible=visible
      CharacterFrame.hooks.OnShow() -- readable effective visibility renders normally
      assert(StatCompass.visible and renders==1)
      StatCompass.panel.IsVisible=function() return secret end
      StatCompass.Flush() -- no render or comparison of secret IsVisible result
      assert(renders==1)
    ''')
