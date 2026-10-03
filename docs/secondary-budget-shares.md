# Rating targets: UI integration contract

This document supersedes the share-primary UI design; its path is retained for existing links. The UI consumes the existing Core payload without changing provider calculations or the data contract. The user accepted the Guardian panel screenshot and custom icon locally; broader acceptance remains tracked in `acceptance.md`.

## Units and presentation

Only `snapshot.ratingTarget[stat]` drives main numbers, status and bars. Fields are `currentRating`, `targetRating`, `lowRating` (P40), `highRating` (P60), `targetPercent`, `sampleCount` and `sourceStatus`. Targets are direct cohort median gear ratings with P40–P60 rating endpoints; live percentage conversions are not used. `targetPercent` is the cohort median percentage for tooltip context. The current producer omits `personal`. The UI never recomputes targets or percentiles. Neither `snapshot.current` effect percentages nor budget shares substitute for ratings.

The stat-colored current rating is large on the left, beside a smaller `Target 638` / `Ziel 638` label (example only). The own fill is opaque. A white target marker is 3 physical pixels wide with a 5-pixel dark outline; it extends 4 physical pixels above and below the track. A two-unit strip shows P40 to P60. Coincident endpoints use a one-physical-pixel position cue without inventing interval width. There are no min/max/mean/current markers, hidden legacy share headings or proximity glow. Stat colors remain Crit red, Haste blue, Mastery gold and Versatility green. A static decorative glow follows the exact fill width: native WHITE8X8 textures fade from 0.65 alpha to transparent over 3 to 9 physical pixels, depending on layout density. All four edges and the fading corner slices sit below the band and target marker. Valid in-band and above-band values receive the same full glow, with no distance fade; below-band, zero, unreadable or invalid comparisons receive none. This is cosmetic emphasis, not a performance/optimality claim or a claim that more is always better. No glow input frames, animations or timers exist.

Status compares the unrounded own rating with the supplied endpoints: below P40 is `too low` / `zu niedrig`; P40 through P60 inclusive is `fits` / `passt`; above P60 is `above` / `darüber`. These labels describe the supplied target band, not simulated performance.

All four display axes are fixed at 0–2000 rating, including zero, refresh and specialization changes. The endpoint labels share the status line without overlapping it. This user-selected display range is neither a technical cap nor a recommended maximum. Drawing alone is clamped: an own or target value above 2000 keeps its number plus `>`; an upper band endpoint above 2000 adds `Band >2000` / `Spanne >2000` to status. Tooltips retain unclamped values (17 significant digits for overflow), explain the edge and include both P40/P60 endpoints. Even a wholly offscale band remains visibly flagged. Width fitting uses the actual native FontString measurement after updates and layout. At minimum height the track is 6 units tall, increasing to 20 at the full-height layout; the existing row height and marker clearance are unchanged.

## Separate DR guides

The user supplied first diminishing-return guide values: Crit 1380, Haste 1320, Mastery 1380 and Versatility 1620. These numbers are not asserted as independently verified here. They never participate in target, band, status or scale calculations. The DR graphic notch, outline and its bar hit target are removed; the vertical white target marker stays unchanged. The separate `DR 1380` label occupies the right of the stat-name line and remains reachable even when DR and target coincide. The label retains its own tooltip explaining first DR onset, continued benefit at a lower incremental rate, exclusion of percentage buffs, and that the guide is no cap, target or optimum.

Guides are shown only for readable Retail mainline project constants, interface 120100 and player level 90. The existing snapshot exposes no player level, so UI calls guarded `GetBuildInfo` and `UnitLevel` once per visible render, with no Core or data-model changes. Missing, Secret, erroneous or unsupported context omits DR without removing a valid target. Unavailable targets retain the prior own-number-only behavior: no track, axis labels or DR graphics. Hidden/collapsed render paths perform no additional API reads.

## Tooltips and priority

Current and target values have small independent tooltip targets. The target marker has its own hit target, above the band input level. Narrow, coincident and offscale bands can be covered by a marker hit rectangle; their endpoints are also included in the independent target-label tooltip. Tooltips expose `targetPercent`. An absent `personal` is the normal pure-rating contract and produces no conversion warning. For older payloads only, a public boolean `personal=false` retains the legacy note (`true` produces none):

> Ziel aus den Wertungen der Top-Spieler, eigene Umrechnung nicht lesbar

If finite nonnegative `snapshot.ratingTarget.totals.targetRating` exceeds `ownRating`, both value tooltips add `Die Ziele zusammen übersteigen dein Budget um X`. Equal or lower totals produce no warning. Unknown totals do not invent one.

The footer shows `Prio` from `snapshot.target.priority`, localized and in supplied order. It requires exactly the four distinct known stat keys. It does not sort or calculate stat weights. Missing or malformed order shows priority unavailable; without a verified target the footer instead shows target unavailable. The metadata tooltip includes the exact German explanation:

> Reihenfolge danach, wie viel ihres Sekundär-Budgets die Top-Spieler in den Wert stecken. Kein simulierter Wert.

Sample size and provenance come from the current snapshot, never a hardcoded top-N count. The priority tooltip also retains source/date metadata. No previous snapshot is merged into a fresh one.

## Fail-closed behavior

Check Secret/public/type validity before indexing, formatting, comparison or arithmetic. Read fields with `rawget` so metatables cannot manufacture values. Ratings and target percentages must be finite and nonnegative; target percentages are effect percentages and are not limited to 100. Counts must be positive integral numbers up to the existing one-million validation limit. A verified target requires `sourceStatus="verified"`. The legacy `personal` field is optional; if present it must be public and boolean. Secret or nonboolean flags are rejected before comparison.

Unavailable source or invalid target/percentage/count/personal data retains only a readable current rating. Target labels, track, fill, marker, outline, band and all reference hit regions disappear. A missing current rating removes the fill and status classification while a separately valid target can remain. Zero is readable, not unknown. One missing raw stat does not blank other readable own ratings.

P40/P60 must be public finite nonnegative endpoints enclosing the target. Missing, Secret, reversed or inconsistent endpoints remove the band and threshold classification, retaining an independently valid target. A zero-width band is valid. Malformed priority does not remove an otherwise valid rating target.

Hidden target/band tooltips release only tooltips actually owned through `GameTooltip:IsOwned`. Foreign tooltips remain untouched. Hidden panels perform no reads, layout or render work. There is no animation or polling.

## Verification scope

Lua 5.1 tests exercise production builder → Core Snapshot → UI with synthetic cohorts of 30 and 50 observations. They check target/endpoint identity, current readability, fallback, budget warnings, expiry and stale tooltip transitions, malformed public/Secret/metatable containers, NaN/infinities/zero/extreme finite values, inclusive thresholds and localized priority validation.

Existing physical placement, native marker ink, minimum-height vertical stack, glyph-width proxy, both skins, pointer targeting in both sibling orders, tooltip ownership, sidebar persistence and hidden-work tests remain active. Fixed-axis regressions cover all four DR labels, supported/unsupported/Secret API context, DR-target coincidence, overflow numbers and tooltips, zero/exact-2000/extreme ratings, width/height/scale geometry, foreign tooltip ownership and collapsed DR read counters. Old dynamic-axis expectations now assert a stable 2000 axis without changing Core's separately retained comparison metadata.

Mocks establish Lua behavior and modeled geometry, not native glyph rendering. The Guardian screenshot and icon have local user acceptance. Independent exact-tree reviews and remaining in-game checks are separate; no all-client, Paladin or performance acceptance is implied.

## Sidebar and context

Only the three skin/reset buttons exist in the panel. There are no Raid or Mythic+ mode buttons. Saved modes migrate to `mythic`; active snapshots always request that context. The provider validator can still validate historical raid datasets. The specialization line contains only the escaped name.

The styled +/− sidebar button belongs to CharacterFrame, not the hidden panel. It is 18-by-18 host-local units, anchored TOPRIGHT at (-4,-22), in the gap below the close control and above the equipment tabs. It inherits host scale rather than panel scale; the reported approximately 1.76 screenshot scale therefore gives a roughly 32-pixel control instead of the previous roughly 56-pixel control. Screenshot-derived close/tab exclusion regions are exercised at several host scales and pixel densities; real-client confirmation remains required. `collapsed` is a sanitized boolean, defaulting to false; full reset expands, while appearance reset retains it. Equipment-tab and ancestor visibility govern both siblings. Collapse invalidates pending refresh generations, hides owned row tooltips and prevents snapshot reads, layout and row rendering. Expansion immediately reads the current snapshot. Sidebar tooltip refresh/hide checks native ownership before touching GameTooltip.
