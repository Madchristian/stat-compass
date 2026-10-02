# Bounded review fixes

All regressions use synthetic test data. Commands below were run from the repository root with `.venv/Scripts/python.exe` and its Lua 5.1 backend. Each RED preceded the corresponding production edit.

1. Effective visibility RED: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_review_fixes.py::test_effective_ancestor_visibility_suppresses_work_and_refreshes_on_restore` → exit 1, `1 failed in 0.05s`; assertion at Lua test line 11: a hidden ancestor still allowed work.
   GREEN: same command → exit 0, `1 passed in 0.01s`.
2. Finite aggregation RED: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_review_fixes.py::test_large_finite_percentages_have_finite_mean_and_bounded_text` → exit 1, `1 failed in 0.06s`; Lua line 3: 50 finite Haste values summed to infinity.
   GREEN: same command → exit 0, `1 passed in 0.02s`.
3. Visible expiry RED: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_review_fixes.py::test_visible_target_expires_once_and_old_lifecycle_timer_cannot_render tests/test_review_fixes.py::test_expiry_timer_is_replaced_on_context_data_refresh_and_unknown_clock` → exit 1, `2 failed in 0.08s`; no expiry timer existed (first test line 5, second test indexed a missing callback).
   GREEN: same command → exit 0, `2 passed in 0.04s`.
4. Observation chronology RED: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_review_fixes.py::test_observation_window_and_summary_in_builder_and_runtime` → exit 1, `1 failed in 0.07s`; builder accepted a row 86,401 seconds older than the reported observation.
   GREEN: same command → exit 0, `1 passed in 0.03s`.
5. Metadata markup RED: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_review_fixes.py::test_all_render_bound_metadata_escapes_wow_markup` → exit 1, `1 failed in 0.08s`; tooltip contained unescaped texture markup (Lua line 4).
   GREEN: same command plus chronology and expiry regression → exit 0, `3 passed in 0.05s`.
6. Placement RED: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_review_fixes.py::test_panel_placement_uses_physical_scales_and_owner_move_signals` → exit 1, `1 failed in 0.08s`; scale 1.5 selected an overflowing right anchor (Lua line 7).
   GREEN: same command → exit 0, `1 passed in 0.02s`.
7. German package README RED: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_review_fixes.py::test_packaged_german_readme_has_matching_status_and_inventory` → exit 1, `1 failed in 0.10s`; `StatCompass/README.de.txt` did not exist.
   GREEN: same command → exit 0, `1 passed in 0.02s`.

The full-suite integration run initially returned exit 1, `2 failed, 28 passed in 0.30s`: scaling each value by 1/50 introduced floating-point drift in an existing exact-mean assertion, and a dependent target assertion failed. The online mean retained finite aggregation while preserving exact constant inputs. The three affected tests then returned exit 0, `3 passed in 0.04s`. A later focused run of all review regressions returned exit 0, `8 passed in 0.06s`.

## Second bounded follow-up, 2026-10-02

The added regressions use only synthetic rows. The first focused run (`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_review_fixes.py -k 'row_age_relative or native_owner_move or same_expiry_replacement or extreme_scientific'`) exited 1 with **3 failed, 1 passed in 0.09s**. The three failures showed that 50 old rows could pass with recent collection, native `StopMovingOrSizing` did not reanchor the panel, and a shown tooltip kept old text after a same-expiry data replacement. The initial scientific fixture was too narrow for the mock width, so it did not prove the overflow.

The row-age fix now rejects a row observed more than 30 days before `collectedAt`; the exact 30-day boundary passes in both the Python builder and Lua 5.1 runtime. The owner geometry fix listens to `StopMovingOrSizing`, `SetAllPoints`, and drag stop, and checks calculated coordinates before `SetPoint`. Expiry callbacks now bind to dataset identity, mode, spec, token, and generation. A shown tooltip receives the refreshed text, including the unavailable message at expiry.

The scientific fixture was strengthened with mixed `1e-308` and `1e308` mastery values and a measured mock glyph width of 9 pixels. With the width fallback temporarily removed, its focused command exited 1, **1 failed in 0.07s**, at the 194-pixel assertion. Restoring the fallback gave **1 passed in 0.02s**. It retains the finite mean and omits the band when the measured text exceeds the column; no numeric rating ceiling was introduced.

After the fixes, the four original focused regressions returned **4 passed, 8 deselected in 0.05s**. A further same-expiry context regression with valid Raid, Mythic+, and second-spec cohorts returned **1 passed in 0.04s**; it checks that callbacks from both prior mode and prior spec cannot render. Final full-suite, Lua, and package results are recorded in [test-report.md](test-report.md). No review approval is claimed.

## Final expiry-callback correction, 2026-10-02

Before changing production code, the focused command below returned exit 1, **3 failed, 1 passed in 0.09s**. All three expiry variants failed at `expiry must refresh even without a readable matching spec`: missing spec, Secret spec, and changed spec without an event. The corrected Secret visibility test already passed; its old `IsShown` overrides did not exercise the production `IsVisible` path.

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_review_fixes.py::test_expiry_invalidates_target_when_spec_unreadable_or_changed tests/test_addon.py::test_secret_visibility_result_is_gated
```

The single production change removes the fresh `A.ReadSpec() == specID` requirement from the expiry callback. Visibility, generation, token, dataset identity, and mode ownership checks remain; the owned callback clears the schedule and calls `Flush`, whose snapshot handles current or unknown spec. Previously refreshed spec contexts still invalidate old callbacks through the token. No polling or retry loop was added.

The same focused command then returned exit 0, **4 passed in 0.03s**. The expiry fixtures assert cleared scheduling, removal of rendered target and open tooltip metadata, no extra timers, and no render from a replayed callback. Existing tests retain normal expiry and stale lifecycle/data/mode/spec callback coverage. The visibility fixture now overrides `IsVisible`, proves a normal visible render, and asserts the render count remains unchanged for a Secret effective-visibility return.

The full suite returned **38 passed in 0.21s** under Lua 5.1; package rebuild and verification succeeded. These are implementation checks only: fresh exact-tree independent reviews remain pending. `Data.lua` is unchanged and contains no real dataset; no commits, GitHub changes, or live writes were performed.
