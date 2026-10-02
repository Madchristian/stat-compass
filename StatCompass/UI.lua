local A = StatCompass
local locale = "enUS"
if A.IsPublic(GetLocale) and type(GetLocale) == "function" then
  local ok, value = pcall(GetLocale)
  if A.IsPublic(ok) and ok == true and A.IsPublic(value) and type(value) == "string" then locale = value end
end
local function T(key) return A.Text(key, locale) end
-- IsOwned(frame) is used by Blizzard_InspectUI/InspectPaperDollFrame.lua.
-- Cached hover state is not proof that the shared tooltip is still ours.
function A.TooltipIsOwned(owner)
  if not A.IsPublic(owner) or not owner or not A.IsPublic(GameTooltip) or not GameTooltip then return false end
  local fn=GameTooltip.IsOwned
  if not A.IsPublic(fn) or type(fn)~="function" then return false end
  local ok,owned=pcall(fn,GameTooltip,owner)
  return A.IsPublic(ok) and ok==true and A.IsPublic(owned) and owned==true
end
local function clearTooltipState()
  A.tooltipOpen=false; A.tooltipOwner=nil
end
local function leaveTooltip(owner)
  if A.TooltipIsOwned(owner) then GameTooltip:Hide() end
  clearTooltipState()
end
local function displayText(value)
  if not A.IsPublic(value) or type(value) ~= "string" then return T("unknown") end
  return (string.gsub(value, "|", "||"))
end
local function label(parent, x, y, width, text, large)
  local font = parent:CreateFontString(nil, "ARTWORK", large and "GameFontNormalLarge" or "GameFontNormal")
  font:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
  font:SetWidth(width)
  font:SetJustifyH("LEFT")
  font:SetText(text)
  return font
end
local function button(parent, x, y, width, text, action)
  local widget = CreateFrame("Button", nil, parent)
  widget:SetSize(width, 34)
  widget:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
  A.AttachButtonStyle(widget)
  widget.caption = widget:CreateFontString(nil, "ARTWORK", "GameFontNormal")
  widget.caption:SetPoint("CENTER")
  widget.caption:SetWidth(width-12)
  widget.caption:SetText(text)
  widget:SetScript("OnClick", action)
  return widget
end
local function number(value)
  if not A.IsPublic(value) or type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then return T("unknown") end
  if math.abs(value) >= 1000000 then return string.format("%.1e%%", value) end
  if value ~= 0 and math.abs(value) < 0.05 then return string.format("%.1e%%", value) end
  return string.format("%.1f%%", value)
end
local function ratingNumber(value)
  if not A.IsPublic(value) or type(value)~="number" or value~=value or value==math.huge or value==-math.huge then return T("unknown") end
  if value~=0 and (math.abs(value)>=1000000 or math.abs(value)<0.01) then return string.format("%.1e",value) end
  return string.format("%.0f",value)
end
local function paint(texture, path, r, g, b, a)
  texture:SetTexture(nil)
  texture:SetVertexColor(1,1,1,1)
  texture:SetTexture(path)
  texture:SetVertexColor(r,g,b,a)
end
local function usableNumber(value)
  return A.IsPublic(value) and type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end
local PALETTE = {
  crit={0.83,0.27,0.31}, haste={0.27,0.51,0.88},
  mastery={0.85,0.65,0.25}, versatility={0.30,0.72,0.48},
}
local NEUTRAL = {0.48,0.52,0.56}
local function publicTable(value)
  return A.IsPublic(value) and type(value)=="table" and value or nil
end
local function validCount(value)
  return usableNumber(value) and value>=1 and value<=1000000 and value==math.floor(value) and value or nil
end
-- Only this explicit rating payload may drive a bar. Core's percent snapshot is display-only.
local function ratingFor(snapshot,key)
  local all=publicTable(snapshot.ratingComparison)
  local item=all and publicTable(all[key])
  if not item then return nil end
  local axis=usableNumber(item.axisMaxRating) and item.axisMaxRating>0 and item.axisMaxRating or nil
  local provenance=A.IsPublic(item.axisProvenance) and type(item.axisProvenance)=="string" and item.axisProvenance~="" and item.axisProvenance or nil
  if not A.IsPublic(item.axisVerified) or item.axisVerified~=true or not provenance then axis=nil end
  local current=usableNumber(item.currentRating) and item.currentRating>=0 and item.currentRating or nil
  local ref=publicTable(item.reference)
  local bounds
  local status=A.IsPublic(item.sourceStatus) and type(item.sourceStatus)=="string" and item.sourceStatus or nil
  if ref and axis and status=="verified" then
    bounds={}
    for _,field in ipairs({{"min","minRating"},{"mean","meanRating"},{"max","maxRating"}}) do
      local value=ref[field[2]]
      if usableNumber(value) and value>=0 and (not axis or value<=axis) then bounds[field[1]]=value end
    end
    if bounds.min and bounds.max and bounds.min>bounds.max then bounds={} end
    if bounds.mean and bounds.min and bounds.mean<bounds.min then bounds.mean=nil end
    if bounds.mean and bounds.max and bounds.mean>bounds.max then bounds.mean=nil end
  end
  local n=validCount(item.sampleCount)
  return {axis=axis,provenance=provenance,current=current,bounds=bounds,n=n,status=status}
end
local NATIVE_BG = "Interface\\DialogFrame\\UI-DialogBox-Background"
local FLAT = "Interface\\Buttons\\WHITE8X8"
function A.AttachButtonStyle(widget)
  widget.bg = widget:CreateTexture(nil, "BORDER", nil, -1)
  widget.bg:SetAllPoints()
  widget.hover = widget:CreateTexture(nil, "BORDER", nil, 0)
  widget.hover:SetAllPoints()
  widget.hover:Hide()
  widget.selection = widget:CreateTexture(nil, "OVERLAY")
  widget.selection:SetPoint("BOTTOMLEFT", widget, "BOTTOMLEFT", 3, 2)
  widget.selection:SetSize(widget:GetWidth()-6, 3)
  widget.selection:Hide()
  widget:SetScript("OnEnter", function(self)
    self.hovered = not self.IsEnabled or self:IsEnabled()
    A.StyleButton(self, self.selected)
  end)
  widget:SetScript("OnLeave", function(self)
    self.hovered = false
    A.StyleButton(self, self.selected)
  end)
  widget:SetScript("OnDisable", function(self) self.hovered = false; A.StyleButton(self, self.selected) end)
  widget:SetScript("OnEnable", function(self) A.StyleButton(self, self.selected) end)
end
function A.StyleButton(widget, selected)
  local native = A.settings.skin == "default"
  local enabled = not widget.IsEnabled or widget:IsEnabled()
  widget.selected = selected and true or false
  if not enabled then
    paint(widget.bg, FLAT, 0.11,0.11,0.11,1)
    widget.hover:Hide()
    widget.selection:Hide()
    widget.caption:SetTextColor(0.48,0.48,0.48,1)
    return
  end
  if native then
    paint(widget.bg, FLAT, selected and 0.38 or 0.18, selected and 0.28 or 0.17, selected and 0.11 or 0.15, 1)
    paint(widget.hover, FLAT, 0.72,0.58,0.31,0.28)
    paint(widget.selection, FLAT, 1,0.82,0.28,1)
    widget.caption:SetTextColor(1,0.82,0,1)
  else
    paint(widget.bg, FLAT, selected and 0.17 or 0.11, selected and 0.31 or 0.15, selected and 0.42 or 0.19, 1)
    paint(widget.hover, FLAT, 0.28,0.43,0.52,0.65)
    paint(widget.selection, FLAT, 0.48,0.77,0.91,1)
    widget.caption:SetTextColor(0.91,0.95,0.98,1)
  end
  if native and selected then widget.selection:Show() else widget.selection:Hide() end
  if widget.hovered then widget.hover:Show() else widget.hover:Hide() end
end
local function place(widget, x, y, width)
  widget:ClearAllPoints()
  widget:SetPoint("TOPLEFT", A.panel, "TOPLEFT", x, y)
  if width then widget:SetWidth(width) end
  if widget.selection then widget.selection:SetWidth(widget:GetWidth()-6) end
end
local function barPosition(value, axis)
  if value <= 0 then return 0 end
  if value >= axis then return 1 end
  return value / axis
end
local function marker(row, texture, value, axis, kind)
  texture:ClearAllPoints()
  local x = 1.5 + (row.barWidth-3) * barPosition(value, axis)
  if kind == "min" then
    texture:SetPoint("BOTTOM", row.track, "TOPLEFT", x, -3)
  elseif kind == "max" then
    texture:SetPoint("TOP", row.track, "BOTTOMLEFT", x, 3)
  elseif kind == "mean" then
    texture:SetPoint("TOP", row.track, "TOPLEFT", x, 2+row.meanHeight)
  else
    texture:SetPoint("CENTER", row.track, "LEFT", x, 0)
  end
  texture:Show()
end
local function redrawBar(row)
  local item=row.cachedRating
  local current,bounds,axis=item and item.current,item and item.bounds,item and item.axis
  row.axis = axis
  if axis then row.track:Show() else row.track:Hide() end
  if axis and current and current<=axis then
    local fraction = barPosition(current, axis)
    row.fill:SetWidth(math.max(0.01, row.barWidth * fraction))
    row.fill:Show()
    marker(row, row.markerCurrent, current, axis)
  else
    row.fill:Hide(); row.markerCurrent:Hide()
  end
  for _,entry in ipairs({{"min",row.markerMin},{"mean",row.markerMean},{"max",row.markerMax}}) do
    local v=bounds and bounds[entry[1]]
    if axis and usableNumber(v) then marker(row,entry[2],v,axis,entry[1]) else entry[2]:Hide() end
  end
  if axis and bounds and usableNumber(bounds.mean) then
    row.meanStem:ClearAllPoints()
    row.meanStem:SetPoint("BOTTOM", row.track, "TOPLEFT", 1.5+(row.barWidth-3)*barPosition(bounds.mean,axis), 0)
    row.meanStem:Show()
  else row.meanStem:Hide() end
  if axis and bounds and bounds.min and bounds.max then
    local x1=1.5+(row.barWidth-3)*barPosition(bounds.min,axis)
    local x2=1.5+(row.barWidth-3)*barPosition(bounds.max,axis)
    row.interval:ClearAllPoints()
    row.interval:SetPoint("LEFT",row.track,"LEFT",x1,0)
    row.interval:SetWidth(math.max(1,x2-x1))
    row.interval:Show()
  else row.interval:Hide() end
  local color=row.palette
  if not axis or not current or current>axis or not bounds or not bounds.min or not bounds.max or not bounds.mean
      or current<bounds.min or current>bounds.max then color=NEUTRAL
  else
    local span=math.max(bounds.mean-bounds.min,bounds.max-bounds.mean)
    local ratio=span==0 and 0 or math.min(1,math.abs(current-bounds.mean)/span)
    local strength=1-0.42*ratio
    -- A dark desaturated baseline makes both brightness and saturation rise.
    color={0.12+(color[1]-0.12)*strength,
      0.14+(color[2]-0.14)*strength,
      0.16+(color[3]-0.16)*strength}
  end
  paint(row.fill,FLAT,color[1],color[2],color[3],1)
end
function A.ApplySkin()
  if not A.visible or not A.panel then return end
  local native = A.settings.skin == "default"
  paint(A.panel.base, FLAT, 0.035, 0.04, 0.055, 1)
  paint(A.panel.bg, native and NATIVE_BG or FLAT, native and 0.24 or 0.035, native and 0.20 or 0.045, native and 0.16 or 0.06, 0.99)
  for _,edge in ipairs(A.panel.borders) do
    paint(edge, FLAT, native and 0.55 or 0.19, native and 0.45 or 0.24, native and 0.26 or 0.29, 1)
  end
  for i,widget in ipairs(A.buttons) do
    local selected = (i == 1 and A.settings.mode == "raid") or (i == 2 and A.settings.mode == "mythic") or (i == 3 and native) or (i == 4 and not native)
    A.StyleButton(widget, selected)
  end
  for _,row in ipairs(A.rows) do
    paint(row.track, FLAT, native and 0.10 or 0.09, native and 0.09 or 0.13, native and 0.08 or 0.17, 1)
    paint(row.interval, FLAT, native and 0.68 or 0.40, native and 0.67 or 0.48, native and 0.62 or 0.55, 0.40)
    paint(row.markerCurrent, FLAT, 1, 1, 1, 1)
    paint(row.markerMin, FLAT, 0.77, 0.81, 0.84, 1)
    paint(row.markerMean, FLAT, 1, 0.82, 0.34, 1)
    paint(row.meanStem, FLAT, 1, 0.82, 0.34, 1)
    paint(row.markerMax, FLAT, 0.77, 0.81, 0.84, 1)
    if row.hasCache then redrawBar(row) end
  end
end
local function dateText(epoch)
  if A.IsPublic(date) and type(date) == "function" then
    local ok, value = pcall(date, "!%Y-%m-%d", epoch)
    if A.IsPublic(ok) and ok == true and A.IsPublic(value) and type(value) == "string" then return value end
  end
  return tostring(epoch)
end
local function meanLabel(row, bounds)
  local mean=bounds and bounds.mean
  row.target:SetText(mean and (T("mean") .. " " .. ratingNumber(mean)) or T("unknown"))
  if mean and row.target:GetStringWidth()>row.target:GetWidth() then
    row.target:SetText(T("meanShort") .. " " .. ratingNumber(mean))
  end
end
function A.Render(snapshot)
  if not A.visible or not A.panel then return end
  snapshot=publicTable(snapshot) or {}
  local target = publicTable(snapshot.target)
  if snapshot.specID then
    A.spec:SetText(T("spec") .. ": " .. displayText(snapshot.specName or T("unknown")) .. " (" .. snapshot.specID .. ")")
  else
    A.spec:SetText(T("noSpec"))
  end
  local firstReference
  for _,key in ipairs(A.statOrder) do
    local ref=ratingFor(snapshot,key)
    if ref and ref.n and ref.status=="verified" then firstReference=ref; break end
  end
  A.status:SetText(firstReference and (T("sample") .. " " .. firstReference.n .. (target and usableNumber(target.observedAt) and ("  |  " .. T("observedAt") .. " " .. dateText(target.observedAt)) or "")) or T("noData"))
  A.tooltipText = target and (T("distributionHelp") .. "\n" .. T("source") .. ": " .. displayText(target.sourceURL) .. "\n" .. T("collectedAt") .. ": " .. dateText(target.collectedAt) .. "  |  " .. T("expiresAt") .. ": " .. dateText(target.expiresAt) .. "\n" .. T("selected") .. ": " .. tostring(target.selectedCount) .. "  |  " .. T("valid") .. ": " .. tostring(target.validCount) .. "\n" .. displayText(target.season) .. " | " .. displayText(target.rankingMetric) .. " | " .. displayText(target.difficulty) .. " | " .. displayText(target.partition)) or (firstReference and T("distributionHelp") or T("unavailableHelp"))
  for i,key in ipairs(A.statOrder) do
    local row = A.rows[i]
    local current = publicTable(snapshot.current) and snapshot.current[key]
    current=usableNumber(current) and current or nil
    local item=ratingFor(snapshot,key)
    local bounds=item and item.bounds
    local rating=item and item.current
    local axis=item and item.axis
    row.current:SetText(rating and (ratingNumber(rating) .. " " .. T("ratingUnit")) or number(current))
    row.min:SetText(bounds and bounds.min and (T("min") .. " " .. ratingNumber(bounds.min)) or T("unknown"))
    row.max:SetText(bounds and bounds.max and (T("max") .. " " .. ratingNumber(bounds.max)) or T("unknown"))
    meanLabel(row,bounds)
    row.axisStatus:SetText(axis and "" or T("axisUnavailableShort"))
    if axis then row.axisStatus:Hide() else row.axisStatus:Show() end
    row.tooltipText=T("distributionHelp") .. "\n" .. T("current") .. ": " .. (rating and ratingNumber(rating) .. " " .. T("ratingUnit") or number(current))
      .. "  |  " .. T("min") .. ": " .. ratingNumber(bounds and bounds.min)
      .. "  |  " .. T("mean") .. ": " .. ratingNumber(bounds and bounds.mean)
      .. "  |  " .. T("max") .. ": " .. ratingNumber(bounds and bounds.max)
      .. "\n" .. (axis and (T("verifiedAxis") .. " " .. ratingNumber(axis) .. " (" .. displayText(item.provenance) .. ")") or T("axisUnavailable"))
      .. (not rating and ("\n" .. T("ratingUnavailable")) or "")
      .. (axis and rating and rating>axis and ("\n" .. T("ratingPastAxis")) or "")
      .. (item and item.n and ("\n" .. T("sample") .. " " .. item.n .. ". " .. T("sampleUncertainty")) or "")
      .. (item and item.status and ("\n" .. displayText(item.status)) or "")
    row.cachedRating, row.hasCache = item, true
    redrawBar(row)
  end
  if A.tooltipOpen then
    local owner=A.tooltipOwner
    if A.TooltipIsOwned(owner) then
      local hoverText=A.tooltipText
      for _,row in ipairs(A.rows) do
        if owner==row.hoverFrame then hoverText=row.tooltipText; break end
      end
      GameTooltip:SetText(hoverText,1,1,1,1,true)
      GameTooltip:Show()
    else
      clearTooltipState()
    end
  end
end
local function coordinate(frame, method)
  if not A.IsPublic(frame) or not frame then return nil end
  local fn = frame[method]
  if not A.IsPublic(fn) or type(fn) ~= "function" then return nil end
  local ok, value = pcall(fn, frame)
  if not A.IsPublic(ok) or ok ~= true or not usableNumber(value) then return nil end
  return value
end
local function clampPanel()
  if not A.panel then return false end
  local rootScale = coordinate(UIParent, "GetEffectiveScale")
  local ownerScale = coordinate(CharacterFrame, "GetEffectiveScale")
  local panelScale = coordinate(A.panel, "GetEffectiveScale")
  local rootLeft, rootRight = coordinate(UIParent, "GetLeft"), coordinate(UIParent, "GetRight")
  local rootBottom, rootTop = coordinate(UIParent, "GetBottom"), coordinate(UIParent, "GetTop")
  local ownerLeft, ownerRight = coordinate(CharacterFrame, "GetLeft"), coordinate(CharacterFrame, "GetRight")
  local ownerTop, ownerBottom = coordinate(CharacterFrame, "GetTop"), coordinate(CharacterFrame, "GetBottom")
  if not rootScale or not ownerScale or not panelScale or not rootLeft or not rootRight or not rootBottom or not rootTop or not ownerLeft or not ownerRight or not ownerTop or not ownerBottom then return false end
  if rootScale <= 0 or ownerScale <= 0 or panelScale <= 0 then return false end
  -- Effective scales produce WoW virtual-screen units, not physical pixels.
  -- Convert before applying pixel-sized layout limits (notably the 420-unit floor).
  if not A.IsPublic(GetPhysicalScreenSize) or type(GetPhysicalScreenSize) ~= "function" then return false end
  local ok, _, physicalHeight = pcall(GetPhysicalScreenSize)
  local virtualHeight = (rootTop-rootBottom)*rootScale
  if not A.IsPublic(ok) or ok ~= true or not usableNumber(physicalHeight) or physicalHeight <= 0 or not usableNumber(virtualHeight) or virtualHeight <= 0 then return false end
  local pixelDensity = physicalHeight/virtualHeight
  if not usableNumber(pixelDensity) or pixelDensity <= 0 then return false end
  rootScale, ownerScale, panelScale = rootScale*pixelDensity, ownerScale*pixelDensity, panelScale*pixelDensity
  local screenLeft, screenRight = rootLeft*rootScale, rootRight*rootScale
  local screenBottom, screenTop = rootBottom*rootScale, rootTop*rootScale
  local left, right, top, bottom = ownerLeft*ownerScale, ownerRight*ownerScale, ownerTop*ownerScale, ownerBottom*ownerScale
  local margin = 8*rootScale
  if not usableNumber(screenLeft) or not usableNumber(screenRight) or not usableNumber(screenBottom) or not usableNumber(screenTop) or not usableNumber(left) or not usableNumber(right) or not usableNumber(top) or not usableNumber(bottom) or not usableNumber(margin) then return false end
  local availableWidth = screenRight-screenLeft-2*margin
  local availableHeight = screenTop-screenBottom
  local height = top-bottom
  if not usableNumber(availableWidth) or not usableNumber(availableHeight) or not usableNumber(height) or height <= 0 or height > availableHeight then return false end
  local desiredScale = math.max(0.8, math.min(1, height/750))
  local localScale = desiredScale/ownerScale
  local desiredWidth = math.max(360, math.min(500, height*0.60))
  local rightSpace = screenRight-margin-right
  local leftSpace = left-screenLeft-margin
  local width = math.min(desiredWidth, availableWidth)
  local side
  -- Exterior space bounds the far edge; the attachment edge must be on-screen too.
  if right >= screenLeft and rightSpace >= 360 then side="right"; width=math.min(width,rightSpace)
  elseif left <= screenRight and leftSpace >= 360 then side="left"; width=math.min(width,leftSpace)
  else side="fallback" end
  if not usableNumber(localScale) or localScale <= 0 or not usableNumber(width) or width < 360 then return false end
  local panelTop = math.min(top, screenTop)
  panelTop = math.max(panelTop, screenBottom+height)
  A.panel:SetScale(localScale)
  panelScale = coordinate(A.panel, "GetEffectiveScale")
  if not panelScale or panelScale <= 0 then return false end
  panelScale = panelScale*pixelDensity
  local panelWidth, panelHeight = width/panelScale, height/panelScale
  if not usableNumber(panelWidth) or not usableNumber(panelHeight) or panelHeight < 420 then return false end
  A.panel:SetSize(panelWidth, panelHeight)
  A.Layout(panelWidth, panelHeight)
  local ownerOffset = (panelTop-top)/panelScale
  local rootOffsetX, rootOffsetY = -margin/panelScale, (panelTop-screenTop)/panelScale
  if not usableNumber(panelTop) or not usableNumber(ownerOffset) or not usableNumber(rootOffsetX) or not usableNumber(rootOffsetY) then return false end
  A.panel:ClearAllPoints()
  if side == "right" then
    A.panel:SetPoint("TOPLEFT", CharacterFrame, "TOPRIGHT", 0, ownerOffset)
  elseif side == "left" then
    A.panel:SetPoint("TOPRIGHT", CharacterFrame, "TOPLEFT", 0, ownerOffset)
  else
    A.panel:SetPoint("TOPRIGHT", UIParent, "TOPRIGHT", rootOffsetX, rootOffsetY)
  end
  return true
end
local function texture(parent, layer, width, height)
  local result = parent:CreateTexture(nil, layer)
  result:SetSize(width, height)
  return result
end
function A.Layout(width, height)
  local panel = A.panel
  local inset, inner = 16, width-32
  local density = math.max(0, math.min(1, (height-424)/326))
  panel.borders[1]:SetSize(width, 3)
  panel.borders[2]:SetSize(width, 3)
  panel.borders[3]:SetSize(3, height)
  panel.borders[4]:SetSize(3, height)
  place(A.title, inset, -(9+9*density), inner)
  place(A.spec, inset, -(31+21*density), inner)
  local gap = 10
  local half = (inner-gap)/2
  place(A.buttons[1], inset, -(51+44*density), half)
  place(A.buttons[2], inset+half+gap, -(51+44*density), half)
  place(A.headers.current, inset+inner*0.52, -(88+61*density), inner*0.48)
  place(A.headers.target, inset, -(88+61*density), inner*0.52)
  local start = 106+64*density
  local step = 62 + (math.max(62, (height-280)/4)-62)*density
  local trackOffset = 25+9*density
  local minOffset = 47+14*density
  local trackHeight = 16+4*density
  for i,row in ipairs(A.rows) do
    local y = -start-(i-1)*step
    place(row.label, inset, y, inner*0.52)
    place(row.current, inset+inner*0.52, y, inner*0.48)
    row.track:ClearAllPoints()
    row.track:SetPoint("TOPLEFT", panel, "TOPLEFT", inset+3, y-trackOffset)
    row.barWidth = inner-6
    row.track:SetSize(row.barWidth, trackHeight)
    row.interval:SetHeight(trackHeight+4)
    -- Keep marker ink out of the heading and endpoint-number lines.
    row.markerCurrent:SetSize(3, trackHeight+4)
    row.markerMin:SetSize(3, 5+2*density)
    row.markerMax:SetSize(3, 5+2*density)
    row.meanHeight = 5+2*density
    row.markerMean:SetSize(row.meanHeight, row.meanHeight)
    row.meanStem:SetSize(2,2)
    row.fill:ClearAllPoints()
    row.fill:SetPoint("TOPLEFT", row.track, "TOPLEFT", 0, 0)
    row.fill:SetHeight(trackHeight)
    local column=(inner-12)/3
    place(row.min, inset, y-minOffset, column)
    place(row.target, inset+column+6, y-minOffset, column)
    if row.hasCache then meanLabel(row,row.cachedRating and row.cachedRating.bounds) end
    place(row.max, inset+2*(column+6), y-minOffset, column)
    place(row.axisStatus, inset+7, y-trackOffset-1, inner-14)
    row.hoverFrame:ClearAllPoints()
    row.hoverFrame:SetPoint("TOPLEFT",panel,"TOPLEFT",inset,y)
    row.hoverFrame:SetSize(inner,step-2)
    if A.visible and row.hasCache then redrawBar(row) end
  end
  place(A.status, inset, -height+(62+46*density), inner)
  local third = (inner-2*gap)/3
  place(A.buttons[3], inset, -height+(38+21*density), third)
  place(A.buttons[4], inset+third+gap, -height+(38+21*density), third)
  place(A.buttons[5], inset+2*(third+gap), -height+(38+21*density), third)
  for _,widget in ipairs(A.buttons) do widget.caption:SetWidth(widget:GetWidth()-12) end
end
local function createPanel()
  if A.panel or not CharacterFrame or not PaperDollFrame then return end
  local panel = CreateFrame("Frame", "StatCompassPanel", CharacterFrame)
  panel:SetSize(468, 750)
  panel:EnableMouse(true)
  panel:SetPoint("TOPLEFT", CharacterFrame, "TOPRIGHT", 0, 0)
  panel.base = panel:CreateTexture(nil, "BACKGROUND", nil, -8)
  panel.base:SetAllPoints()
  panel.bg = panel:CreateTexture(nil, "BACKGROUND", nil, -7)
  panel.bg:SetAllPoints()
  panel.borders = {}
  local edges = {{"TOPLEFT",468,3}, {"BOTTOMLEFT",468,3}, {"TOPLEFT",3,750}, {"TOPRIGHT",3,750}}
  for i,edge in ipairs(edges) do
    local texture = panel:CreateTexture(nil, "BORDER")
    texture:SetPoint(edge[1], panel, edge[1], 0, 0)
    texture:SetSize(edge[2], edge[3])
    panel.borders[i] = texture
  end
  panel.border = panel.borders[1]
  A.panel = panel
  A.buttons, A.rows, A.headers = {}, {}, {}
  A.title = label(panel, 16, -18, 436, T("title"), true)
  A.spec = label(panel, 16, -52, 436, T("noSpec"), true)
  A.buttons[1] = button(panel, 16, -95, 213, T("raid"), function() A.SetMode("raid") end)
  A.buttons[2] = button(panel, 239, -95, 213, T("mythic"), function() A.SetMode("mythic") end)
  A.headers.current = label(panel, 16, -149, 100, T("current"))
  A.headers.target = label(panel, 128, -149, 324, T("observed"))
  for i,key in ipairs(A.statOrder) do
    local y = -181-(i-1)*103
    local row = {
      label = label(panel, 16, y, 215, T(key), true),
      current = label(panel, 242, y, 210, T("unknown"), true),
      min = label(panel, 16, y-61, 210, T("unknown")),
      max = label(panel, 242, y-61, 210, T("unknown")),
      target = label(panel, 16, y-61, 436, T("unknown")),
      axisStatus = label(panel, 23, y-30, 422, T("axisUnavailableShort")),
      track = texture(panel, "ARTWORK", 430, 20),
      fill = texture(panel, "ARTWORK", 1, 20),
      interval = texture(panel, "BORDER", 1, 24),
      markerCurrent = texture(panel, "OVERLAY", 3, 28),
      markerMin = texture(panel, "OVERLAY", 3, 15),
      markerMean = texture(panel, "OVERLAY", 7, 7),
      meanStem = texture(panel, "OVERLAY", 2, 2),
      markerMax = texture(panel, "OVERLAY", 3, 15),
      hoverFrame = CreateFrame("Frame",nil,panel),
      palette = PALETTE[key], neutralColor = NEUTRAL,
    }
    row.current:SetJustifyH("RIGHT")
    row.max:SetJustifyH("RIGHT")
    row.target:SetJustifyH("CENTER")
    row.axisStatus:SetJustifyH("CENTER")
    row.current:SetTextColor(1,1,1,1)
    row.min:SetTextColor(0.77,0.81,0.84,1)
    row.max:SetTextColor(0.77,0.81,0.84,1)
    row.hoverFrame:EnableMouse(true)
    row.hoverFrame:SetScript("OnEnter",function(self)
      A.tooltipOpen=true
      A.tooltipOwner=self
      GameTooltip:SetOwner(self,"ANCHOR_RIGHT")
      if not A.TooltipIsOwned(self) then clearTooltipState(); return end
      GameTooltip:SetText(row.tooltipText or T("unavailableHelp"),1,1,1,1,true)
      GameTooltip:Show()
    end)
    row.hoverFrame:SetScript("OnLeave",function()
      leaveTooltip(row.hoverFrame)
    end)
    A.rows[i] = row
  end
  A.status = label(panel, 16, -642, 436, T("noData"))
  A.buttons[3] = button(panel, 16, -691, 138, T("default"), function() A.SetSkin("default") end)
  A.buttons[4] = button(panel, 165, -691, 138, T("flat"), function() A.SetSkin("flat") end)
  A.buttons[5] = button(panel, 314, -691, 138, T("reset"), function() A.ResetSettings() end)
  A.Layout(468,750)
  panel:SetScript("OnEnter", function(self)
    if A.IsPublic(GameTooltip) and GameTooltip and A.tooltipText then
      A.tooltipOpen = true
      A.tooltipOwner = self
      GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
      if not A.TooltipIsOwned(self) then clearTooltipState(); return end
      GameTooltip:SetText(A.tooltipText, 1,1,1,1,true)
      GameTooltip:Show()
    end
  end)
  panel:SetScript("OnLeave", function() leaveTooltip(panel) end)
  panel:HookScript("OnHide", function()
    leaveTooltip(panel)
    for _,row in ipairs(A.rows) do
      if A.TooltipIsOwned(row.hoverFrame) then GameTooltip:Hide(); break end
    end
  end)
  panel:Hide()
end
local function sync()
  if not CharacterFrame or not PaperDollFrame then return end
  local characterShown = CharacterFrame:IsVisible()
  local equipmentShown = PaperDollFrame:IsVisible()
  local show = A.IsPublic(characterShown) and characterShown == true and A.IsPublic(equipmentShown) and equipmentShown == true
  if show then
    if clampPanel() then
      A.panel:Show()
      A.SetVisible(true)
    else
      A.SetVisible(false)
      A.panel:Hide()
    end
  else
    A.SetVisible(false)
    A.panel:Hide()
  end
end
local hooked
local function attach()
  if hooked or not CharacterFrame or not PaperDollFrame then return end
  createPanel()
  hooked = true
  CharacterFrame:HookScript("OnShow", sync)
  CharacterFrame:HookScript("OnHide", sync)
  PaperDollFrame:HookScript("OnShow", sync)
  PaperDollFrame:HookScript("OnHide", sync)
  CharacterFrame:HookScript("OnSizeChanged", sync)
  CharacterFrame:HookScript("OnDragStop", sync)
  if UIParent and UIParent.HookScript then UIParent:HookScript("OnSizeChanged", sync) end
  if type(hooksecurefunc) == "function" then
    for _,method in ipairs({"SetPoint", "SetAllPoints", "ClearAllPoints", "SetScale", "SetSize", "SetWidth", "SetHeight", "StopMovingOrSizing"}) do
      if type(CharacterFrame[method]) == "function" then hooksecurefunc(CharacterFrame, method, sync) end
    end
    if type(UIParent.SetScale) == "function" then hooksecurefunc(UIParent, "SetScale", sync) end
  end
  sync()
end
local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:RegisterEvent("PLAYER_LOGIN")
for _,event in ipairs({"COMBAT_RATING_UPDATE", "PLAYER_EQUIPMENT_CHANGED", "MASTERY_UPDATE", "UNIT_SPELL_HASTE", "UNIT_STATS", "UNIT_AURA", "PLAYER_SPECIALIZATION_CHANGED", "ACTIVE_TALENT_GROUP_CHANGED", "PLAYER_TALENT_UPDATE", "UNIT_LEVEL"}) do
  events:RegisterEvent(event)
end
events:SetScript("OnEvent", function(_, event, arg1)
  if event == "ADDON_LOADED" then
    if A.IsPublic(arg1) and arg1 == "StatCompass" then
      A.SaveSettings(StatCompassDB)
      if A.InitializeControls then A.InitializeControls() end
    end
    attach()
    return
  end
  if event == "PLAYER_LOGIN" then
    A.SaveSettings(StatCompassDB)
    attach()
    if A.InitializeControls then A.InitializeControls() end
    return
  end
  if event == "PLAYER_SPECIALIZATION_CHANGED" or event == "UNIT_SPELL_HASTE" or event == "UNIT_STATS" or event == "UNIT_AURA" or event == "UNIT_LEVEL" then
    if not A.IsPublic(arg1) or arg1 ~= "player" then return end
  end
  A.QueueRefresh()
end)
A.Attach = attach
A.EventFrame = events
