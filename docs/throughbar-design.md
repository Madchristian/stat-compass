# Through-bar comparison (latest approved design)

Implemented on an isolated current-working-tree snapshot. No provider, Core, Data, controls, live addon, or main-tree changes. The snapshot includes non-ignored in-progress typography/footer regression tests recorded in baseline-manifest.json.

- One rating bar per stat; existing red/blue/yellow/green palette and current provider `ratingComparison` contract retained. Core currently provides a **dynamic observed/current comparison scale plus headroom**, not a verified technical equipment cap. UI does not invent or change that contract.
- Cohort minimum/mean/maximum use white vertical lines through the bar; mean is thicker. White ink extends 4 physical pixels above/below the track; dark outlines extend one additional pixel. Fixed labelled minimum/mean/maximum values avoid label collisions. Coincident markers share the same true x; their separate labelled targets remain accessible.
- Static stat-colour glow near the cohort mean, symmetric about the track, with alpha decreasing linearly with absolute distance / maximum half-spread. Zero spread, absent mean, unknown values, or unverified references suppress glow. No animation or permanent OnUpdate.
- Individual current/minimum/mean/maximum label hitframes fit the measured visible text and alignment. Narrow marker hitframes provide the same concise details. Empty columns and the old row/panel surfaces have no tooltip. Coincident marker hitboxes may overlap; the fixed role labels remain distinct targets.
- Current tooltip: rating and secondary percentage. Minimum/maximum: lower/upper observed value. Mean: descriptive average, signed rating difference, short glow hint. Source/sample/date/freshness information is restricted to the metadata target.
- Tooltip ownership is checked with actual `GameTooltip:IsOwned` before refresh/leave/hide; foreign tooltip contents remain untouched. Physical/virtual placement, class-coloured Flat specialization, native options/minimap, width fitting, and footer clickability retained.

## Evidence and limits

Actual Codex gpt-6-sol implementation followed by direct independent correction of an invalid mock-only FontString geometry dependency, and narrowing label hitboxes to rendered text. RED logs: throughbar-red.log, native-hit-red.log, narrow-hit-red.log. Final full run: throughbar-final.log, 291 passed using project Python and `lupa.lua51`.

Tests exercise coordinate pointer targets, both equal-level sibling orders, foreign/private tooltip ownership, physical protrusion and clearance, yellow contrast and skin roundtrips, partial/zero-span references, symmetric distance response, lifecycle/hidden reads, existing provider-to-renderer integration, typography and virtual screen geometry.

No browser preview was needed or produced. No live-client verification: native font rasterization, texture appearance (including client IconAlert glow asset), true client pointer arbitration, and final screenshot acceptance remain required. Do not treat mocked geometry as native visual approval.
