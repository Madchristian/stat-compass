# Stat Compass: Changelog / Änderungsverlauf

This file contains the complete public release history. Every version is listed once, English first, then German.

Diese Datei enthält die vollständige öffentliche Release-Historie. Jede Version steht genau einmal, zuerst Englisch, danach Deutsch.

## 2026.10.28

### English

#### Data update

The comparison values now come from the Mythic+ leaderboards up to week 1087 of season 18. 40 specializations and 56 hero talent trees have their own top-player data. This data stays valid until 2026-11-27.

### Deutsch

#### Datenaktualisierung

Die Vergleichswerte stammen jetzt aus den Mythic+-Bestenlisten bis Woche 1087 der Saison 18. 40 Spezialisierungen und 56 Heldentalente haben eigene Daten der Top-Spieler. Die Daten gelten bis 2026-11-27.

---

## 2026.10.21

### English

#### Data update

The comparison values now come from the Mythic+ leaderboards up to week 1086 of season 18. 40 specializations and 56 hero talent trees have their own top-player data. This data stays valid until 2026-11-20.

### Deutsch

#### Datenaktualisierung

Die Vergleichswerte stammen jetzt aus den Mythic+-Bestenlisten bis Woche 1086 der Saison 18. 40 Spezialisierungen und 56 Heldentalente haben eigene Daten der Top-Spieler. Die Daten gelten bis 2026-11-20.

---

## 2026.10.18

### English

#### Fixed

- Comparison values remain available after WoW updates to a newer build on the same interface version. Previously, such an update could hide all comparison values even while the dataset was still valid. ([#48](https://github.com/Madchristian/stat-compass/pull/48))
- Expired data, different interface versions and clients older than the source build remain unsupported.

### Deutsch

#### Behoben

- Vergleichswerte bleiben nach WoW-Updates mit höherer Buildnummer innerhalb derselben Interface-Version sichtbar. Bisher konnte ein solches Update alle Vergleichswerte ausblenden, obwohl die Daten noch gültig waren. ([#48](https://github.com/Madchristian/stat-compass/pull/48))
- Abgelaufene Daten, abweichende Interface-Versionen und Clients mit älterer Buildnummer bleiben gesperrt.

---

## 2026.10.14-2

### English

#### Data update

The comparison values now come from the Mythic+ leaderboards up to week 1085 of season 18. 40 specializations and 57 hero talent trees have their own top-player data. This data stays valid until 2026-11-13.

### Deutsch

#### Datenaktualisierung

Die Vergleichswerte stammen jetzt aus den Mythic+-Bestenlisten bis Woche 1085 der Saison 18. 40 Spezialisierungen und 57 Heldentalente haben eigene Daten der Top-Spieler. Die Daten gelten bis 2026-11-13.

---

## 2026.10.14

### English

#### Fixed

- Updated the interface version to 120105 for WoW 12.1.5 so the addon is no longer marked as out of date. ([#46](https://github.com/Madchristian/stat-compass/pull/46))

### Deutsch

#### Behoben

- Interface-Version auf 120105 für WoW 12.1.5 aktualisiert, damit das Addon nicht mehr als veraltet angezeigt wird. ([#46](https://github.com/Madchristian/stat-compass/pull/46))

---

## 2026.10.7

### English

#### Data update

The comparison values now come from the Mythic+ leaderboards up to week 1084 of season 18. 40 specializations and 58 hero talent trees have their own top-player data. This data stays valid until 2026-11-06.

### Deutsch

#### Datenaktualisierung

Die Vergleichswerte stammen jetzt aus den Mythic+-Bestenlisten bis Woche 1084 der Saison 18. 40 Spezialisierungen und 58 Heldentalente haben eigene Daten der Top-Spieler. Die Daten gelten bis 2026-11-06.

---

## 2026.10.4

### English

- The minimap button now stays fully outside the map, including its border, with a small gap. This also works with square minimaps and shapes with mixed round and square corners.
- Dragging follows the outer edge. The saved angle is preserved, and the position adjusts when the minimap is resized or scaled.

### Deutsch

- Das Minimap-Symbol sitzt jetzt einschließlich seines Rahmens mit kleinem Abstand vollständig außerhalb der Karte. Das gilt auch für eckige Minimaps und Formen mit runden und eckigen Ecken.
- Beim Ziehen folgt das Symbol dem äußeren Rand. Der gespeicherte Winkel bleibt erhalten; bei Größen- und Skalierungsänderungen passt sich die Position an.

---

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
