# Combined controls integration test report

## Main-tree integration evidence (current)

Integrated into `C:/Users/Christian/orca/stat-compass` without live-addon, WTF, release automation, commit, push, or GitHub writes. The original main suite returned **93 passed in 0.45s** (one pytest cache-permission warning); subsequent runs disabled that cache. Applying the eight candidate control tests alone first returned **8 failed in 0.31s**, including missing category/launcher, discarded minimap settings, premature SavedVariables replacement, and stale documentation. Applying the remaining narrow candidate patch hunks returned **101 passed in 0.62s**.

Five additional combined-candidate verification cases exercise lazy Character loading, authoritative SavedVariables after TOC execution, own ADDON_LOADED and login fallback initialization, and minimap opening into the preserved 768-high virtual viewport at physical heights 1080/1440/2160. These verify existing merged behavior, not newly fixed defects. The full suite returned **106 passed in 0.54s**, exit 0, using `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`.

Explicit TOC loading and standalone behavior execution through `lupa.lua51` printed `Lua 5.1`, `TOC Lua loaded`, and `behavior: green`. Package build and separate verification each printed **verified 10 files**, exit 0. ZIP SHA-256: `acb26d25072a9373d2db0924c233fdcce2787751fd5bf76bdf96ba74a2d2a8ad`. `git diff --check` exited 0. The package manifest binds every source/archive byte and the exact TOC order.

The main UI started at SHA-256 `f56116e3a2b607dbcc2e322809ff84ca1cee8b61703910e751f35f2b8c5a9fd2`. Only its ADDON_LOADED/PLAYER_LOGIN event hunk changed; the physical-screen conversion and updated shared mocks were retained. Lifecycle inspection confirms controls execute after all TOC chunks and SavedVariables normalization; callbacks can open the native Character UI without requiring a preexisting addon panel. Repeated initialization is idempotent. No merge regression requiring a production fix was found. Pinned CharacterFrame, Settings, and texture API sources were re-fetched and their hashes matched `controls-api.md`.

This is integration verification, **not independent final-review approval**. Fresh commissioned reviews and in-game minimap/category/rendering/combat acceptance remain pending. Comparison data remains unavailable and release automation remains disabled.

## Historical isolated-candidate evidence

The following records the predecessor only; its counts and ZIP hash are not the integrated candidate.

Candidate: isolated copy of tracked and nonignored untracked working-tree source, selected with `git ls-files --cached --others --exclude-standard`. No main-repository, live-addon, WTF, credential, release configuration, GitHub, commit or push changes were made by this task. The concurrently investigated visibility fix is not included.

Python used: `C:/Users/Christian/orca/stat-compass/.venv/Scripts/python.exe`. Commands ran with the scratch candidate as working directory.

## Actual TDD evidence

The following assertions failed before their respective implementation changes, then passed:

- Persisted settings: `minimap visibility must persist`; normalized angle and retained fields were then added to the shared store.
- Native category lifecycle: `native category must register at own ADDON_LOADED`; options/minimap creation and click routes were then implemented.
- Drag behavior: `launcher must support drag`; temporary drag update, scale normalization, geometry invalidation and hide cleanup were then added.
- SavedVariables lifecycle: `TOC execution must not overwrite SavedVariables`; TOC loading was changed to read-only sanitization, with persistence at own ADDON_LOADED/login.
- Documentation: `There is no minimap button` remained in the README; both languages and packaged notes were then updated.

Final full-suite execution returned **95 passed in 0.52s**, exit 0. The baseline suite contained 87 tests; the new controls module has eight collected cases (including three locales). Existing rendering, no-data, privacy/provider, release-gate and lifecycle regressions remain green. A later verification replay is recorded beside the patch, with its own exact timings.

The feature tests exercise native category registration before Character opens, unrelated addon events, idempotence, native canvas reparent/reopen, left/right clicks, inline-to-native skin synchronization, visibility/reset, normalized persistent angles, 86/106-pixel radii, zero-size fallback, scaled dragging, atan2 fallback quadrants, invalid/secret cursor and zero-scale rejection, exact-center stability, hide/ancestor-hide cleanup, localization and English fallback. Geometry and widget behavior are synthetic fixtures around real production Lua, not client execution.

An explicit TOC load printed `Lua 5.1` and `TOC Lua loaded`; standalone `tests/behavior.lua` printed `behavior: green`. Both used `lupa.lua51` and exited 0.

Package build and separate verification printed `verified 10 files`, both exit 0. Candidate ZIP SHA-256: `87d4b438261a102639a191e5ff88910264a6de9b7947acb9c827540835fb7b3e`. Package tests also rebuild twice and compare bytes, exact inventory and TOC order. This local test ZIP is not a published release.

## Pending

Parent must reconcile the small `UI.lua` initialization hunks with the concurrent visibility fix, rerun all combined gates and obtain fresh review. Native glyph/clipping, icon texture appearance, actual drag/click delivery, combat/taint and in-game category behavior remain unverified. No claim is made that the invisible-panel problem is fixed by this work. Comparison data remains unavailable.
