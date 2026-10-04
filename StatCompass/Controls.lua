-- Native Settings canvas and dependency-free minimap launcher.
local A = StatCompass
local function T(key) return A.Text(key, GetLocale()) end
local function finite(value)
  return A.IsPublic(value) and type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end
local function positive(value, fallback)
  if finite(value) and value > 0 then return value end
  return fallback
end
local BORDER_SIZE, MINIMAP_GAP = 53, 3
-- Rounded quadrants in GetMinimapShape order: SE, SW, NE, NW.
local roundedQuadrants = {
  ROUND={true,true,true,true}, SQUARE={false,false,false,false},
  ["CORNER-TOPLEFT"]={false,false,false,true},
  ["CORNER-TOPRIGHT"]={false,false,true,false},
  ["CORNER-BOTTOMLEFT"]={false,true,false,false},
  ["CORNER-BOTTOMRIGHT"]={true,false,false,false},
  ["SIDE-LEFT"]={false,true,false,true}, ["SIDE-RIGHT"]={true,false,true,false},
  ["SIDE-TOP"]={false,false,true,true}, ["SIDE-BOTTOM"]={true,true,false,false},
  ["TRICORNER-TOPLEFT"]={false,true,true,true},
  ["TRICORNER-TOPRIGHT"]={true,false,true,true},
  ["TRICORNER-BOTTOMLEFT"]={true,true,false,true},
  ["TRICORNER-BOTTOMRIGHT"]={true,true,true,false},
}
local function position()
  local b = A.minimapButton
  if not b then return end
  -- SetPoint offsets use the button's units, even with an independent scale.
  local scale = positive(Minimap:GetEffectiveScale(),1)/positive(b:GetEffectiveScale(),1)
  local w = positive(Minimap:GetWidth(),140)*scale/2
  local h = positive(Minimap:GetHeight(),140)*scale/2
  local bw, bh = positive(b:GetWidth(),32)/2, positive(b:GetHeight(),32)/2
  local radians = math.rad(A.settings.minimapAngle)
  local x, y = math.cos(radians), math.sin(radians)
  -- TrackingBorder is TOPLEFT anchored: its full envelope extends right/down.
  local insetX = (x >= 0 and bw or math.max(bw,BORDER_SIZE-bw)) + MINIMAP_GAP
  local insetY = (y >= 0 and math.max(bh,BORDER_SIZE-bh) or bh) + MINIMAP_GAP
  local dx, dy = math.abs(x), math.abs(y)
  local radius = math.min(dx > 0 and (w+insetX)/dx or math.huge,
    dy > 0 and (h+insetY)/dy or math.huge)
  local shape = type(GetMinimapShape) == "function" and GetMinimapShape() or "ROUND"
  local quadrants = roundedQuadrants[shape] or roundedQuadrants.ROUND
  local quadrant = 1 + (x < 0 and 1 or 0) + (y > 0 and 2 or 0)
  if quadrants[quadrant] then
    -- Find the first non-overlapping rectangle on the saved angular ray.
    -- Ellipse distance also covers non-square round minimap frames.
    local low, high = 0, radius
    for _ = 1, 32 do
      local mid = (low+high)/2
      local nx = math.max(0,dx*mid-insetX)/w
      local ny = math.max(0,dy*mid-insetY)/h
      if nx*nx+ny*ny < 1 then low = mid else high = mid end
    end
    radius = high
  end
  b:ClearAllPoints()
  b:SetPoint("CENTER", Minimap, "CENTER", x*radius, y*radius)
end
local function dragUpdate()
  local scale = Minimap:GetEffectiveScale()
  if not finite(scale) or scale <= 0 then return end
  local cx, cy = Minimap:GetCenter()
  local x, y = GetCursorPosition()
  if not finite(cx) or not finite(cy) or not finite(x) or not finite(y) then return end
  x, y = x/scale-cx, y/scale-cy
  if not finite(x) or not finite(y) or (x == 0 and y == 0) then return end
  local radians
  if math.atan2 then radians = math.atan2(y,x)
  elseif x > 0 then radians = math.atan(y/x)
  elseif x < 0 then radians = math.atan(y/x) + (y >= 0 and math.pi or -math.pi)
  else radians = y > 0 and math.pi/2 or -math.pi/2 end
  A.SetMinimapAngle(math.deg(radians))
end
local function stopDrag(self)
  self:SetScript("OnUpdate",nil)
end
local function label(parent, y, text, large)
  local f = parent:CreateFontString(nil,"ARTWORK",large and "GameFontNormalLarge" or "GameFontNormal")
  f:SetPoint("TOPLEFT",parent,"TOPLEFT",16,y)
  f:SetWidth(460)
  f:SetJustifyH("LEFT")
  f:SetText(text)
  return f
end
local function option(parent, y, action)
  local b = CreateFrame("Button",nil,parent)
  b:SetSize(320,32)
  b:SetPoint("TOPLEFT",parent,"TOPLEFT",16,y)
  b:RegisterForClicks("LeftButtonUp")
  A.AttachButtonStyle(b)
  b.caption = b:CreateFontString(nil,"ARTWORK","GameFontNormal")
  b.caption:SetPoint("CENTER")
  b.caption:SetWidth(300)
  b:SetScript("OnClick",action)
  return b
end
function A.RefreshControls()
  if A.options then
    A.options.skin.caption:SetText(T("skin") .. ": " .. T(A.settings.skin))
    A.options.minimap.caption:SetText(T("minimap") .. ": " .. T(A.settings.minimapShown and "shown" or "hidden"))
    A.StyleButton(A.options.skin,false)
    A.StyleButton(A.options.minimap,A.settings.minimapShown)
    A.StyleButton(A.options.reset,false)
  end
  if A.minimapButton then
    position()
    if A.settings.minimapShown then A.minimapButton:Show() else A.minimapButton:Hide() end
  end
end
function A.OpenOptions()
  if A.settingsCategory and Settings and type(Settings.OpenToCategory) == "function" then
    Settings.OpenToCategory(A.settingsCategory:GetID())
  end
end
function A.InitializeControls()
  -- Called only after SavedVariables initialization (own ADDON_LOADED or login).
  if not A.settingsCategory and Settings and type(Settings.RegisterCanvasLayoutCategory) == "function"
      and type(Settings.RegisterAddOnCategory) == "function" then
    local canvas = CreateFrame("Frame",nil,UIParent)
    canvas:Hide() -- Blizzard owns its parent, anchors, visibility, scale and closing.
    label(canvas,-16,T("title"),true)
    label(canvas,-52,T("appearanceHelp"))
    A.options = {canvas=canvas}
    A.options.skin = option(canvas,-94,function() A.SetSkin(A.settings.skin == "default" and "flat" or "default") end)
    A.options.minimap = option(canvas,-138,function() A.SetMinimapShown(not A.settings.minimapShown) end)
    A.options.reset = option(canvas,-182,A.ResetPresentation)
    A.options.reset.caption:SetText(T("resetPresentation"))
    A.RefreshControls()
    label(canvas,-240,T("unavailableHelp"))
    canvas:SetScript("OnShow",A.RefreshControls)
    A.settingsCategory = Settings.RegisterCanvasLayoutCategory(canvas,T("title"))
    Settings.RegisterAddOnCategory(A.settingsCategory)
  end
  if not A.minimapButton and Minimap then
    local b = CreateFrame("Button","StatCompassMinimapButton",Minimap)
    b:SetSize(32,32)
    b:RegisterForClicks("LeftButtonUp","RightButtonUp")
    b.icon = b:CreateTexture(nil,"ARTWORK")
    b.icon:SetSize(22,22)
    b.icon:SetPoint("CENTER")
    b.icon:SetTexture("Interface\\AddOns\\StatCompass\\icon")
    b.icon:SetMask("Interface\\CharacterFrame\\TempPortraitAlphaMask")
    local border = b:CreateTexture(nil,"OVERLAY")
    border:SetSize(BORDER_SIZE,BORDER_SIZE)
    border:SetPoint("TOPLEFT",b,"TOPLEFT",0,0)
    border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    b:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
    b:SetScript("OnClick",function(_,mouseButton)
      if mouseButton == "RightButton" then A.OpenOptions()
      elseif mouseButton == "LeftButton" and type(ToggleCharacter) == "function" then
        ToggleCharacter("PaperDollFrame",true) -- onlyShow: repeated clicks do not close equipment.
      end
    end)
    b:SetScript("OnEnter",function(self)
      GameTooltip:SetOwner(self,"ANCHOR_LEFT")
      if not A.TooltipIsOwned(self) then return end
      GameTooltip:SetText(T("title") .. "\n" .. T("minimapHelp"),1,1,1,1,true)
      GameTooltip:Show()
    end)
    b:SetScript("OnLeave",function() if A.TooltipIsOwned(b) then GameTooltip:Hide() end end)
    b:RegisterForDrag("LeftButton")
    b:SetScript("OnDragStart",function(self)
      if A.TooltipIsOwned(self) then GameTooltip:Hide() end
      self:SetScript("OnUpdate",dragUpdate)
    end)
    b:SetScript("OnDragStop",stopDrag)
    b:SetScript("OnHide",function(self) stopDrag(self); if A.TooltipIsOwned(self) then GameTooltip:Hide() end end)
    b:SetScript("OnShow",position)
    Minimap:HookScript("OnSizeChanged",position)
    b:HookScript("OnSizeChanged",position)
    hooksecurefunc(Minimap,"SetScale",position)
    hooksecurefunc(b,"SetScale",position)
    A.minimapButton = b
  end
  A.RefreshControls()
end
