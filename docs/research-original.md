# Stat Compass

Status: idea and research only. Implementation is deferred. There is no installable addon, tested fix, or release in this repository.

## Goal

A small, independent WoW Retail addon that only compares the player's secondary stats with specialization-specific recommended targets. Keep the useful stat guidance from RecommendedStats without its BiS, talent, rotation, or other expanded features.

Working name: **Stat Compass**. Use a separate addon identity and SavedVariables so it cannot overwrite RecommendedStats settings.

## Agreed scope

- Current secondary stats versus recommended targets for the player's class/spec.
- Raid / Mythic+ context selection.
- Compact panel attached to the character equipment/stats window.
- German and English, automatic locale selection with English fallback.
- Clearly show source data date and sample size.
- Explain that top-player target distributions are not personalized simulation-derived stat weights or guaranteed optimal values.

Excluded: BiS item lists, gems/enchant inspection, item or tooltip scans, talents, rotations, skin import/export, rating prompts, extra feature windows, and unrelated functionality. A minimap library stack is not a requirement.

## Performance contract for the future implementation

- Closed character window: no panel rendering and no expensive stat evaluation. Minimal invalidation/bookkeeping is allowed.
- Opening the window: read current values and render once; never show stale data from the last opening.
- While visible: coalesce relevant event bursts and only update necessary display values.
- Avoid permanent polling timers, OnUpdate work, and repeated frame creation.
- Defer hidden-page work, rather than merely hiding already rebuilt widgets.
- Handle Retail secret values safely before comparisons, formatting, arithmetic, or persistence.
- In-game profiling and usable visual acceptance are required. Mocks cannot establish millisecond improvements.

## Upstream source and attribution

- Source: https://github.com/VaughanT31/recommendedstats
- Inspected repository snapshot: `ea1ddf34af3ef1091f0680c4c6b52191bc62f151`.
- Version-specific archive used for static inspection: [RecommendedStats_V2.0.0-2026-10-02.zip](https://github.com/VaughanT31/recommendedstats/blob/ea1ddf34af3ef1091f0680c4c6b52191bc62f151/Releases/RecommendedStats_V2.0.0-2026-10-02.zip).
- Upstream bug report with measurements and hypotheses: https://github.com/VaughanT31/recommendedstats/issues/8
- [Upstream license at inspected snapshot](https://github.com/VaughanT31/recommendedstats/blob/ea1ddf34af3ef1091f0680c4c6b52191bc62f151/LICENSE): MIT, Copyright (c) 2026 VaughanT31.

MIT permits reuse and modification subject to retaining the copyright and permission notice in copies or substantial portions. Before importing code/data, record exact provenance and retain the complete upstream MIT text. Check any third-party data or bundled-library terms separately. This planning repository does not yet copy upstream implementation or datasets, and does not select a license for future original code.

Do not claim the current upstream branch is identical to the tested installed addon. The release's version label matches the profiler label, but installed files were not byte-compared with the ZIP. The pinned repository commit is a source locator, not proof of the installation's commit.

## Measurements motivating this project

The user noticed stutters after the latest RecommendedStats update and investigated the same scene using CapFrameX and Numy's Addon Profiler. The suspected UI action was opening and closing the **character equipment/stats window, not the bags**.

Hardware: Ryzen 7 7800X3D, RTX 4090, 64 GB RAM; Windows 11; WoW Retail, DX12, 3840x2160. CapFrameX 1.9.1.5; AddonProfiler 1.4.37; RecommendedStats version label 2026-10-02.

### Paired 60-second comparison

Only RecommendedStats was disabled for the second run; other addons, including the profiler, remained enabled.

| Metric | RecommendedStats enabled | RecommendedStats disabled |
| --- | ---: | ---: |
| Capture identifier | 2026-10-02T114632 | 2026-10-02T114956 |
| Frames | 6930 | 6868 |
| Average FPS | 115.5 | 114.5 |
| P1 FPS | 53.9 | 50.4 |
| P0.1 FPS | 21.6 | 25.3 |
| Longest frame | 265.8 ms | 85.9 ms |
| Frames over 50 ms | 7 | 2 |
| Frames over 100 ms | 3 | 0 |

P1/P0.1 are the inverses of interpolated 99th/99.9th frame-time percentiles, not averages of slowest-frame subsets.

Enabled run: long frames at 34.79 s (153.4 ms), 44.68 s (134.8 ms), and 58.34 s (265.8 ms). GPU active time for those frames was about 5-7 ms.

Profiler enabled run: RecommendedStats peak 248.954 ms and three frames over 100 ms; overall addon peak 249.538 ms; RecommendedStats average 0.066 ms/frame. History Since Reset, Active Mode, approximately 65 seconds.

Disabled run: overall addon peak 62.978 ms, no addon frames over 100 ms; GSE peak 62.154 ms. Profiler window approximately 61 seconds.

Interpretation: strong evidence that RecommendedStats contributes to severe intermittent stalls in this configuration. Average FPS did not improve, smaller stalls remained, and this is one paired comparison rather than a repeated statistical benchmark. Profiler values are accumulated attributed CPU time **per frame**, not necessarily individual function calls. Different capture windows prevent exact event matching.

Earlier exploratory captures were shorter or had mismatched profiling windows. One four-minute profiler view recorded a RecommendedStats peak of 731.209 ms, but that observation may include loading/first-open work and should not be substituted for the paired comparison.

Raw captures and screenshots remain with the user; they have not been uploaded here. Do not publish unsanitized machine names, paths, or account metadata.

## Static findings: hypotheses, not measured function-level causes

Line numbers below refer to files inside the pinned October 2 archive.

1. `UI/CharacterPanel.lua:866-867`: CharacterFrame OnShow and OnHide both call `RS:SyncVisibility()`.
2. `Core.lua:449-456`: SyncVisibility always invokes Refresh after synchronizing visibility.
3. `Core.lua:424-426`: Refresh evaluates data and invokes all refresh listeners.
4. `Core.lua:570-576`: COMBAT_RATING_UPDATE and PLAYER_EQUIPMENT_CHANGED directly trigger Refresh, with no coalescing at this entry point.
5. `UI/BiSWindow.lua:691-695,746-759`: Render only checks whether the page exists, not whether it is visible, then updates BiS rows. After first creation, hidden-page work remains possible.
6. `UI/BiSWindow.lua:616-628,670-687`: row updates perform item/gem lookups; ItemRatings can fall back to hidden tooltip scanning (`:184-220`). Enchant information already has a cache; not every lookup is uncached.

This is a plausible explanation for a change after first opening the character window, but the actual expensive function has not been isolated in-game. Tooltip-addon interactions and multiple events in one frame are still possible contributors. Do not describe the regression's introducing commit as known.

## Data strategy and open decisions

Start with an explicitly pinned, attributed target dataset. Inspect the actual dependencies before selecting upstream files; likely candidates include StatTargets, Meta, SampleSize and any context metadata that the reduced evaluator really requires. Do not import BiS/talent/rotation datasets merely because upstream loads them.

Decide later how stat-only data updates will be reviewed, validated, versioned and shipped. Never silently pull upstream executable code or equate a current TOC version label with current data. Addons should not be designed around direct HTTP access in-game.

Remaining decisions: final name, distribution/license for original work, update process, target values presentation, and exact UI layout. Reuse only the minimal required implementation after dependency and provenance review.

## Later implementation and acceptance

1. Inspect the pinned source, confirm installed baseline if needed, and map stat-only dependencies.
2. Define data/schema boundaries, locale strings and compact UI specification.
3. Write behavioral tests before implementation: hidden events do not evaluate/render; opening shows latest stats exactly once; visible bursts coalesce; spec/context/locale changes work; secret values fail safely.
4. Implement the isolated stat-only addon without excluded feature dependencies.
5. Verify syntax, TOC/data loading, license notices, namespace separation and no unrelated modifications.
6. Obtain explicit permission before writing the WoW installation. Back up and deploy only with the client closed using fail-closed process checks.
7. Perform visible in-game acceptance and repeated comparable A/B captures, separating login/first-open costs from steady state. Test character-window open/close, spec/context changes and combat handling.
8. No release or claim of a performance fix before real in-game evidence. Future implementation commits, publication and releases require fresh authorization.

## Related work, kept separate

A separate WeeklyAltTracker investigation also found hidden-window rendering and uncoalesced scan events. Its report explicitly distinguishes mock invocation counts from in-game timings and notes that AddonProfiler counters aggregate per-frame time. This supports the testing discipline above, but does not prove RecommendedStats has the same measured cause or justify including WAT code in this project.
