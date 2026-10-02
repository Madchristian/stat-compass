local A = StatCompass
local floor, huge = math.floor, math.huge
local function public(value)
  if type(issecretvalue) == "function" and issecretvalue(value) then return false end
  return true
end
A.IsPublic = public
local function safeFunction(container, key)
  if not public(container) or type(container) ~= "table" then return nil end
  local fn = container[key]
  if not public(fn) or type(fn) ~= "function" then return nil end
  return fn
end
local function call(fn, ...)
  if not public(fn) or type(fn) ~= "function" then return nil end
  local ok, value = pcall(fn, ...)
  if not public(ok) or ok ~= true or not public(value) then return nil end
  return value
end
local function finite(value)
  return public(value) and type(value) == "number" and value == value and value ~= huge and value ~= -huge
end
local function same(value, expected)
  return public(value) and value == expected
end
local function integer(value, min, max)
  return finite(value) and value == floor(value) and value >= min and value <= max
end
local function literal(value, allowed)
  return public(value) and type(value) == "string" and allowed[value] == true
end
local MODES = {raid=true, mythic=true}
local SKINS = {default=true, flat=true}
function A.SanitizeSettings(raw)
  local result = {mode="raid", skin="default", minimapShown=true, minimapAngle=225}
  if not public(raw) or type(raw) ~= "table" then return result end
  if literal(raw.mode, MODES) then result.mode = raw.mode end
  if literal(raw.skin, SKINS) then result.skin = raw.skin end
  if public(raw.minimapShown) and type(raw.minimapShown) == "boolean" then result.minimapShown = raw.minimapShown end
  if finite(raw.minimapAngle) then result.minimapAngle = raw.minimapAngle % 360 end
  return result
end
function A.SaveSettings(raw)
  A.settings = A.SanitizeSettings(raw)
  StatCompassDB = A.SanitizeSettings(A.settings)
  if A.RefreshControls then A.RefreshControls() end
end
function A.SetMinimapShown(shown)
  if not public(shown) or type(shown) ~= "boolean" then return end
  local settings = A.SanitizeSettings(A.settings)
  settings.minimapShown = shown
  A.SaveSettings(settings)
end
function A.SetMinimapAngle(angle)
  if not finite(angle) then return end
  local settings = A.SanitizeSettings(A.settings)
  settings.minimapAngle = angle % 360
  A.SaveSettings(settings)
end
function A.ResetPresentation()
  A.SaveSettings({mode=A.settings.mode})
  if A.visible and A.ApplySkin then A.ApplySkin() end
end
function A.ResetSettings()
  A.SaveSettings(nil)
  if A.visible then
    if A.ApplySkin then A.ApplySkin() end
    A.QueueRefresh()
  end
end
local STATS = {"crit", "haste", "mastery", "versatility"}
local RATINGS = {crit="critRating", haste="hasteRating", mastery="masteryRating", versatility="versatilityRating"}
local MIN_COHORT, MAX_COHORT = 20, 50
A.statOrder = STATS
-- Percent points, never rating. Mastery is displayed effect, not rating or base GetMastery().
local getters = {haste="GetHaste", mastery="GetMasteryEffect"}
local function crit()
  local highest = call(GetCritChance)
  local ranged = call(GetRangedCritChance)
  if not finite(highest) or not finite(ranged) then return nil end
  if ranged > highest then highest = ranged end
  local lowestSpell
  for school=2,7 do
    local value = call(GetSpellCritChance, school)
    if not finite(value) then return nil end
    if not lowestSpell or value < lowestSpell then lowestSpell = value end
  end
  if finite(lowestSpell) and (not finite(highest) or lowestSpell > highest) then highest = lowestSpell end
  return highest
end
local function versatility()
  local rating = call(GetCombatRatingBonus, 29)
  local bonus = call(GetVersatilityBonus, 29)
  if not finite(rating) or not finite(bonus) then return nil end
  return rating + bonus
end
function A.ReadStats()
  local values = {}
  for i=1,#STATS do
    local key = STATS[i]
    local value
    if key == "crit" then value = crit()
    elseif key == "versatility" then value = versatility()
    else value = call(_G[getters[key]]) end
    if finite(value) then values[key] = value end
  end
  return values
end
function A.ReadSpecInfo()
  local getter = safeFunction(C_SpecializationInfo, "GetSpecialization")
  local info = safeFunction(C_SpecializationInfo, "GetSpecializationInfo")
  local index = call(getter)
  if not integer(index, 1, 10) or not info then return nil end
  local ok, id, name = pcall(info, index)
  if not public(ok) or ok ~= true or not integer(id, 1, 1000000) then return nil end
  if not public(name) or type(name) ~= "string" or name == "" then name = nil end
  return id, name
end
function A.ReadSpec()
  local id = A.ReadSpecInfo()
  return id
end
local function plainText(value)
  return public(value) and type(value) == "string" and value ~= ""
end
local function validateCohort(cohort, specID, mode, interface, clientBuild, level, collectedAt, now)
  if not public(cohort) or type(cohort) ~= "table" then return false end
  if not same(cohort.region,"EU") or not same(cohort.mode,mode) or not same(cohort.specID,specID) or not same(cohort.interface,interface) or not same(cohort.clientBuild,clientBuild) or not same(cohort.level,level) or not same(cohort.unit,"percentPoints") or not same(cohort.semanticKind,"masteryEffectPercent") then return false end
  for _,key in ipairs({"season","rankingMetric","difficulty","partition"}) do
    if not plainText(cohort[key]) then return false end
  end
  if not integer(cohort.observedAt, 1000000000, 9999999999) or cohort.observedAt > collectedAt or cohort.observedAt > now then return false end
  if not public(cohort.observations) or type(cohort.observations) ~= "table" then return false end
  local count = #cohort.observations
  if not integer(count, MIN_COHORT, MAX_COHORT) or not same(cohort.selectedCount,count) or not same(cohort.validCount,count) then return false end
  local seen = {}
  local latestRow = 0
  for i=1,count do
    local row = cohort.observations[i]
    if not public(row) or type(row) ~= "table" or not same(row.rank,i) or not public(row.id) or type(row.id) ~= "string" or row.id == "" or seen[row.id] then return false end
    if not same(row.region,"EU") or not same(row.mode,mode) or not same(row.specID,specID) or not same(row.interface,interface) or not same(row.clientBuild,clientBuild) or not same(row.level,level) or not same(row.unit,"percentPoints") or not same(row.semanticKind,"masteryEffectPercent") then return false end
    if not integer(row.observedAt, 1000000000, 9999999999) or row.observedAt > collectedAt or row.observedAt > now then return false end
    if row.observedAt < collectedAt - 30*86400 or row.observedAt < cohort.observedAt - 86400 or row.observedAt > cohort.observedAt then return false end
    if row.observedAt > latestRow then latestRow = row.observedAt end
    seen[row.id] = true
    for j=1,#STATS do
      local v = row[STATS[j]]
      if not finite(v) or v < 0 or (STATS[j] == "crit" and v > 100) then return false end
      local r = row[RATINGS[STATS[j]]]
      if not finite(r) or r < 0 then return false end
    end
  end
  return latestRow == cohort.observedAt
end
function A.ValidateDataset(data, interface, clientBuild, level, now)
  if not public(data) or type(data) ~= "table" then return false end
  if not same(data.schema,3) or not integer(data.interface, 1, 999999) or not integer(data.clientBuild,1,9999999) or not integer(data.level, 1, 1000) then return false end
  if interface and not same(data.interface,interface) then return false end
  if clientBuild and not same(data.clientBuild,clientBuild) then return false end
  if level and not same(data.level,level) then return false end
  if not integer(now, 1000000000, 9999999999) then return false end
  if not integer(data.collectedAt,1000000000,9999999999) or not integer(data.observedAt,1000000000,9999999999) or not integer(data.expiresAt,1000000000,9999999999) then return false end
  if data.observedAt > data.collectedAt or data.collectedAt > now or data.expiresAt <= now or data.expiresAt <= data.collectedAt or data.expiresAt > data.collectedAt + 30*86400 then return false end
  for _,key in ipairs({"sourceURL", "rawSHA256", "permission"}) do
    if not plainText(data[key]) then return false end
  end
  if not string.match(data.sourceURL, "^https://") then return false end
  if string.len(data.rawSHA256) ~= 64 or string.match(data.rawSHA256, "[^0-9a-f]") then return false end
  if not public(data.cohorts) or type(data.cohorts) ~= "table" then return false end
  local latestCohort = 0
  for specID,modes in pairs(data.cohorts) do
    if not integer(specID, 1, 1000000) or not public(modes) or type(modes) ~= "table" then return false end
    for mode,cohort in pairs(modes) do
      if not public(mode) or not MODES[mode] or not validateCohort(cohort, specID, mode, data.interface, data.clientBuild, data.level, data.collectedAt, now) then return false end
      if cohort.observedAt > latestCohort then latestCohort = cohort.observedAt end
    end
  end
  return latestCohort == data.observedAt
end
function A.GetTarget(specID, mode)
  if not integer(specID,1,1000000) or not literal(mode,MODES) then return nil end
  local data = A.releaseData
  -- GetBuildInfo returns numeric client build as a string in result 2 and interface in result 4.
  local fn = GetBuildInfo
  if not public(fn) or type(fn) ~= "function" then return nil end
  local ok, _, buildText, _, interface = pcall(fn)
  if not public(ok) or ok ~= true or not integer(interface, 100000, 999999) then return nil end
  if not public(buildText) or type(buildText) ~= "string" or not string.match(buildText,"^%d+$") then return nil end
  local clientBuild = tonumber(buildText)
  if not integer(clientBuild,1,9999999) then return nil end
  local level = call(UnitLevel, "player")
  local now = call(GetServerTime)
  if not integer(level, 1, 1000) or not A.ValidateDataset(data, interface, clientBuild, level, now) then return nil end
  local modes = data.cohorts[specID]
  if not modes then return nil end
  local cohort = modes[mode]
  if not cohort then return nil end
  local count = #cohort.observations
  local result = {band={}, range={}, rating={}}
  local function summary(field)
    local sum, values = 0, {}
    for i=1,count do
      local value = cohort.observations[i][field]
      sum = sum + (value - sum) / i
      values[i] = value
    end
    table.sort(values)
    if not finite(sum) then return nil end
    return sum, values
  end
  for j=1,#STATS do
    local key = STATS[j]
    local mean, values = summary(key)
    if not mean then return nil end
    result[key] = mean
    -- nearest-rank quartiles; for 50 rows these are ranks 13 and 38 as before
    result.band[key] = {low=values[math.ceil(count*0.25)], high=values[math.ceil(count*0.75)]}
    result.range[key] = {min=values[1], max=values[count]}
    local ratingMean, ratings = summary(RATINGS[key])
    if not ratingMean then return nil end
    result.rating[key] = {mean=ratingMean, min=ratings[1], max=ratings[count]}
  end
  result.sample = count
  result.selectedCount = cohort.selectedCount
  result.validCount = cohort.validCount
  result.collectedAt = data.collectedAt
  result.observedAt = cohort.observedAt
  result.expiresAt = data.expiresAt
  result.interface = data.interface
  result.clientBuild = data.clientBuild
  result.semanticKind = cohort.semanticKind
  result.season = cohort.season
  result.rankingMetric = cohort.rankingMetric
  result.difficulty = cohort.difficulty
  result.partition = cohort.partition
  result.sourceURL = data.sourceURL
  result.rawSHA256 = data.rawSHA256
  result.permission = data.permission
  return result
end
function A.Snapshot()
  local specID, specName = A.ReadSpecInfo()
  return {specID=specID, specName=specName, current=A.ReadStats(), target=A.GetTarget(specID, A.settings.mode)}
end
function A.Flush()
  A.pending = false
  if not A.visible then return end
  if A.panel then
    if not A.panel.IsVisible then return end
    local visible = A.panel:IsVisible()
    if not public(visible) or visible ~= true then return end
  end
  local snapshot = A.Snapshot()
  if A.Render then A.Render(snapshot) end
  local expiry = snapshot.target and snapshot.target.expiresAt
  local data, mode, specID = A.releaseData, A.settings.mode, snapshot.specID
  if expiry ~= A.expiryAt or data ~= A.expiryData or mode ~= A.expiryMode or specID ~= A.expirySpec then
    A.expiryToken = (A.expiryToken or 0) + 1
    A.expiryAt = expiry
    A.expiryData, A.expiryMode, A.expirySpec = data, mode, specID
    A.expiryScheduled = nil
  end
  if expiry and A.expiryScheduled ~= expiry then
    local now = call(GetServerTime)
    local timer = safeFunction(C_Timer, "After")
    if integer(now, 1000000000, 9999999999) and timer then
      local delay = expiry - now
      if delay < 0 then delay = 0 end
      local generation = A.generation
      local token = A.expiryToken
      A.expiryScheduled = expiry
      timer(delay, function()
        if A.visible and A.generation == generation and A.expiryToken == token and A.releaseData == data and A.settings.mode == mode then
          A.expiryScheduled = nil
          A.Flush()
        end
      end)
    end
  elseif not expiry then
    A.expiryScheduled = nil
  end
end
function A.QueueRefresh()
  if not A.visible or A.pending then return end
  local timer = safeFunction(C_Timer, "After")
  if not timer then A.Flush(); return end
  A.pending = true
  local generation = A.generation or 0
  timer(0, function()
    if A.generation == generation then A.Flush() end
  end)
end
function A.SetVisible(visible)
  if not public(visible) or type(visible) ~= "boolean" then return end
  if visible == A.visible then return end
  A.visible = visible
  A.generation = (A.generation or 0) + 1
  A.expiryToken = (A.expiryToken or 0) + 1
  A.expiryAt = nil
  A.expiryData, A.expiryMode, A.expirySpec = nil, nil, nil
  A.expiryScheduled = nil
  if visible then
    A.pending = false
    if A.ApplySkin then A.ApplySkin() end
    A.Flush() -- immediate current data exactly once
  end
end
function A.SetMode(mode)
  if not literal(mode, MODES) then return end
  if A.settings.mode == mode then return end
  local settings = A.SanitizeSettings(A.settings)
  settings.mode = mode
  A.SaveSettings(settings)
  if A.visible and A.ApplySkin then A.ApplySkin() end
  A.QueueRefresh()
end
function A.SetSkin(skin)
  if not literal(skin, SKINS) then return end
  if A.settings.skin == skin then return end
  local settings = A.SanitizeSettings(A.settings)
  settings.skin = skin
  A.SaveSettings(settings)
  if A.visible and A.ApplySkin then A.ApplySkin() end
end
-- Defaults are usable during TOC loading; persistence starts at ADDON_LOADED.
A.settings = A.SanitizeSettings(StatCompassDB)
