# Stat Compass: Changelog / Änderungsverlauf

This file contains the complete public release history. Every version is listed once, English first, then German.

Diese Datei enthält die vollständige öffentliche Release-Historie. Jede Version steht genau einmal, zuerst Englisch, danach Deutsch.

## 2026.10.3-2

### English

- During combat, the panel keeps the last readable values from before combat and labels them "Pre-combat snapshot". Stat Compass does not scan new character stats during combat.
- Validated comparison data is cached. The full dataset is not revalidated during combat; expired or mismatched comparison data stays unavailable.
- When combat ends, the panel immediately refreshes with current values.

### Deutsch

- Im Kampf zeigt das Panel die letzten lesbaren Werte vor Kampfbeginn mit dem Hinweis „Stand vor Kampf“. Während des Kampfes fragt Stat Compass keine neuen Charakterwerte ab.
- Bereits geprüfte Vergleichsdaten werden zwischengespeichert. Im Kampf wird der Datensatz nicht erneut vollständig geprüft; abgelaufene oder nicht mehr passende Vergleichsdaten bleiben gesperrt.
- Nach Kampfende aktualisiert sich das Panel sofort mit den aktuellen Werten.

---

## 2026.10.3

### English

#### First release

Stat Compass compares your secondary stats with the best European Mythic+ players of your specialization, right on the equipment page of your character window.

For Critical Strike, Haste, Mastery and Versatility you see your rating, a target and the range most top players fall into. The comparison uses the 30 best EU players of your specialization in the current Mythic+ season. If your hero talent tree is common enough among them, Stat Compass uses the best players of that hero talent tree instead.

Below the stats, a priority line shows which stats top players put most of their secondary stats into.

The data comes from Blizzard's official APIs and is collected again every week. The addon contains no player names.

There are two skins: Default in WoW style and Flat dark.

The values show how the best players distribute their gear. They come from no simulation, and Stat Compass cannot tell whether that distribution is the best one for your character.

### Deutsch

#### Erste Veröffentlichung

Stat Compass vergleicht auf der Ausrüstungsseite des Charakterfensters deine Sekundärwerte mit den besten Mythic+-Spielern Europas, die deine Spezialisierung spielen.

Für Kritisch, Tempo, Meisterschaft und Vielseitigkeit siehst du deine Wertung, einen Zielwert und den Bereich, in dem die meisten Top-Spieler liegen. Verglichen wird mit den 30 besten EU-Spielern deiner Spezialisierung in der aktuellen Mythic+-Saison. Ist dein Heldentalent unter den Top-Spielern verbreitet genug, nimmt Stat Compass stattdessen die besten Spieler mit diesem Heldentalent.

Darunter zeigt eine Prio-Zeile, in welche Werte die Top-Spieler den größten Teil ihrer Sekundärwerte stecken.

Die Daten kommen aus Blizzards offiziellen Schnittstellen und werden jede Woche neu erhoben. Spielernamen enthält das Addon nicht.

Es gibt zwei Designs: Standard im WoW-Stil und Flach dunkel.

Die Werte zeigen, wie die besten Spieler ihre Ausrüstung verteilen. Eine Simulation steckt nicht dahinter, und ob diese Verteilung für deinen Charakter die beste ist, kann Stat Compass nicht sagen.

---
