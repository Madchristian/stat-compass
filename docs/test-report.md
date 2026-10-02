# Test report

## Combined minimap/settings integration (current)

This section supersedes earlier candidate counts and package hashes below. The preserved virtual-to-physical screen fix was integrated with the isolated minimap/native Settings feature through narrow hunks, not whole-file replacement. Full evidence and limitations are in [controls-test-report.md](controls-test-report.md).

- Baseline main: **93 passed in 0.45s** (pytest cache permission warning only). Candidate tests before production integration: **8 failed in 0.31s**. Narrow-hunk integration: **101 passed in 0.62s**.
- Combined lifecycle/geometry verification added five cases; `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` returned **106 passed in 0.54s**, exit 0. All prior virtual-screen and offscreen-owner tests remain present.
- Explicit TOC load and standalone behavior run used `lupa.lua51`: **Lua 5.1**, `TOC Lua loaded`, `behavior: green`.
- Package build and separate verification returned **verified 10 files**; `git diff --check` passed. ZIP SHA-256: `acb26d25072a9373d2db0924c233fdcce2787751fd5bf76bdf96ba74a2d2a8ad`.
- Controls initialize after DB normalization, including before lazy Character loading. Native Settings, Character `onlyShow`, and texture-mask source hashes were rechecked against the pinned Blizzard source. No integration lifecycle regression requiring a new production fix was observed.

No final independent-review approval is claimed. Fresh commissioned reviews and real-client acceptance remain pending. No live-addon/WTF, commit, push, GitHub or release-automation writes were made. Shipped data remains empty; meaningful EU top 50 comparisons remain unavailable.

## Offscreen-owner containment correction (historical)

This section supersedes earlier suite counts and package hashes. Only the horizontal side-attachment guards changed: exterior space already bounds the far panel edge; the attachment edge must now also be within the root viewport. Otherwise the existing UIParent fallback is used. Physical height, data/provider code, and the empty shipped dataset are unchanged.

- RED: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_offscreen_owner.py` exited 1: **7 failed, 1 passed in 0.23s**. Both reproduced wholly offscreen owners failed their respective horizontal containment assertion; the normal-owner control passed. Each mixed-scale/root-offset grid failed at left containment.
- GREEN: the same focused command exited 0: **8 passed in 0.04s**. The new tests cover the reproduced bounds, normal/partially/wholly offscreen owners, root offsets, mixed effective scales, vertical clamping, unchanged physical height, the 424-native-unit host at 1.76 scale, no extra visible geometry-triggered stat reads/rendering, and no hidden stat reads/rendering. They use mock geometry without injecting recommendation data.
- Full suite: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` exited 0: **87 passed in 0.40s**.
- Explicit TOC loading through `tests.test_addon.load_runtime()` printed **Lua 5.1** and `TOC Lua loaded`; executing `tests/behavior.lua` through `lupa.lua51.LuaRuntime` with `arg={}` printed **behavior: green** (exit 0).
- `.venv/Scripts/python.exe tools/package.py` and the separate `--verify` invocation each exited 0: **verified 9 files**, checking exact inventory, TOC agreement, timestamps, manifest hashes, and archive/source byte identity. `git diff --check` exited 0.

Current `dist/StatCompass-0.1.0.zip` SHA-256: **`1d06b8aad7cb01c8957a584548a25aacff60b9fb18711673fc6d78ddabcc1cc5`**. New exact-candidate independent reviews and real-client acceptance remain pending. No installation, commit, push, GitHub write, or provider/data change occurred.

## Local rivals acquisition and release gate, 2026-10-02

This section records the current implementation run; earlier candidate hashes and suite counts below are historical. No independent review approval is implied. New test fixtures are explicitly synthetic; no raw identities were added to the repository or addon ZIP.

Executed vertical RED/GREEN steps:

| Slice | RED command and observed result | GREEN command and observed result |
| --- | --- | --- |
| Bounded spec-window traversal, overlap and hidden ranks | `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_rio_rivals.py` exited 1 during collection: `FileNotFoundError` for the new provider | Same command initially found one rank-1 anchor case (`1 failed, 2 passed`), then exited 0: `3 passed` after visiting rank 1 |
| Local 120-hour release prerequisite gate | `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_release_gate.py` exited 1 during collection: `FileNotFoundError` for the new gate | Same command first found an incorrect test expectation for the idempotency key (`1 failed, 8 passed`); corrected to change the previous release ID, then exited 0: `9 passed` |
| HTTP-date Retry-After and safe network error | Focused provider test exited 1: `TypeError` for missing `clock` argument | Provider suite exited 0: `5 passed`, including the new focused behavior |
| Exact transport query allowlist | Focused provider test exited 1 because an added `access_key` query reached the network boundary | Focused rerun exited 0: `1 passed` after canonical query validation |
| Unique identities across all observed ranks | Focused provider test exited 1 because the same public identity appeared beyond the cutoff | Focused rerun exited 0: `1 passed` |
| Verified data-channel release anchor | Gate suite exited 1: `1 failed, 10 passed` because the new structured prior release was treated as a first release | Gate suite exited 0: `11 passed` after requiring channel `data`, `verified=true`, and a valid publication epoch |

The saved Arcane raw windows were replayed locally through the provider from a rank-1 public seed: 26 requests, ranks 1–50 covered, rank 51 witness, hidden ranks 15/38/40/49, 46 public identities, `strict50Eligible=false`. These windows were gathered in the earlier probe and are an interval collection, not a new atomic snapshot. The Codex sandbox seed attempt exited 1 before HTTP with local `WinError 10013` socket permission denied. The orchestrator subsequently ran the production `get_json(request_url(...), max_attempts=1)` and `_validated(...)` outside that sandbox: one HTTP 200 response, EU Arcane ranks 1–5, selfRank 1, observed `2026-10-02T13:34:16.790126+00:00`. Reserialized response SHA-256: `755f4f9c4d3c5d12d379c94d2ca201eff083d2bc729f118618945ac7df63ee62`; raw output is only at external scratch `rio_probe/provider-live-seed.json`. An independent production-provider replay reconfirmed 26 windows, 46 public identities and the same four hidden positions. No new full crawl was attempted.

Final orchestrator command: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` exited 0 with **79 passed in 0.36s**. Two additional missing/null prior-release-ID cases first failed (`2 failed, 11 passed`); rejecting absent IDs made the gate suite pass (`13 passed`). A repository-local raw directory masquerading as scratch first failed (`1 failed`); resolving it against the actual user scratch boundary and excluding repository descendants made the final suite green. `tools/package.py` and `tools/package.py --verify` each exited 0 with `verified 9 files`. An independent ZIP inspection confirmed the exact nine-file inventory (TOC, Locales, Data, Core, UI, LICENSE, NOTICE, English README, German README), nine manifest file hashes matching archive contents, and archive SHA-256 **`1d2ae51d8eaf6945ee6407f82baedc733c4b83b117b0f84bfefa8fc998e180eb`**. `git diff --check` exited 0. The packaged addon files and empty `Data.lua` are unchanged from the prior candidate.

Remaining blockers: four privacy-hidden Arcane positions prevent strict 50 named players; all-spec completeness, authenticated Blizzard payload/stat semantics, redistribution rights, retention/deletion, and real publication/recovery are unverified. The release gate is local only; no schedule, credentials, GitHub release, installation, commit or push was created.

Date: 2026-10-02. CPython 3.11 in `.venv`; `pytest==8.4.2`, `lupa==2.6`, and `lupa.lua51.LuaRuntime` (`_VERSION` = `Lua 5.1`). The TOC Lua files are loaded in order through the real Lua 5.1 parser/runtime. `lua.exe` 5.4.6 is supplementary only.

## Recorded RED/GREEN work

1. Original vertical slice: `lua tests/behavior.lua` failed with `cannot open StatCompass/Locales.lua` (exit 1) before implementation. It printed `behavior: green` after the first addon files were added.
2. Initial widget-specific Lua 5.1 suite: 5 passed, 2 failed from mistaken test expectations (frame count and a Lua path escape). Corrected expectations: 7 passed. The earlier completed suite reached 14 passed.
3. Follow-up policy/UI regressions were written first. `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_followup.py` returned **4 failed** because the old builder required the old `build`/`generatedAt` schema and lacked separate client build and expiry fields. A further hidden-skin regression failed (1 failed) when `SetSkin` repainted a closed panel; painting was deferred until show. After implementation, the final full suite returned **20 passed in 0.12 s** (exit 0). Two intermediate failures were corrected expectations/error wording for the anchor side and rating-unit rejection. Test-runner duration is not a WoW performance measurement.

4. Orchestrator regressions first returned **2 failed**: restoring the SavedVariables table at `ADDON_LOADED` was ignored, and a full-panel opaque border texture covered the flat background. The event now revalidates the persisted settings; four one-pixel edge textures replace the opaque overlay. After these corrections, `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` returned **22 passed in 0.11 s**. ZIP build and verification both returned `verified 8 files`; the real backend reported `Lua 5.1`. This is implementation verification, not an independent review.

The **Lua-backed tests** cover every TOC Lua file, equipment-page visibility, one latest-data read/render at show, hidden event suppression, visible burst coalescing, stale callback invalidation, parent close/reopen, specialization and context changes, all registered stat events, saved settings on actual Lua load, reset, frame count stability, both skins including border/hover/selected surfaces, lazy Character UI loading, tooltip metadata, screen-side clamping, deDE/enUS/fallback strings, measured mock text bounds, secret return values and nested containers, missing APIs, same-interface/different-client-build mismatch, expiry boundary/future/unknown server time, exact 50 synthetic rows, mastery-effect semantics, unit rejection, and unknown target values. Native WoW secret behavior and visual dimensions still require in-game acceptance.

The **Python tests** validate the offline builder's schema, raw SHA-256, source/unit/count/expiry rejection, control-character rejection, and Lua 5.1 serializer roundtrip. They build the ZIP twice and compare bytes, verify fixed timestamps, exact eight-file archive inventory, per-file and archive SHA-256 hashes, and exact TOC-to-allowlist Lua agreement. Synthetic rows and timestamps are labeled test-only and are never in the shipped `Data.lua`.

`docs/research-original.md` byte-matches `git show HEAD:README.md`; `docs/top50-eu-source-research.md` byte-matches the supplied research file. No WoW/WTF installation, native glyph/attachment/combat check, in-game timing, provider API authentication, or independent review was performed here. See [pending acceptance](acceptance.md).

Final commands, all successful:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe tools/package.py
.venv/Scripts/python.exe tools/package.py --verify
lua tests/behavior.lua
git diff --check
```

Final `dist/StatCompass-0.1.0.zip` SHA-256: `9ec7da650832af86e8ae33a41c122907221a8c5a8cf49b955bd1a5aec7b1f76f`. `dist/StatCompass-0.1.0.sha256.json` records file hashes and the exact eight-file inventory. Both build outputs are ignored by Git.

## Current bounded-review verification (supersedes the earlier final block)

Date: 2026-10-02. Exact per-defect RED and GREEN commands and outcomes are in [review-fixes.md](review-fixes.md). All new fixtures are synthetic and `StatCompass/Data.lua` remains empty.

Final commands from the repository root:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
lua tests/behavior.lua
.venv/Scripts/python.exe -c "from lupa.lua51 import LuaRuntime; print(LuaRuntime().eval('_VERSION'))"
.venv/Scripts/python.exe tools/package.py
.venv/Scripts/python.exe tools/package.py --verify
git diff --check
```

Results: full suite exit 0, **30 passed in 0.25 s**; standalone Lua behavior exit 0, `behavior: green`; Lupa backend exit 0, `Lua 5.1`; package build exit 0, `verified 9 files`; package verification exit 0, `verified 9 files`. `git diff --check` exited 0 with only Git's LF-to-CRLF notice for `README.md`. The package test also rebuilt twice and checked byte identity, exact allowlist/TOC agreement, fixed ZIP timestamps, archive SHA-256, and each packaged file against the source bytes. Final ZIP SHA-256: `e8f0ef2467b6ef41cd9c87018ca221920f0d72e5d4bb9dbe0ccb922128f2c757`. The ninth file is `StatCompass/README.de.txt`.

The work remains **BLOCKED for meaningful EU Top 50 target comparisons** until a permitted, verified dataset and its distribution rights exist. No live WoW installation, game session, provider authentication, or independent approval review occurred in this run.

## Second bounded follow-up verification, 2026-10-02

The new RED and GREEN regression history is in [review-fixes.md](review-fixes.md). The final commands from the repository root produced these outputs:

| Command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | Exit 0; `35 passed in 0.20s` |
| `lua tests/behavior.lua` | Exit 0; `behavior: green` |
| `.venv/Scripts/python.exe -c "from lupa.lua51 import LuaRuntime; print(LuaRuntime().eval('_VERSION'))"` | Exit 0; `Lua 5.1` |
| `.venv/Scripts/python.exe tools/package.py` | Exit 0; `verified 9 files`; ZIP SHA-256 `b6835ec9a1b90046e83424d7ac7577c683e8b469af713ff7011e8e59e3d4d60a` |
| `.venv/Scripts/python.exe tools/package.py --verify` | Exit 0; `verified 9 files` |
| `git diff --check` | Exit 0; only the existing LF-to-CRLF notice for `README.md` |

The archive was rebuilt and checked against the nine-file allowlist, TOC Lua list, fixed ZIP timestamps, manifest hashes, and source bytes. The dataset remains empty; no live install, Git staging or commit, GitHub action, or approval review was performed.

Orchestrator rerun: full suite returned `35 passed in 0.19s`. Executing `tests/behavior.lua` directly through `lupa.lua51` initially failed because the CLI-provided `arg` table was absent; initializing `arg={}` fixed that harness prerequisite. The corrected real Lua 5.1 run printed `Lua 5.1` and `behavior: green` (exit 0). Package rebuild and separate verification both printed `verified 9 files`, retaining the ZIP hash above; `git diff --check` exited 0 with the same line-ending notice. These are execution checks, not independent review approval.

## Final expiry and Secret visibility verification, 2026-10-02

Supersedes earlier suite counts and archive hashes. RED/GREEN evidence is in [review-fixes.md](review-fixes.md).

| Command | Result |
| --- | --- |
| Focused expiry/Secret visibility command in review-fixes | Before production fix: exit 1, `3 failed, 1 passed in 0.09s`; after: exit 0, `4 passed in 0.03s` |
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | Exit 0; `38 passed in 0.21s` |
| `.venv/Scripts/python.exe -c "from pathlib import Path; from lupa.lua51 import LuaRuntime; lua=LuaRuntime(); print(lua.eval('_VERSION')); lua.execute('arg={}'); lua.execute(Path('tests/behavior.lua').read_text())"` | Exit 0; `Lua 5.1`, `behavior: green` |
| `.venv/Scripts/python.exe tools/package.py` | Exit 0; `verified 9 files` |
| `.venv/Scripts/python.exe tools/package.py --verify` | Exit 0; `verified 9 files` |
| `git diff --check` | Exit 0; existing README LF-to-CRLF notice only |

Rebuilt `dist/StatCompass-0.1.0.zip` SHA-256: `34269fa0271985adace5813ca6be4560d867fd543597fb2800f34405b313da81`. The archive and manifest verification checked exact inventory, TOC agreement, fixed timestamps, hashes, and source-byte identity. The full suite includes normal expiry and stale callback ownership checks, plus missing/Secret/changed-without-event spec expiry and effective Secret visibility render suppression.

No real dataset was added; meaningful EU Top 50 comparisons remain blocked on permitted verified data. No commits, GitHub writes, live installation, or in-game acceptance occurred. Fresh independent reviews of this exact candidate remain pending; this report is not review approval.

## Orchestrator final verification (supersedes candidate hashes below)

The actual Codex CLI used `gpt-6-sol` for the main implementation and the physical-scale blocker corrections. Independent local execution then reproduced `55 passed`, real `Lua 5.1` and `behavior: green`, and verified the nine-file package. A further marker-ink clearance regression at host heights 424, 530 and 750 first returned `3 failed in 0.09s`: the tall minimum ticks crossed headings in compact layouts, and maximum ticks crossed endpoint text. Adaptive tick heights corrected those overlaps. The focused rerun returned `3 passed in 0.04s`; the complete suite returned `58 passed in 0.37s` using `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`.

Package build and separate verification both returned `verified 9 files`. Current ZIP SHA-256: `1d2ae51d8eaf6945ee6407f82baedc733c4b83b117b0f84bfefa8fc998e180eb`. Per-file hashes are in `dist/StatCompass-0.1.0.sha256.json`. The real-client screenshot, native font appearance, and final independent reviews remain pending. No installation, commit, push, source authentication, or publication occurred.

## Screenshot-directed full-height bar candidate, 2026-10-02

The pre-change baseline was `38 passed in 0.21s`. After adding the first four full-height/bar tests and before changing production Lua, the focused command returned **4 failed in 0.08s**: no exact `range`, no full-height panel, and no bar/marker widgets. After implementing exact 50-row minima/maxima, bars, opaque skins, layout, and the revised mock geometry, the focused command returned `4 passed in 0.04s`. Two more geometry tests were added; the first run returned `1 failed, 5 passed in 0.09s` because the mock did not fire `OnSizeChanged` for `UIParent:SetSize`. The mock was corrected and the full suite passed. A final finite-axis/marker-bounds test brought the suite to **45 passed in 0.40s**.

The suite loads every TOC Lua file through `lupa.lua51`. A separate run of `tests/behavior.lua` printed `Lua 5.1` and `behavior: green`. After the final backing and minimum-height checks, the full suite returned **45 passed in 0.27s**. An explicit TOC load printed `Lua 5.1` and `TOC Lua loaded`. Package build and separate `--verify` both printed `verified 9 files`; candidate ZIP SHA-256 is `e70d8287b13a87e54742676a1775e8f1d1c5140b57ca5df7ecdba3d4fc9fad62`. `git diff --check` exited 0 with the existing README line-ending notice.

The mock checks physical top/bottom alignment, host movement and resize, effective parent/child scales, viewport side/fallback, four native texture bars, fixed current/min/max labels, exact endpoints including coincidence, absent/Secret current, missing cohort, huge finite axes, both skins, and German/English copy. **Real-client screenshot acceptance remains pending.** The screenshot may expose font metrics, texture opacity, or frame anchoring differences that the Lua mock cannot prove. `Data.lua` remains empty; no live install, commit, push, or publication was performed.

## Independent-review blocker corrections, 2026-10-02

Ten screenshot-scale and readability cases were added before production changes. The first focused run was **8 failed in 0.13s**: all 424-native-unit host cases hid the panel, width changes left bars stale, the axis stayed at 100%, coincident ticks overlapped, and compact text/layer checks could not run. The first implementation pass returned **7 passed, 1 failed in 0.10s**; the remaining test had kept the bar's local width constant while changing only its physical scale. The test now forces a real viewport width change and also checks a scale change. The focused suite returned **10 passed in 0.09s** after adding mixed root/owner scales and bottom-zero/offscreen fallback cases.

The mock now measures `GameFontNormalLarge` separately from `GameFontNormal`, models texture sublevels, and checks label/button widths and vertical gaps in both locales at the narrow accepted layout. The geometry cases include a 424-unit CharacterFrame at effective scales 0.8, 1, and 1.76, a 1659×777 physical viewport, and a host bottom at physical zero. Existing layout assertions were updated to compare physical dimensions, because the panel now has an independent local scale.

Final verification from the repository root: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` returned **55 passed in 0.34s**; explicit TOC loading returned `Lua 5.1` and `TOC Lua loaded`; standalone behavior returned `Lua 5.1` and `behavior: green`; package build and `--verify` each printed `verified 9 files`; `git diff --check` exited 0 with the existing README line-ending notice. Candidate ZIP SHA-256: `e3e48c94dc1571fd7a04a02bf936e4510287dce6e0ee2bcdffa01a097408c671`. Real-client screenshot acceptance is still pending. No external writes, live install, commit, push, or publication occurred.
