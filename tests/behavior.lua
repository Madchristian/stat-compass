-- Native Lua smoke suite. The Python/Lupa suite is authoritative when available.
local root = arg[1] or "StatCompass/"
local function loadfile_at(name)
  local chunk, err = loadfile(root .. name)
  assert(chunk, err)
  chunk()
end
loadfile_at("Locales.lua")
loadfile_at("Data.lua")
loadfile_at("Core.lua")
assert(StatCompass and StatCompass.ValidateDataset, "core must load")
assert(StatCompass.ValidateDataset({}) == false)
print("behavior: green")
