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
  -- Raw reads prevent hostile container metatables from manufacturing values.
  local all=publicTable(rawget(snapshot,"ratingComparison"))
  local item=all and publicTable(rawget(all,key))
  if not item then return nil end
  local axis=rawget(item,"axisMaxRating")
  axis=usableNumber(axis) and axis>0 and axis or nil
  local provenance=rawget(item,"axisProvenance")
  provenance=A.IsPublic(provenance) and type(provenance)=="string" and provenance~="" and provenance or nil
  local verified=rawget(item,"axisVerified")
  if not A.IsPublic(verified) or verified~=true or not provenance then axis=nil end
  local current=rawget(item,"currentRating")
  current=usableNumber(current) and current>=0 and current or nil
  local ref=publicTable(rawget(item,"reference"))
  local bounds
  local status=rawget(item,"sourceStatus")
  status=A.IsPublic(status) and type(status)=="string" and status or nil
  if ref and axis and status=="verified" then
    bounds={}
    for _,field in ipairs({{"min","minRating"},{"mean","meanRating"},{"max","maxRating"}}) do
      local value=rawget(ref,field[2])
      if usableNumber(value) and value>=0 and (not axis or value<=axis) then bounds[field[1]]=value end
    end
    if bounds.min and bounds.max and bounds.min>bounds.max then bounds={} end
    if bounds.mean and bounds.min and bounds.mean<bounds.min then bounds.mean=nil end
    if bounds.mean and bounds.max and bounds.mean>bounds.max then bounds.mean=nil end
    -- Provider-owned nearest-rank quartiles; never derive them from extrema.
    local low,high=rawget(ref,"lowRating"),rawget(ref,"highRating")
    if usableNumber(low) and usableNumber(high) and low>=0 and high<=axis and low<=high then
      bounds.low,bounds.high=low,high
    end
  end
  local n=validCount(rawget(item,"sampleCount"))
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
local function marker(row, texture, value, axis, outline, hit)
  local x = row.markerInset + (row.barWidth-2*row.markerInset)*barPosition(value, axis)
  texture:ClearAllPoints()
  texture:SetPoint("CENTER", row.track, "LEFT", x, 0)
  texture:Show()
  if outline then
    outline:ClearAllPoints()
    outline:SetPoint("CENTER", row.track, "LEFT", x, 0)
    outline:Show()
  end
  if hit then
    hit:ClearAllPoints()
    hit:SetPoint("TOPLEFT", A.panel, "TOPLEFT", row.trackX+x-hit:GetWidth()/2,
      row.trackY+(hit:GetHeight()-row.trackHeight)/2)
    hit:Show()
  end
end
local function redrawBar(row)
  local item=row.cachedRating
  local current,bounds,axis=item and item.current,item and item.bounds,item and item.axis
  row.axis = axis
  if axis then row.track:Show() else row.track:Hide() end
  row.band:Hide(); row.bandCue:Hide()
  row.bandWidth=0; row.bandTip=nil
  if axis and bounds and bounds.low and bounds.high then
    local span=row.barWidth-2*row.markerInset
    local x1=row.markerInset+span*barPosition(bounds.low,axis)
    local x2=row.markerInset+span*barPosition(bounds.high,axis)
    row.bandWidth=x2-x1
    row.bandTip=string.format(T("middle50"),ratingNumber(bounds.low),ratingNumber(bounds.high))
    if x2>x1 then
      row.band:ClearAllPoints()
      row.band:SetPoint("LEFT",row.track,"LEFT",x1,0)
      row.band:SetSize(x2-x1,row.trackHeight)
      row.band:Show()
    else
      -- A one-physical-pixel position cue, NOT a fabricated nonzero interval.
      row.bandCue:ClearAllPoints()
      row.bandCue:SetPoint("CENTER",row.track,"LEFT",x1,0)
      row.bandCue:SetSize(row.markerInset/3,row.trackHeight)
      row.bandCue:Show()
    end
    local hitWidth=math.max(row.markerInset*2,x2-x1)
    row.bandHit:ClearAllPoints()
    row.bandHit:SetPoint("TOPLEFT",A.panel,"TOPLEFT",row.trackX+(x1+x2-hitWidth)/2,row.trackY)
    row.bandHit:SetSize(hitWidth,row.trackHeight)
    row.bandHit:Show()
  else
    row.bandHit:Hide()
    if A.TooltipIsOwned(row.bandHit) then leaveTooltip(row.bandHit) end
  end
  if axis and current and current<=axis then
    local fraction = barPosition(current, axis)
    row.fill:SetWidth(math.max(0.01, row.barWidth * fraction))
    row.fill:Show()
    marker(row, row.markerCurrent, current, axis, row.outlineCurrent, row.markerHit.current)
  else
    row.fill:Hide(); row.markerCurrent:Hide(); row.outlineCurrent:Hide(); row.markerHit.current:Hide()
  end
  for _,entry in ipairs({{"min",row.markerMin},{"mean",row.markerMean},{"max",row.markerMax}}) do
    local v=bounds and bounds[entry[1]]
    if axis and usableNumber(v) then marker(row,entry[2],v,axis,row.outline[entry[1]],row.markerHit[entry[1]])
    else entry[2]:Hide(); row.outline[entry[1]]:Hide(); row.markerHit[entry[1]]:Hide() end
  end
  if axis and current and bounds and bounds.min and bounds.max and bounds.mean and bounds.max>bounds.min then
    local spread=math.max(bounds.mean-bounds.min,bounds.max-bounds.mean)
    local proximity=math.max(0,1-math.abs(current-bounds.mean)/spread)
    if proximity>0 then
      local x=row.markerInset+(row.barWidth-2*row.markerInset)*barPosition(bounds.mean,axis)
      row.glow:ClearAllPoints()
      row.glow:SetPoint("CENTER",row.track,"LEFT",x,0)
      row.glow:SetVertexColor(row.palette[1],row.palette[2],row.palette[3],0.45*proximity)
      row.glow:Show()
    else row.glow:Hide() end
  else row.glow:Hide() end
  local color=row.palette
  if not axis or not current or current>axis or not bounds or not bounds.min or not bounds.max or not bounds.mean
      or current<bounds.min or current>bounds.max then color=NEUTRAL
  else
    local span=math.max(bounds.mean-bounds.min,bounds.max-bounds.mean)
    local ratio=span==0 and 1 or math.min(1,math.abs(current-bounds.mean)/span)
    local strength=1-0.42*ratio
    -- A dark desaturated baseline makes both brightness and saturation rise.
    color={0.12+(color[1]-0.12)*strength,
      0.14+(color[2]-0.14)*strength,
      0.16+(color[3]-0.16)*strength}
  end
  paint(row.fill,FLAT,color[1],color[2],color[3],row.bandTip and 0.65 or 1)
end
local specTextColor
local function colorSpecialization()
  if not specTextColor then specTextColor = {A.spec:GetTextColor()} end
  local r,g,b,a = unpack(specTextColor)
  if A.settings.skin == "flat" and A.IsPublic(UnitClass) and type(UnitClass) == "function" then
    local ok, _, token = pcall(UnitClass, "player")
    if A.IsPublic(ok) and ok == true and A.IsPublic(token) and type(token) == "string" then
      local colors = publicTable(RAID_CLASS_COLORS)
      local color = colors and publicTable(colors[token])
      if color and usableNumber(color.r) and usableNumber(color.g) and usableNumber(color.b)
          and color.r >= 0 and color.r <= 1 and color.g >= 0 and color.g <= 1 and color.b >= 0 and color.b <= 1 then
        r,g,b,a = color.r,color.g,color.b,1
      end
    end
  end
  A.spec:SetTextColor(r,g,b,a)
end
function A.ApplySkin()
  if not A.visible or not A.panel then return end
  colorSpecialization()
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
    paint(row.band, FLAT, 0.88,0.91,1,0.8)
    paint(row.bandCue, FLAT, 0.88,0.91,1,0.8)
    paint(row.markerCurrent, FLAT, 1, 1, 1, 1)
    for _,mark in ipairs({row.markerMin,row.markerMean,row.markerMax}) do paint(mark, FLAT, 1,1,1,1) end
    for _,mark in ipairs({row.outlineCurrent,row.outline.min,row.outline.mean,row.outline.max}) do paint(mark,FLAT,0.015,0.018,0.025,1) end
    row.glow:SetTexture("Interface\\SpellActivationOverlay\\IconAlert")
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
local fitTypography
function A.Render(snapshot)
  if not A.visible or not A.panel then return end
  colorSpecialization()
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
  A.status:SetText(firstReference and T("referenceAvailable") or T("noData"))
  A.metadataText = target and (T("sample") .. ": " .. ratingNumber(firstReference and firstReference.n) .. "\n" .. T("observedAt") .. ": " .. (usableNumber(target.observedAt) and dateText(target.observedAt) or T("unknown")) .. "\n" .. T("source") .. ": " .. displayText(target.sourceURL) .. "\n" .. T("collectedAt") .. ": " .. (usableNumber(target.collectedAt) and dateText(target.collectedAt) or T("unknown")) .. "  |  " .. T("expiresAt") .. ": " .. (usableNumber(target.expiresAt) and dateText(target.expiresAt) or T("unknown")) .. "\n" .. T("selected") .. ": " .. ratingNumber(target.selectedCount) .. "  |  " .. T("valid") .. ": " .. ratingNumber(target.validCount) .. "\n" .. displayText(target.season) .. " | " .. displayText(target.rankingMetric) .. " | " .. displayText(target.difficulty) .. " | " .. displayText(target.partition)) or T("referenceUnavailable")
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
    row.tip={
      current=T("ownRating") .. ": " .. ratingNumber(rating) .. " " .. T("ratingUnit") .. "\n" .. T("ownPercent") .. ": " .. number(current),
      min=T("observedLower") .. ": " .. ratingNumber(bounds and bounds.min) .. " " .. T("ratingUnit"),
      mean=T("cohortAverage") .. ": " .. ratingNumber(bounds and bounds.mean) .. " " .. T("ratingUnit"),
      max=T("observedUpper") .. ": " .. ratingNumber(bounds and bounds.max) .. " " .. T("ratingUnit"),
    }
    if rating and bounds and bounds.mean then
      row.tip.mean=row.tip.mean .. "\n" .. T("meanDifference") .. ": " .. string.format("%+.0f",rating-bounds.mean) .. " " .. T("ratingUnit")
    end
    row.glowTip=T("glowCloseness")
    if rating and bounds and bounds.min and bounds.max and bounds.mean and bounds.max>bounds.min
        and math.abs(rating-bounds.mean)<math.max(bounds.mean-bounds.min,bounds.max-bounds.mean) then
      row.tip.mean=row.tip.mean .. "\n" .. row.glowTip
    end
    row.cachedRating, row.hasCache = item, true
    redrawBar(row)
  end
  fitTypography()
  if A.tooltipOpen then
    local owner=A.tooltipOwner
    if A.TooltipIsOwned(owner) then
      local hoverText=owner==A.metadataHit and A.metadataText or nil
      for _,row in ipairs(A.rows) do
        if owner==row.bandHit then hoverText=row.bandTip end
        for role,hit in pairs(row.hit) do if owner==hit then hoverText=row.tip[role] end end
        for role,hit in pairs(row.markerHit) do if owner==hit then hoverText=row.tip[role] end end
      end
      if hoverText then GameTooltip:SetText(hoverText,1,1,1,1,true); GameTooltip:Show() end
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
-- Read a visible host label's size, never its font asset or private addon data.
-- One bounded discovery per shown session; subsequent geometry uses the cached
-- FontString and fresh effective scales. No OnUpdate or hidden tree traversal.
local hostFont, searchedHost
local function publicCall(object, method)
  if not A.IsPublic(object) or (type(object)~="table" and type(object)~="userdata") then return nil end
  local fn=object[method]
  if not A.IsPublic(fn) or type(fn)~="function" then return nil end
  local result={pcall(fn,object)}
  if not A.IsPublic(result[1]) or result[1]~=true then return nil end
  return result
end
local function shown(object)
  local result=publicCall(object,"IsVisible")
  return result and A.IsPublic(result[2]) and result[2]==true
end
local function hostTextSize()
  local root=EUI_CharSheet_StatsPanel
  if not shown(root) then root=CharacterStatsPane end
  if not shown(root) then return nil end
  if searchedHost~=root then
    searchedHost,hostFont=root,nil
    local budget=128
    local function visit(frame,depth)
      if budget<=0 or depth>4 or not shown(frame) then return end
      budget=budget-1
      local regions=publicCall(frame,"GetRegions")
      if regions then
        for i=2,math.min(#regions,65) do
          if budget<=0 then break end
          budget=budget-1
          local region=regions[i]
          if shown(region) then
            local text=publicCall(region,"GetText")
            if text and A.IsPublic(text[2]) and type(text[2])=="string" and text[2]==T("haste") then
              hostFont=region; return
            end
          end
        end
      end
      local children=publicCall(frame,"GetChildren")
      if children then
        for i=2,math.min(#children,65) do
          visit(children[i],depth+1)
          if hostFont or budget<=0 then break end
        end
      end
    end
    visit(root,0)
  end
  if not shown(hostFont) then return nil end
  local font=publicCall(hostFont,"GetFont")
  local scale=coordinate(hostFont,"GetEffectiveScale")
  local own=coordinate(A.panel,"GetEffectiveScale")
  if font and usableNumber(font[3]) and font[3]>0 and scale and scale>0 and own and own>0 then
    local size=font[3]*scale/own
    if usableNumber(size) then return size end
  end
end
local function sizeFont(font,size)
  font.desiredSize=size
  local current=publicCall(font,"GetFont")
  if not current or not A.IsPublic(current[2]) or type(current[2])~="string"
      or not A.IsPublic(current[4]) or type(current[4])~="string" then return end
  -- Retain our inherited Blizzard font/flags, including the user's font override.
  font:SetFont(current[2],size,current[4])
end
-- Measure rendered glyphs, not character-count estimates. Restore each widget's
-- enlarged target first so a shorter spec/value can grow again after refresh.
local function fitFont(font)
  local size=font.desiredSize
  if not size then return end
  sizeFont(font,size)
  local width=coordinate(font,"GetWidth")
  if not width or width<=0 then return end
  for _=1,3 do
    local measured=coordinate(font,"GetStringWidth")
    if not measured or measured<=width then break end
    size=math.max(1,size*(width-0.5)/measured)
    local current=publicCall(font,"GetFont")
    if not current or not A.IsPublic(current[2]) or type(current[2])~="string"
        or not A.IsPublic(current[4]) or type(current[4])~="string" then break end
    font:SetFont(current[2],size,current[4])
  end
end
local function fitHit(hit,font,align)
  if not hit or not hit.columnX then return end
  local width=math.max(1,math.min(font:GetWidth(),font:GetStringWidth()))
  local shift=align=="RIGHT" and font:GetWidth()-width or (align=="CENTER" and (font:GetWidth()-width)/2 or 0)
  hit:ClearAllPoints()
  hit:SetPoint("TOPLEFT",A.panel,"TOPLEFT",hit.columnX+shift,hit.columnY)
  hit:SetWidth(width)
end
fitTypography=function()
  fitFont(A.title); fitFont(A.spec); fitFont(A.status)
  fitHit(A.metadataHit,A.status,"LEFT")
  for _,font in pairs(A.headers) do fitFont(font) end
  for _,widget in ipairs(A.buttons) do fitFont(widget.caption) end
  for _,row in ipairs(A.rows) do
    for _,font in ipairs({row.label,row.current,row.min,row.target,row.max,row.axisStatus}) do fitFont(font) end
    fitHit(row.hit.current,row.current,"RIGHT")
    fitHit(row.hit.min,row.min,"LEFT")
    fitHit(row.hit.mean,row.target,"CENTER")
    fitHit(row.hit.max,row.max,"RIGHT")
  end
end
local function typography(density)
  local size=20
  if CharacterFrame:IsVisible() and PaperDollFrame:IsVisible() then
    size=math.max(20,math.min(21+3*density,hostTextSize() or 20))
  end
  sizeFont(A.title,size); sizeFont(A.spec,size)
  local secondary=math.max(14,math.min(14+2*density,size*0.70))
  for _,font in pairs(A.headers) do sizeFont(font,secondary) end
  sizeFont(A.status,secondary)
  for _,widget in ipairs(A.buttons) do sizeFont(widget.caption,secondary) end
  for _,row in ipairs(A.rows) do
    sizeFont(row.label,size); sizeFont(row.current,size)
    for _,font in ipairs({row.min,row.target,row.max,row.axisStatus}) do sizeFont(font,secondary) end
  end
  return secondary
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
  A.pixelDensity=pixelDensity
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
  local gutter = 0
  -- Exterior space bounds the far edge; the attachment edge must be on-screen too.
  -- These spaces are physical pixels. Preserve a small gap when space permits,
  -- shrinking the gap before sacrificing the minimum readable panel width.
  if right >= screenLeft and rightSpace >= 360 then
    side="right"; gutter=math.min(10,rightSpace-360); width=math.min(width,rightSpace-gutter)
  elseif left <= screenRight and leftSpace >= 360 then
    side="left"; gutter=math.min(10,leftSpace-360); width=math.min(width,leftSpace-gutter)
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
    A.panel:SetPoint("TOPLEFT", CharacterFrame, "TOPRIGHT", gutter/panelScale, ownerOffset)
  elseif side == "left" then
    A.panel:SetPoint("TOPRIGHT", CharacterFrame, "TOPLEFT", -gutter/panelScale, ownerOffset)
  else
    A.panel:SetPoint("TOPRIGHT", UIParent, "TOPRIGHT", rootOffsetX, rootOffsetY)
  end
  return true
end
local function texture(parent, layer, width, height, sublevel)
  local result = parent:CreateTexture(nil, layer, nil, sublevel)
  result:SetSize(width, height)
  return result
end
local function tooltipHit(parent, textFor)
  local hit=CreateFrame("Frame",nil,parent)
  hit:EnableMouse(true)
  hit:SetScript("OnEnter",function(self)
    local value=textFor()
    if not value or not A.IsPublic(GameTooltip) or not GameTooltip then return end
    A.tooltipOwner=self; A.tooltipOpen=true
    GameTooltip:SetOwner(self,"ANCHOR_RIGHT")
    if not A.TooltipIsOwned(self) then clearTooltipState(); return end
    GameTooltip:SetText(value,1,1,1,1,true)
    GameTooltip:Show()
  end)
  hit:SetScript("OnLeave",function(self) leaveTooltip(self) end)
  return hit
end
function A.Layout(width, height)
  local panel = A.panel
  local inset, inner = 16, width-32
  local density = math.max(0, math.min(1, (height-424)/326))
  local secondarySize=typography(density)
  panel.borders[1]:SetSize(width, 3)
  panel.borders[2]:SetSize(width, 3)
  panel.borders[3]:SetSize(3, height)
  panel.borders[4]:SetSize(3, height)
  -- Build the top stack from unfitted font targets, so shorter text can grow
  -- back without invalidating clearance. Budget rows between it and the footer.
  local titleTop = 4+14*density
  local specTop = titleTop+(A.title.desiredSize or 21)+4
  place(A.title, inset, -titleTop, inner)
  place(A.spec, inset, -specTop, inner)
  local gap = 10
  local half = (inner-gap)/2
  -- Reserve the maximum heading size even when the current spec is fitted down;
  -- a subsequent shorter name may restore that size without another layout.
  local buttonTop=math.max(51+44*density,specTop+(A.spec.desiredSize or 21)+4)
  place(A.buttons[1], inset, -buttonTop, half)
  place(A.buttons[2], inset+half+gap, -buttonTop, half)
  local headerTop=buttonTop+math.max(A.buttons[1]:GetHeight(),A.buttons[2]:GetHeight())+4
  place(A.headers.current, inset+inner*0.52, -headerTop, inner*0.48)
  place(A.headers.target, inset, -headerTop, inner*0.52)
  local start = headerTop+secondarySize+4
  local footerButtonTop = height-(4+21*density)-A.buttons[3]:GetHeight()
  local footerGap = 4+math.min(4,math.max(0,(height-424)/4))
  local statusTop = footerButtonTop-secondarySize-footerGap
  local trackOffset = 28+9*density
  local minOffset = 47+18*density
  local rowExtent = minOffset+secondarySize
  local step = (statusTop-footerGap-start-rowExtent)/(#A.rows-1)
  local trackHeight = 12+8*density
  for i,row in ipairs(A.rows) do
    local y = -start-(i-1)*step
    place(row.label, inset, y, inner*0.52)
    place(row.current, inset+inner*0.52, y, inner*0.48)
    row.track:ClearAllPoints()
    row.trackX,row.trackY=inset+3,y-trackOffset
    row.track:SetPoint("TOPLEFT", panel, "TOPLEFT", row.trackX,row.trackY)
    row.barWidth = inner-6
    row.trackHeight=trackHeight
    row.track:SetSize(row.barWidth, trackHeight)
    local physical=panel:GetEffectiveScale()*(A.pixelDensity or 1)
    local pixel=1/physical
    row.markerInset=3*pixel
    local markerHeight=trackHeight+8*pixel
    for role,mark in pairs({current=row.markerCurrent,min=row.markerMin,mean=row.markerMean,max=row.markerMax}) do
      local thick=(role=="current" and 5 or role=="mean" and 3 or 2)*pixel
      mark:SetSize(thick,markerHeight)
      row.outline[role]:SetSize(thick+2*pixel,markerHeight+2*pixel)
      row.markerHit[role]:SetSize(8*pixel,markerHeight)
    end
    row.outlineCurrent=row.outline.current
    row.glow:SetSize(math.min(row.barWidth*0.32,100*pixel),trackHeight+20*pixel)
    row.fill:ClearAllPoints()
    row.fill:SetPoint("TOPLEFT", row.track, "TOPLEFT", 0, 0)
    row.fill:SetHeight(trackHeight)
    local column=(inner-12)/3
    place(row.min, inset, y-minOffset, column)
    place(row.target, inset+column+6, y-minOffset, column)
    if row.hasCache then meanLabel(row,row.cachedRating and row.cachedRating.bounds) end
    place(row.max, inset+2*(column+6), y-minOffset, column)
    place(row.axisStatus, inset+7, y-trackOffset-1, inner-14)
    for role,font in pairs({current=row.current,min=row.min,mean=row.target,max=row.max}) do
      local hit=row.hit[role]
      hit:ClearAllPoints()
      local x=inset
      local hitY=y-minOffset
      if role=="current" then x=inset+inner*0.52; hitY=y
      elseif role=="mean" then x=inset+column+6
      elseif role=="max" then x=inset+2*(column+6) end
      hit.columnX,hit.columnY=x,hitY
      hit:SetPoint("TOPLEFT",panel,"TOPLEFT",x,hitY)
      hit:SetSize(font:GetWidth(),role=="current" and (row.current.desiredSize or 20) or secondarySize)
    end
    row.hoverFrame:ClearAllPoints()
    row.hoverFrame:SetPoint("TOPLEFT",panel,"TOPLEFT",inset,y)
    -- Row spacing grows with panel height; it is not the row's hit height.
    -- In particular the final row must never intercept status/footer input.
    row.hoverFrame:SetSize(inner,rowExtent)
    row.hoverFrame:EnableMouse(false)
    if A.visible and row.hasCache then redrawBar(row) end
  end
  place(A.status, inset, -statusTop, inner)
  A.metadataHit:ClearAllPoints()
  A.metadataHit:SetPoint("TOPLEFT",panel,"TOPLEFT",inset,-statusTop)
  A.metadataHit.columnX,A.metadataHit.columnY=inset,-statusTop
  A.metadataHit:SetSize(inner,secondarySize)
  local third = (inner-2*gap)/3
  place(A.buttons[3], inset, -footerButtonTop, third)
  place(A.buttons[4], inset+third+gap, -footerButtonTop, third)
  place(A.buttons[5], inset+2*(third+gap), -footerButtonTop, third)
  for _,widget in ipairs(A.buttons) do widget.caption:SetWidth(widget:GetWidth()-12) end
  fitTypography()
end
local function createPanel()
  if A.panel or not CharacterFrame or not PaperDollFrame then return end
  local panel = CreateFrame("Frame", "StatCompassPanel", CharacterFrame)
  panel:SetSize(468, 750)
  panel:EnableMouse(false)
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
      band = texture(panel, "ARTWORK", 1, 20, 1),
      bandCue = texture(panel, "ARTWORK", 1, 20, 1),
      fill = texture(panel, "ARTWORK", 1, 20, 2),
      glow = texture(panel, "OVERLAY", 100, 40, 0),
      markerCurrent = texture(panel, "OVERLAY", 3, 28, 4),
      markerMin = texture(panel, "OVERLAY", 3, 15, 2),
      markerMean = texture(panel, "OVERLAY", 3, 28, 2),
      markerMax = texture(panel, "OVERLAY", 3, 15, 2),
      hoverFrame = CreateFrame("Frame",nil,panel),
      palette = PALETTE[key], neutralColor = NEUTRAL,
    }
    row.outline={}
    row.bandHit=tooltipHit(panel,function() return row.bandTip end)
    -- The bar-only target stays below the independent marker/value targets.
    row.bandHit:SetFrameLevel(panel:GetFrameLevel())
    row.markerHit={}
    row.hit={}
    for _,role in ipairs({"current","min","mean","max"}) do
      -- Keep current ink above coincident references, without extending its height.
      row.outline[role]=texture(panel,"OVERLAY",5,30,role=="current" and 3 or 1)
      row.markerHit[role]=tooltipHit(panel,function() return row.tip and row.tip[role] end)
      row.hit[role]=tooltipHit(panel,function() return row.tip and row.tip[role] end)
    end
    row.outlineCurrent=row.outline.current
    row.current:SetJustifyH("RIGHT")
    row.max:SetJustifyH("RIGHT")
    row.target:SetJustifyH("CENTER")
    row.axisStatus:SetJustifyH("CENTER")
    row.current:SetTextColor(1,1,1,1)
    row.min:SetTextColor(0.77,0.81,0.84,1)
    row.max:SetTextColor(0.77,0.81,0.84,1)
    row.hoverFrame:EnableMouse(false)
    A.rows[i] = row
  end
  A.status = label(panel, 16, -642, 436, T("noData"))
  A.metadataHit=tooltipHit(panel,function() return A.metadataText end)
  A.buttons[3] = button(panel, 16, -691, 138, T("default"), function() A.SetSkin("default") end)
  A.buttons[4] = button(panel, 165, -691, 138, T("flat"), function() A.SetSkin("flat") end)
  A.buttons[5] = button(panel, 314, -691, 138, T("reset"), function() A.ResetSettings() end)
  A.Layout(468,750)
  panel:HookScript("OnHide", function()
    local owner=A.tooltipOwner
    if A.TooltipIsOwned(owner) then GameTooltip:Hide() end
    clearTooltipState()
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
    hostFont,searchedHost=nil,nil
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
