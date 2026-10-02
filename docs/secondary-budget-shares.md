# Secondary budget shares: UI integration contract

This candidate changes UI.lua, adds locale keys, updates UI regression fixtures and documentation. Core.lua, Data.lua, Controls.lua and tools are provider-owned and unchanged. No main-tree or live-addon installation is part of this work.

## Units and presentation

- Only `snapshot.shareComparison[stat]` drives the main number and bar graphics. A main value such as `36%` is a rounded budget share; tooltips retain one decimal. `snapshot.current` effect percentages never substitute for shares, including missing/Secret/unavailable cases.
- Core supplies `currentShare`, `axisMaxShare`, `axisVerified`, `axisProvenance`, `sourceStatus`, `sampleCount` and `reference.{minShare,lowShare,meanShare,highShare,maxShare}`. UI does not sum ratings, compute shares, calculate quartiles or fabricate four readable values.
- The bar is zero to the supplied axis. The main reference is the provider's low/high middle-50% band, with a translucent own fill (alpha 0.35 while a band exists). White min/max markers are thin, mean is 3 physical pixels, current is 5 physical pixels. Dark outlines, original stat colors and symmetric static mean-proximity glow remain. No personal-optimum or performance claim follows from proximity.
- Each min/mean/max label displays a share. Its tooltip shows the corresponding absolute `ratingComparison` value. The current tooltip shows the own absolute rating and budget share, never the combat-effect percentage. Reference ratings require verified axes/status and matching sample counts in the same fresh snapshot. The snapshot/spec binding itself is owned by Core; the payload does not provide independently checkable per-item spec IDs. No previous snapshot is merged into the current one.
- Dynamic sample count and metadata come from the current verified snapshot; no top-30/top-50 count is hardcoded in the new UI copy.

The explanation is on the current-value and source/status tooltips, preserving the full-height layout and footer budget:

> Anteil an deinen Sekundärwerten. Die markierte Spanne zeigt, wo die mittlere Hälfte der Top-Spieler liegt.

> Share of your secondary stats. The marked band shows where the middle half of top players lies.

The metadata tooltip explains that the distribution and mean describe the sample and do not guarantee a balanced build or a personal optimum.

## Fail-closed graphics

`sourceStatus != "verified"` or an unverified/invalid axis hides **everything graphical**: track, fill, IQR band/cue, all four markers and outlines, marker/band hit targets, and glow. A valid own numeric share may remain, explicitly labelled as independent: the row says no comparison/own share only and the own-value tooltip repeats that distinction. This implements “nichts bei unavailable” for all bar graphics, not suppression of the independently known own number.

A nil own share hides fill, current marker and glow, even when reference band/markers remain valid. Core currently makes every own share nil when any of the four raw secondary readings is unreadable. Old effect percentages are never a fallback.

Containers and fields are checked for Secret/public/type validity before arithmetic or formatting. Raw table reads reject metatable-supplied fields. Scalars must be finite and nonnegative. Shares and reference percentages must also be at most 100; graphic values must fit inside the supplied axis. Min/mean/max ordering is validated; low/high must both exist and be ordered, public, finite and in axis. Invalid quartiles hide only the band, retaining separately valid extrema/mean markers. A zero-width IQR is a position cue, not a fabricated interval.

The inspected Core caps its rounded share axis at 100. The renderer accepts any supplied finite positive verified axis, including headroom above 100, without recalculation or clipping it to a new cap. Reference and own percentages remain restricted to 0..100 even on an axis above 100. The axis is a display scale, not a technical rating cap.

Hidden marker/band tooltips release only tooltips actually owned through `GameTooltip:IsOwned`; foreign tooltips remain untouched. Existing small hit regions, marker priority, footer access, ancestor visibility, typography, physical scaling, gutter and Flat specialization class color remain under regression tests. No polling or animation is added.

## Verification scope

New Lua 5.1 tests run the real production builder, Core Snapshot and UI with clearly labelled synthetic/test cohorts of both 30 and 50 observations, plus a synthetic provider handoff using the supplied Paladin example: raw ratings 1014/928/591/290, own shares 35.9/32.9/20.9/10.3 and bands 31.1-43.3/31.9-39.7/12.1-22.1/6.3-14.3. These values are fixtures only and are not written to shipping Data.lua.

Coverage includes unreadable raw ratings, all-own-share unknown, expiry/unavailable transitions, malicious Secret/metatable containers, NaN/infinities/extreme values, out-of-axis shares, incomplete quartiles, tooltip ownership, share/rating/effect-unit separation and axis headroom. Existing geometry, skin, glyph-width proxy, narrow pointer and hidden-work tests have been migrated to share fixtures where their old rating-display expectations were intentionally replaced.

Runtime mocks verify Lua behavior and modeled geometry, not native glyph rendering. Real-client visual acceptance, screenshot inspection and installation remain pending. Historical rating-design documents describe superseded UI; this document defines the current share presentation.
