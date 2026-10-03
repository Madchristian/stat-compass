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
-- Mythic+ only: Blizzard publishes no per-player raid ranking (the Hall of Fame stops before Midnight).
local MODES = {mythic=true}
local SKINS = {default=true, flat=true}
function A.SanitizeSettings(raw)
  local result = {mode="mythic", skin="default", minimapShown=true, minimapAngle=225, collapsed=false}
  if not public(raw) or type(raw) ~= "table" then return result end

  if public(raw.collapsed) and type(raw.collapsed) == "boolean" then result.collapsed = raw.collapsed end
  if literal(raw.skin, SKINS) then result.skin = raw.skin end
  if public(raw.minimapShown) and type(raw.minimapShown) == "boolean" then result.minimapShown = raw.minimapShown end
  if finite(raw.minimapAngle) then result.minimapAngle = raw.minimapAngle % 360 end
  return result
end
function A.SaveSettings(raw)
  A.settings = A.SanitizeSettings(raw)
  StatCompassDB = A.SanitizeSettings(A.settings)
  if A.RefreshControls then A.RefreshControls() end
  if A.SyncVisibility then A.SyncVisibility() end
end
function A.SetCollapsed(collapsed)
  if not public(collapsed) or type(collapsed) ~= "boolean" then return end
  local settings = A.SanitizeSettings(A.settings)
  settings.collapsed = collapsed
  A.SaveSettings(settings)
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
  A.SaveSettings({collapsed=A.SanitizeSettings(A.settings).collapsed})
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
-- Target band: the cohort median, bracketed by its 40th and 60th percentiles.
local TARGET_LOW, TARGET_MID, TARGET_HIGH = 0.4, 0.5, 0.6
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
  if cohort.heroMix ~= nil then
    if not public(cohort.heroMix) or type(cohort.heroMix) ~= "table" then return false end
    local total = 0
    for name,n in pairs(cohort.heroMix) do
      if not plainText(name) or not integer(n, 1, count) then return false end
      total = total + n
    end
    if total > count then return false end
  end
  return latestRow == cohort.observedAt
end
local combat = false
local function inCombat()
  if combat then return true end
  -- Missing API is tolerated by offline tools; unreadable live state fails closed.
  if public(InCombatLockdown) and type(InCombatLockdown) == "nil" then return false end
  return call(InCombatLockdown) ~= false
end
function A.ValidateDataset(data, interface, clientBuild, level, now)
  if inCombat() then return false end
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
  -- optional hero talent cohorts: heroCohorts[specID][heroTreeID][mode]
  if data.heroCohorts ~= nil then
    if not public(data.heroCohorts) or type(data.heroCohorts) ~= "table" then return false end
    for specID,heroes in pairs(data.heroCohorts) do
      if not integer(specID, 1, 1000000) or not public(heroes) or type(heroes) ~= "table" then return false end
      for heroID,modes in pairs(heroes) do
        if not integer(heroID, 1, 1000000) or not public(modes) or type(modes) ~= "table" then return false end
        for mode,cohort in pairs(modes) do
          if not public(mode) or not MODES[mode] or not validateCohort(cohort, specID, mode, data.interface, data.clientBuild, data.level, data.collectedAt, now) then return false end
          if not same(cohort.heroTreeID, heroID) or not plainText(cohort.heroTreeName) then return false end
          if cohort.observedAt > latestCohort then latestCohort = cohort.observedAt end
        end
      end
    end
  end
  return latestCohort == data.observedAt
end
local function readHeroContext()
  if public(C_ClassTalents) and type(C_ClassTalents) == "nil" then return nil, true end
  local fn = safeFunction(C_ClassTalents, "GetActiveHeroTalentSpec")
  if not fn then return nil, false end
  local ok, id = pcall(fn)
  if not public(ok) or ok ~= true or not public(id) then return nil, false end
  if integer(id, 1, 1000000) then return id, true end
  return nil, id == nil
end
function A.ReadHeroTree()
  local id = readHeroContext()
  return id
end
local targetCache
-- Lua 5.1 tables are mutable. Keep an exact identity/value ledger, not a hash or
-- identity-only validation memo. Audit it only out of combat before reusing work.
local function datasetLedger(data)
  local ledger, seen = {}, {}
  local function visit(t)
    if seen[t] then return true end
    if not public(t) or getmetatable(t) ~= nil then return false end
    seen[t] = true
    local entry = {source=t, values={}, count=0}
    ledger[#ledger+1] = entry
    for k,v in pairs(t) do
      if not public(k) or not public(v) then return false end
      entry.values[k], entry.count = v, entry.count + 1
      if type(v) == "table" and not visit(v) then return false end
    end
    return true
  end
  if visit(data) then return ledger end
end
local function unchanged(ledger)
  if not ledger then return false end
  for i=1,#ledger do
    local entry, count = ledger[i], 0
    if not public(entry.source) or getmetatable(entry.source) ~= nil then return false end
    for k,v in pairs(entry.source) do
      if not public(k) or not public(v) or not rawequal(v, entry.values[k]) then return false end
      count = count + 1
    end
    if count ~= entry.count then return false end
  end
  return true
end
local function copy(value)
  if type(value) ~= "table" then return value end
  local result = {}
  for k,v in pairs(value) do result[k] = copy(v) end
  return result
end
local HEADER = {"schema", "interface", "clientBuild", "level", "collectedAt", "observedAt", "expiresAt",
  "sourceURL", "rawSHA256", "permission", "cohorts", "heroCohorts"}
local function tableField(t, key)
  if not public(t) or type(t) ~= "table" then return nil end
  return rawget(t, key)
end
local function selectedCohort(data, specID, mode, heroID)
  local cohort
  if integer(heroID,1,1000000) then
    local heroes = tableField(tableField(data,"heroCohorts"),specID)
    cohort = tableField(tableField(heroes,heroID),mode)
  end
  if not public(cohort) then return nil end
  if cohort == nil then cohort = tableField(tableField(tableField(data,"cohorts"),specID),mode) end
  return cohort
end
local function cacheMatches(data, specID, mode, heroID, interface, clientBuild, level, now)
  local c = targetCache
  if not c or not c.ledger or not public(data) or data ~= c.data or specID ~= c.specID or mode ~= c.mode
      or heroID ~= c.heroID or interface ~= c.interface or clientBuild ~= c.clientBuild
      or level ~= c.level or not integer(now,1000000000,9999999999)
      or now < c.collectedAt or now >= c.expiresAt then return false end
  for _,key in ipairs(HEADER) do
    if not same(rawget(data,key), c.header[key]) then return false end
  end
  if not same(selectedCohort(data,specID,mode,heroID),c.cohort) then return false end
  return true
end
-- Shared bounded context reads for both target paths. No dataset traversal here.
local function readTargetContext(specID, mode, heroID)
  if not integer(specID,1,1000000) or not literal(mode,MODES) or not public(heroID) then
    targetCache = nil; return nil
  end
  local function unavailable() targetCache = nil; return nil end
  local data = A.releaseData
  -- GetBuildInfo returns numeric client build as a string in result 2 and interface in result 4.
  local fn = GetBuildInfo
  if not public(fn) or type(fn) ~= "function" then return unavailable() end
  local ok, _, buildText, _, interface = pcall(fn)
  if not public(ok) or ok ~= true or not integer(interface, 100000, 999999) then return unavailable() end
  if not public(buildText) or type(buildText) ~= "string" or not string.match(buildText,"^%d+$") then return unavailable() end
  local clientBuild = tonumber(buildText)
  if not integer(clientBuild,1,9999999) then return unavailable() end
  local level = call(UnitLevel, "player")
  local now = call(GetServerTime)
  return true, data, interface, clientBuild, level, now
end
-- Combat dispatch uses this cache-only path, never the public aggregation entry.
local function cachedTarget(specID, mode, heroID)
  local ok, data, interface, clientBuild, level, now = readTargetContext(specID, mode, heroID)
  if ok and cacheMatches(data, specID, mode, heroID, interface, clientBuild, level, now) then
    return copy(targetCache.target)
  end
  targetCache = nil
  return nil
end
function A.GetTarget(specID, mode, heroID)
  if inCombat() then return cachedTarget(specID, mode, heroID) end
  local ok, data, interface, clientBuild, level, now = readTargetContext(specID, mode, heroID)
  if not ok then return nil end
  if cacheMatches(data, specID, mode, heroID, interface, clientBuild, level, now)
      and unchanged(targetCache.ledger) then return copy(targetCache.target) end
  targetCache = nil
  if not integer(level, 1, 1000) or not A.ValidateDataset(data, interface, clientBuild, level, now) then return nil end
  -- a cohort of the player's own hero talent tree wins; otherwise the whole specialization
  local heroes = integer(heroID, 1, 1000000) and data.heroCohorts and data.heroCohorts[specID]
  local cohort = heroes and heroes[heroID] and heroes[heroID][mode]
  if not cohort then
    local modes = data.cohorts[specID]
    cohort = modes and modes[mode]
  end
  if not cohort then return nil end
  local count = #cohort.observations
  local result = {band={}, range={}, rating={}}
  local function summary(field, read)
    local sum, values = 0, {}
    for i=1,count do
      local value = read and read(cohort.observations[i]) or cohort.observations[i][field]
      sum = sum + (value - sum) / i
      values[i] = value
    end
    table.sort(values)
    if not finite(sum) then return nil end
    return sum, values
  end
  -- Budget share: a stat's rating as percent of the row's four secondary ratings. Gear level moves
  -- the budget, not the split, so shares show the direction a player builds in.
  local budgets = {}
  for i=1,count do
    local row, total = cohort.observations[i], 0
    for j=1,#STATS do total = total + row[RATINGS[STATS[j]]] end
    budgets[row] = total
    if not (total > 0) then budgets = nil; break end
  end
  if budgets then result.share = {} end
  -- nearest-rank percentile of an ascending list
  local function at(values, p) return values[math.max(1, math.ceil(count * p))] end
  result.pct = {}
  for j=1,#STATS do
    local key = STATS[j]
    local mean, values = summary(key)
    if not mean then return nil end
    result[key] = mean
    -- nearest-rank quartiles; for 50 rows these are ranks 13 and 38 as before
    result.band[key] = {low=values[math.ceil(count*0.25)], high=values[math.ceil(count*0.75)]}
    result.range[key] = {min=values[1], max=values[count]}
    result.pct[key] = {median=at(values, TARGET_MID), low=at(values, TARGET_LOW), high=at(values, TARGET_HIGH)}
    local ratingMean, ratings = summary(RATINGS[key])
    if not ratingMean then return nil end
    result.rating[key] = {mean=ratingMean, min=ratings[1], max=ratings[count],
      median=at(ratings, TARGET_MID), p40=at(ratings, TARGET_LOW), p60=at(ratings, TARGET_HIGH),
      low=ratings[math.ceil(count*0.25)], high=ratings[math.ceil(count*0.75)]}
    if budgets then
      local field = RATINGS[key]
      local shareMean, shares = summary(nil, function(row) return row[field] / budgets[row] * 100 end)
      if not shareMean then return nil end
      result.share[key] = {mean=shareMean, median=at(shares, TARGET_MID), min=shares[1], max=shares[count],
        low=shares[math.ceil(count*0.25)], high=shares[math.ceil(count*0.75)]}
    end
  end
  -- Stat priority: where the cohort puts most of its secondary budget (median share), highest first.
  -- This is what top players invest in, not a simulated value; ties keep the Character-window order.
  if result.share then
    local order = {}
    for j=1,#STATS do order[j] = STATS[j] end
    local rank = {}
    for j=1,#STATS do rank[STATS[j]] = j end
    table.sort(order, function(a, b)
      local x, y = result.share[a].median, result.share[b].median
      if x ~= y then return x > y end
      return rank[a] < rank[b]
    end)
    result.priority = order
  end
  result.sample = count
  result.heroTreeID = cohort.heroTreeID
  result.heroTreeName = cohort.heroTreeName
  result.heroMix = cohort.heroMix
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
  local header = {}
  for _,key in ipairs(HEADER) do header[key] = data[key] end
  targetCache = {data=data, cohort=cohort, ledger=datasetLedger(data), header=header, specID=specID, mode=mode, heroID=heroID,
    interface=interface, clientBuild=clientBuild, level=level,
    collectedAt=data.collectedAt, expiresAt=data.expiresAt, target=copy(result)}
  return result
end
-- Combat rating IDs as the Character window uses them: crit is the best of melee/ranged/spell,
-- haste likewise; mastery 26 (checked in game) and versatility (damage done) 29.
local RATING_IDS = {crit={9,10,11}, haste={18,19,20}, mastery={26}, versatility={29}}
function A.ReadRatings()
  local fn = GetCombatRating
  local ratings = {}
  for j=1,#STATS do
    local key = STATS[j]
    local best
    for _,id in ipairs(RATING_IDS[key]) do
      local value = call(fn, id)
      if finite(value) and value >= 0 and (not best or value > best) then best = value end
    end
    ratings[key] = best
  end
  return ratings
end
-- The bar axis is a display scale, not a game cap: the larger of the cohort's top rating and the
-- player's own, plus 10%, rounded up to 50. Its provenance says exactly that.
local AXIS_HEADROOM, AXIS_STEP = 1.1, 50
function A.RatingComparison(target, ratings)
  local result = {}
  for j=1,#STATS do
    local key = STATS[j]
    local current = ratings and finite(ratings[key]) and ratings[key] or nil
    local ref = target and target.rating and target.rating[key]
    if ref then
      local top = ref.max
      if current and current > top then top = current end
      local axis = math.max(AXIS_STEP, math.ceil(top * AXIS_HEADROOM / AXIS_STEP) * AXIS_STEP)
      result[key] = {currentRating=current, axisMaxRating=axis, axisVerified=true,
        axisProvenance="scale: max(EU top " .. target.sample .. " maximum, own rating) + 10%",
        -- lowRating/highRating: nearest-rank quartiles, where the middle half of the cohort sits
        reference={minRating=ref.min, meanRating=ref.mean, maxRating=ref.max, lowRating=ref.low, highRating=ref.high},
        sampleCount=target.sample, sourceStatus="verified"}
    else
      result[key] = {currentRating=current, sourceStatus="unavailable"}
    end
  end
  return result
end
-- The same comparison as budget shares (percent of the four secondary ratings), which does not
-- depend on item level. The axis follows the rating rule but in 5-point steps, capped at 100.
function A.ShareComparison(target, ratings)
  local total, own = 0, {}
  for j=1,#STATS do
    local value = ratings and ratings[STATS[j]]
    if not finite(value) then total = nil; break end
    total = total + value
  end
  if total and total > 0 then
    for j=1,#STATS do own[STATS[j]] = ratings[STATS[j]] / total * 100 end
  end
  local result = {}
  for j=1,#STATS do
    local key = STATS[j]
    local current = own[key]
    local ref = target and target.share and target.share[key]
    if ref then
      local top = ref.max
      if current and current > top then top = current end
      local axis = math.min(100, math.max(5, math.ceil(top * AXIS_HEADROOM / 5) * 5))
      result[key] = {currentShare=current, axisMaxShare=axis, axisVerified=true,
        axisProvenance="scale: max(EU top " .. target.sample .. " maximum share, own share) + 10%",
        reference={minShare=ref.min, meanShare=ref.mean, maxShare=ref.max, lowShare=ref.low, highShare=ref.high},
        sampleCount=target.sample, sourceStatus="verified"}
    else
      result[key] = {currentShare=current, sourceStatus="unavailable"}
    end
  end
  return result
end
-- Rating targets compare rating with rating: GetCombatRating in game and Blizzard's
-- rating_normalized are both pure gear rating, free of buffs, talents and racials. Converting the
-- cohort's percentages with the player's own in-game conversion was dropped: the player's live
-- percentages include buffs (Mark of the Wild alone is +3% versatility) that the logged-out API
-- profiles never have, which pushed targets far too low (Guardian versatility came out at 8).
function A.RatingTargets(target, ratings)
  local result, total, budget = {}, 0, 0
  for j=1,#STATS do
    local key = STATS[j]
    local own = ratings and finite(ratings[key]) and ratings[key] or nil
    if own and budget then budget = budget + own else budget = nil end
    local rating, pct = target and target.rating and target.rating[key], target and target.pct and target.pct[key]
    local entry = {currentRating=own}
    if rating and rating.median then
      entry.targetRating, entry.lowRating, entry.highRating = rating.median, rating.p40, rating.p60
      entry.targetPercent = pct and pct.median  -- the cohort's median percentage, for the tooltip only
      entry.sampleCount, entry.sourceStatus = target.sample, "verified"
      if total then total = total + entry.targetRating end
    else
      entry.sourceStatus, total = "unavailable", nil
    end
    result[key] = entry
  end
  -- the four targets together may exceed the player's budget at a lower item level; say so
  result.totals = {targetRating=total, ownRating=budget}
  return result
end
local lastSnapshot, lastRatings
local readableSnapshot, readableRatings, readableCache
local function readContext()
  local specID, specName = A.ReadSpecInfo()
  local heroID, readable = readHeroContext()
  local target
  if readable == false then targetCache = nil
  elseif inCombat() then target = cachedTarget(specID, A.settings.mode, heroID)
  else target = A.GetTarget(specID, A.settings.mode, heroID) end
  return specID, specName, heroID, target
end
local function withoutTarget(snapshot, ratings)
  local result = copy(snapshot)
  result.target = nil
  result.ratingComparison = A.RatingComparison(nil, ratings)
  result.shareComparison = A.ShareComparison(nil, ratings)
  result.ratingTarget = A.RatingTargets(nil, ratings)
  return result
end
function A.Snapshot()
  if inCombat() then
    -- Only bounded safety checks are allowed; never sample current stats here.
    local _, _, _, target = readContext()
    if not readableSnapshot then
      local unknown = withoutTarget({current={}}, nil)
      unknown.preCombat = false
      return unknown
    end
    if not target or targetCache ~= readableCache then
      readableSnapshot = withoutTarget(readableSnapshot, readableRatings)
    end
    local frozen = copy(readableSnapshot)
    frozen.preCombat = true
    return frozen
  end
  local specID, specName, heroID, target = readContext()
  local ratings, current = A.ReadRatings(), A.ReadStats()
  lastRatings = ratings
  lastSnapshot = {specID=specID, specName=specName, heroTreeID=heroID, current=current, target=target,
    preCombat=false,
    ratingComparison=A.RatingComparison(target, ratings), shareComparison=A.ShareComparison(target, ratings),
    ratingTarget=A.RatingTargets(target, ratings)}
  for _,key in ipairs(STATS) do
    if finite(current[key]) or finite(ratings[key]) then
      readableSnapshot, readableRatings = copy(lastSnapshot), copy(ratings)
      readableCache = targetCache
      break
    end
  end
  return copy(lastSnapshot)
end
local scheduleExpiry
local function panelVisible()
  if not A.visible or A.settings.collapsed then return false end
  if A.panel then
    local visible = call(A.panel.IsVisible, A.panel)
    if visible ~= true then return false end
  end
  return true
end
function A.InvalidateTarget()
  targetCache = nil
  if readableSnapshot then readableSnapshot = withoutTarget(readableSnapshot, readableRatings) end
  if not lastSnapshot or not lastSnapshot.target then return end
  -- Discard references even while hidden; retain only the safe historical values.
  lastSnapshot = withoutTarget(lastSnapshot, lastRatings)
  if panelVisible() and A.Render then
    local snapshot = inCombat() and A.Snapshot() or copy(lastSnapshot)
    A.Render(snapshot)
  end
end
function A.SetCombat(active)
  if not public(active) or type(active) ~= "boolean" or active == combat then return end
  combat = active
  A.generation = (A.generation or 0) + 1
  A.expiryToken = (A.expiryToken or 0) + 1
  A.expiryScheduled = nil
  A.pending = false
  A.Flush() -- frozen render on entry; one fresh visible sample on exit
end
function A.Flush()
  A.pending = false
  if not panelVisible() then return end
  local snapshot = A.Snapshot()
  if A.Render then A.Render(snapshot) end
  scheduleExpiry(snapshot)
end
scheduleExpiry = function(snapshot)
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
        -- The token binds this callback to the displayed dataset/context. A silent
        -- replacement must not prevent removal of its now-expired references.
        if panelVisible() and A.generation == generation and A.expiryToken == token then
          A.expiryScheduled = nil
          if inCombat() then A.InvalidateTarget() else A.Flush() end
        end
      end)
    end
  elseif not expiry then
    A.expiryScheduled = nil
  end
end
local CONTEXT_EVENTS = {PLAYER_SPECIALIZATION_CHANGED=true, ACTIVE_TALENT_GROUP_CHANGED=true,
  PLAYER_TALENT_UPDATE=true, TRAIT_CONFIG_UPDATED=true, UNIT_LEVEL=true, PLAYER_ENTERING_WORLD=true}
function A.QueueRefresh(reason)
  if public(reason) and type(reason) == "string" and CONTEXT_EVENTS[reason] then
    if inCombat() then A.InvalidateTarget() else targetCache = nil end
  end
  if not panelVisible() then return end
  if inCombat() then A.pending = true; return end
  if A.pending then return end
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
  A.pending = false
  A.generation = (A.generation or 0) + 1
  A.expiryToken = (A.expiryToken or 0) + 1
  A.expiryAt = nil
  A.expiryData, A.expiryMode, A.expirySpec = nil, nil, nil
  A.expiryScheduled = nil
  if visible then
    A.pending = false
    if A.ApplySkin then A.ApplySkin() end
    A.Flush() -- one fresh out-of-combat sample, or the frozen combat display
  end
end
function A.SetMode(mode)
  if not public(mode) or mode ~= "mythic" then return end
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
