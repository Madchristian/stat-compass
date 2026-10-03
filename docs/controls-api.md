# Minimap and native options

The controls are integrated with the virtual-to-physical panel-coordinate correction preserved. The user accepted the Guardian panel screenshot and custom icon in the local client. This does not establish all-client, Paladin, combat/taint or performance acceptance, or a public release; remaining checks are in `acceptance.md`.

## API binding

All source checks use the repository's pinned Retail 12.1.0 source commit [`09b9db7948abc9b9648dedaab51eb0cf3ee67b31`](https://github.com/Gethe/wow-ui-source/tree/09b9db7948abc9b9648dedaab51eb0cf3ee67b31/Interface/AddOns). Files were fetched and inspected directly for this change; no Blizzard source or artwork is included in the addon ZIP.

Paths below are relative to `Interface/AddOns/` at that commit.

| Source | Contract used | Inspected SHA-256 |
| --- | --- | --- |
| `Blizzard_UIPanels_Game/Mainline/CharacterFrame.lua` | Lines 24-49: `ToggleCharacter(tab, onlyShow)`; `ToggleCharacter("PaperDollFrame", true)` selects equipment and opens it without closing an already-open equipment page. | `6f747e421a44207dc731c4bd0e2f1e0cf9085dd7d96b6c6291c4a84ee0014984` |
| `Blizzard_Settings_Shared/Blizzard_Settings.lua` | Lines 133-162: `RegisterCanvasLayoutCategory(frame,name)`, `RegisterAddOnCategory(category)`, `OpenToCategory(category:GetID())`. | `3ce23f05b171c12a1a3a71596892def5bc0ee7153bedabc00d153f306d1d85a6` |
| `Blizzard_Settings_Shared/Blizzard_SettingsInbound.lua` | Canvas registration is passed through SettingsInbound; registration does not require opening the gameplay panel. | `76199e42d6ef45077b79f3cca236d05ed4720aca5c357bb6bafa5134371240cd` |
| `Blizzard_Settings_Shared/Blizzard_SettingsPanel.lua` | `ClearCurrentCategoryCanvas` detaches, clears anchors and hides the old canvas; `DisplayLayout` parents, fills and shows the selected canvas. No custom closing/scale/dragging is added to this canvas. | `11835d2b8ff1b7e00e7eb6f9f1c56c82a47c6a9ad6beb03efbcd978691d1b7c5` |
| `Blizzard_APIDocumentationGenerated/SimpleTextureBaseAPIDocumentation.lua` | Texture `SetMask(file)` at line 461. No `SetMaskTexture` call on a Texture. | `ea4bc1fe42c961a5449c3ae9e629cd95ff2f6298a90da534c638241b8a1cd417` |
| `Blizzard_APIDocumentationGenerated/SimpleButtonAPIDocumentation.lua` | `RegisterForClicks` accepts ClickButton values, single release edge per mouse button. | `71bfd49d2a2425d2b36ee8d629c8b69ea664348b28b6aada575db5a5bd444449` |
| `Blizzard_APIDocumentationGenerated/SimpleFrameAPIDocumentation.lua` | `GetEffectiveScale`, `RegisterForDrag` with MouseButton values. | `76fd146d432cb7ad8bc9d8ae034e29e54cd9d06f4de33c2c321874ecab0cea42` |
| `Blizzard_APIDocumentationGenerated/SimpleScriptRegionAPIDocumentation.lua` | `GetCenter` returns UI coordinates and may return nothing; geometry can be secret. | `cd4dc47781b8b77f088ebe7aa4aead4d34fee3ce3d679a1a950b3fc1a21fa5c9` |
| `Blizzard_APIDocumentationGenerated/InputDocumentation.lua` | Global `GetCursorPosition()` returns `posX, posY`. | `1eb7a8c921e1a52a7fb8a2928b5ba01a15306f093dc549ba543ca1ac4d1e628a` |

## UX and persistence

- One 32x32 minimap button uses the bundled custom `StatCompass/icon.tga` through `Interface\AddOns\StatCompass\icon`, with a client-runtime portrait mask, tracking border and zoom highlight. No third-party libraries are required.
- Left-click opens Character equipment; right-click opens the native Stat Compass AddOns category. The English/German tooltip also explains dragging.
- Native canvas: existing Default/Flat dark skin choice, minimap visibility, and appearance reset. Settings apply immediately. The inline controls remain available and use the same store.
- Appearance reset restores Default, visible minimap and angle 225, preserving the collapsed state. The inline reset additionally expands the panel. Both retain the Mythic+-only comparison.
- `StatCompassDB` is normalized at the addon's own `ADDON_LOADED`, with a login fallback. TOC execution reads defaults but does not replace SavedVariables. Minimap/canvas creation is idempotent and occurs only at initialization, never merely because an unrelated addon loaded.
- Persist only a validated finite normalized `minimapAngle` and boolean `minimapShown`, alongside `mode`, `skin` and the sanitized boolean `collapsed`. All setters preserve the other validated fields.
- Radius follows actual minimap/button geometry: 86 for 140x140 map plus 32x32 button, 106 for 180x180. Invalid/nonpositive dimensions use positive fallbacks. Cursor positions are divided by effective minimap scale. Invalid/secret center/cursor/scale values do not change persistence. Exact-center dragging keeps the previous angle.
- `OnUpdate` exists only while dragging. Drag stop, icon hide and ancestor hide remove it. Resize and show callbacks reposition the button without polling.
- No credential fields, network requests or new comparison data. The existing honest no-data notice also appears in native Options.

The launcher and TOC use the custom icon, not the earlier map-icon candidate. The PNG artwork remains in `assets/icon/` for repository presentation; the runtime package includes `StatCompass/icon.tga`.

## Integration and limits

`Controls.lua` is loaded after `UI.lua` in the TOC and included in the exact eleven-file package inventory (including `StatCompass/icon.tga`). Integration applied only the initialization event hunks to the current `UI.lua`; the virtual-coordinate geometry code was not replaced. The existing physical-screen mock and all prior tests were retained. Core changes extend the existing store rather than maintaining a second database. Combined tests additionally exercise native category creation before lazy Character-frame loading, both own-ADDON_LOADED and login initialization, authoritative post-TOC SavedVariables, and launcher-to-panel rendering at 1080/1440/2160 physical heights.

Tests run production Lua through `lupa.lua51`, not a newer backend. The widget harness records native Settings reparent/show lifecycle, mask ownership, clicks, geometry and drag callbacks. It does not verify Blizzard glyph metrics, custom icon rendering on other clients, actual mouse drag delivery, combat taint, third-party square minimap layouts, or the separate invisible-panel fix. Real-client checks remain in `acceptance.md`. The circular launcher follows the inscribed map radius; special square-map corner layouts are outside this minimal control.
