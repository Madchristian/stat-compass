Stat Compass 0.1.0 — Retail 12.1.0
Copy this StatCompass directory into Interface/AddOns only after separate
installation approval. Open the Character equipment page to see the panel.
The panel matches CharacterFrame height and shows four current-stat rows.
Main numbers and bars show rating points from Core's ratingTarget.
Your large stat-colored rating sits beside a labelled target. Your rating fills
the bar; a white marker shows the target and a narrow strip shows P40 to P60.
Status reads too low / fits / above, with both endpoints included in fits.
A static glow surrounds the fill within and above the band; it does not mean
that more rating is better.
All four scales stay at 0–2000; this display range is not a technical cap.
Above-range values retain their numbers plus >; bands show Band >2000.
A separate DR label with its own tooltip, but no bar marker, shows the user-supplied first diminishing-return
guides: Crit 1380, Haste 1320, Mastery 1380, Versatility 1620. They appear only on
level-90 Retail interface 120100 and are not targets or optimal values. Further
rating still works with less benefit per point; percentage buffs are excluded.
Without a verified target, only a readable own rating remains. All bar graphics
and target labels are hidden. Missing one own stat leaves the others readable.
Targets are cohort median gear ratings with P40–P60 rating endpoints, not
conversions of live percentages. Tooltips show cohort median percentages for
context and warn when combined targets exceed your rating budget. Prio orders stats by top players'
secondary-budget investment, not simulated stat weights.
Mythic+ is the only comparison. Choose Default/Flat dark in the panel.
The +/− sidebar button on CharacterFrame collapses/expands the panel and persists
across reloads. It hides on other Character tabs. Collapsed panels do not read stats
or render rows; expanding refreshes current values. The spec name has no ID suffix.
Reset restores Mythic+, Default, the expanded panel and minimap defaults. German is automatic for deDE; English is the fallback.
The minimap button uses the bundled Stat Compass icon. Drag it to move it. Left-click opens equipment.
Right-click opens Options > AddOns > Stat Compass: choose Default/Flat dark,
show/hide the minimap button, or reset appearance (keeps the collapsed state).
The angle and visibility persist across reloads. No extra feature window or libraries.

The repository Data.lua deliberately contains no target data. Release packages
use generated data from a successful weekly run for the EU top 30 comparison.
Without valid data, readable own ratings remain; targets and bars stay hidden.
The distribution does not guarantee a balanced build or your personal optimum.
The user accepted the Guardian panel screenshot and custom icon locally. This
does not establish all-client, Paladin or performance acceptance or a public release.
