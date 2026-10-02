> **Erratum, 2026-10-02:** The preserved research below incorrectly states that Raider.IO has no published EU specialization player leaderboard endpoint. The [official Swagger](https://raider.io/swagger.json) publishes GET /api/v1/client/character-rivals?region=eu&realm={realm}&name={name}&scope=region&specId={specId}. The operation describes a spec leaderboard window, not an active-spec filter. A bounded Arcane replay covered ranks 1–52; ranks 15, 38, 40 and 49 in the first 50 are anonymous. This is an interval collection, not an atomic snapshot, and it cannot supply 50 public identities. See [acquisition notes](rio-acquisition.md). The historical text is retained below for audit.

# Stat Compass – Quellenprüfung Top 50 EU je Spezialisierung

Recherche im Auftrag der Implementierung, 02.10.2026 (Sitzungsdatum). Keine Repository-/GitHub-Änderungen, keine OAuth-App angelegt, keine Zugangsdaten verwendet. Keine Spieler-Datensätze oder Platzhalter erzeugt. Dies ist eine technische Rechte-/Provenienzprüfung, keine Rechtsberatung.

## Ergebnis für die Implementierung

- **Echte Top 50 EU je Spec sind gegenwärtig NICHT end-to-end verifiziert.** Nicht mit einer globalen Top-50-Liste, bloßen Top-Runs, Gildenprogress oder aktuell eingeloggter Spec gleichsetzen.
- **Raider.IO:** dokumentierte öffentliche API erlaubt Community-Nutzung, aber derzeit KEIN veröffentlichter M+-Spielerranglisten-Endpunkt mit Spec-Filter. `/mythic-plus/runs` ist eine Laufrangliste, kein vollständiges Spec-Season-Ranking. Nicht den internen Website-Endpunkt als öffentliche API erfinden.
- **Blizzard:** geeignet für Charakterstatistiken, Equipment, aktuelle Spec und Status-/Löschprüfung. Liefert hier keine fertige EU-Top-50-je-Spec-Rangliste und keinen garantiert passenden Loadout-Snapshot zum historischen Run/Kill. Nutzung und Anzeige an Endnutzer unter API-Bedingungen ausdrücklich möglich; Maximal-TTL/Statusvalidierung ist release-relevant.
- **Warcraft Logs v2:** technisch bester Kandidat für Raid-Rangliste plus zugehörigen Kampfsnapshot. EU-, Klassen-, Spec-, Difficulty-, Partition- und Metric-Filter sind in der offiziellen GraphQL-Dokumentation nachweisbar. **Rechteblocker:** veröffentlichte API-Bedingungen beschränken permanente Kopien und wesentlich unveränderte Anzeige in Ingame-Addons ausdrücklich. Kein grünes Licht für eingebettete Ranglisten/Stat-Seed-Dateien ohne passende schriftliche Erlaubnis. Volltext-Livezugriff war Cloudflare-blockiert; relevante Passagen wurden im Suchindex der offiziellen Betreiberseiten bestätigt, nicht als vollständig live gelesene Bedingungen ausgegeben.
- **Murlok:** ausdrücklich Top 50 über US/EU/KR/TW; EU herausfiltern ergibt NICHT EU Top 50. Außerdem keine Raid-Quelle im geprüften Moduskatalog, keine öffentliche Daten-Redistributionslizenz gefunden.
- **4000 Tempowertung:** derzeit weder als allgemein unmöglich noch als nachgewiesen erreichbar belegt. Kein fixer Ausschlussgrenzwert. Aktueller EU-Live-Build wurde als **12.1.0.69933** direkt in Blizzards Versionsmanifest gesehen. Eine absolute Obergrenze bräuchte eine vollständige, build-/level-/zustandsgebundene Herleitung.

## Belegstatus

**D** = direkt vom Betreiber jetzt gelesen, **I** = Suchindexauszug der offiziellen Betreiber-Dokumentation (Live-Fetch blockiert), **E** = Empfehlung/Schlussfolgerung, **O** = offen/nicht durch authentifizierte Antwort geprüft.

### 1. Raider.IO [D]

Offizielle Dokumentation: https://raider.io/api
Maschinenlesbare Specs: https://raider.io/swagger.json und https://raider.io/openapi.json
Gelesen: swagger.json, Version 0.62.5. API-Seite bindet diese Datei ausdrücklich ein.
Bedingungen: https://raider.io/terms-of-use (Last updated July 1st, 2025).

Verifizierte GET-Endpunkte:

- `https://raider.io/api/v1/mythic-plus/runs?season={seasonSlug}&region=eu&dungeon=all&affixes=all&page=0`
  - erlaubte Parameter: `access_key` optional, `season`, `region`, `dungeon`, `affixes`, `page`.
  - Beschreibung: "Retrieve information about the top runs that match the given criteria".
  - Kein `spec`, `spec_id`, `class` oder vergleichbarer Spec-Filter in der veröffentlichten Operation. Im gesamten geprüften M+-Pfadkatalog kein Spec-Queryparameter.
  - Dokumentiertes Paging: standardmäßig 100 Seiten, mit Access-Key bis 1000; Seite beginnt bei 0. Daher selbst ein Crawl dieser Läufe kein Vollständigkeitsbeweis für alle Specs.
  - Dokumentationsdefault zur Recherche: `season-mn-2`; Produktion muss Season über Metadaten bestimmen, nicht diesen zeitabhängigen Wert dauerhaft fest einbauen.
- `https://raider.io/api/v1/mythic-plus/run-details?season={seasonSlug}&id={runId}` – Details eines konkreten Laufs.
- `https://raider.io/api/v1/mythic-plus/static-data` – Metadaten für Season/Dungeons.
- `https://raider.io/api/v1/characters/profile?region=eu&realm={realm}&name={name}&fields=gear,talents,mythic_plus_scores_by_season:current,mythic_plus_ranks,mythic_plus_best_runs:all`
  - dokumentierte Felder: `gear`, `talents`, `talents:categorized`, Saison-Scores, Charakterränge, best/recent/highest runs, Raidprogress.
  - Ränge/Scores eines BEREITS BEKANNTEN Charakters sind keine enumerierbare Top-50-Spec-Liste. Aktuelle Talente beweisen keine Spec-Nutzung in den gewerteten Läufen.
- `https://raider.io/api/v1/raiding/raid-rankings?raid={raidSlug}&difficulty=mythic&region=eu&limit=50&page=0`
  - API erlaubt `guilds` als Einschränkung und liefert Gildenprogressranglisten, keine individuellen DPS/HPS-/Spec-Ränge.
- `https://raider.io/api/v1/raiding/boss-rankings?raid={raidSlug}&boss={bossSlug}&difficulty=mythic&region=eu` – Bossprogress, ebenfalls kein Spieler-Spec-Performance-Ranking.

**Berechtigung/Ratelimits [D]:** API-Beschreibung: Community/personal use; öffentliche Anwendungen müssen auf https://raider.io verlinken. Kein Aufbau konkurrierender Services, kein Weiterverkauf, kein schädigender Gebrauch. "Automated scraping beyond the published endpoints is prohibited." Kommerzielle Nutzung/Enterprise-Limits über hello@raider.io klären. Unauthentifizierte Nutzung möglich; `access_key` optional für höhere Limits, Registrierung unter https://raider.io/settings/apps. Bei HTTP 429 `Retry-After` (Sekunden) und `X-RateLimit-*` beachten; keinen ausgedachten festen Gratis-RPS-Wert verwenden.

Website-ToS erlauben automatisierten Zugriff explizit als Ausnahme für die öffentliche API; dies ist KEINE Erlaubnis für interne Website-Rankingrouten/HTML-Crawls. API-Nutzung in einer Community-App ist grundsätzlich vorgesehen; ein dauerhaft öffentlich weiterverteilter Datenbank-/Seed-Export und die Grenze zu einem konkurrierenden Build-Service sind damit nicht pauschal freigegeben [E/O]. Für benötigte Spec-Rangliste und konkrete Cache/Derivat/Addon-Verteilung Betreiberfreigabe bzw. offiziellen erweiterten Feed einholen.

**M+-Metrikempfehlung [E]:** saisonaler, tatsächlich mit der Spec erzielter M+-Score, EU, identischer Season-/Zeitstichtag, eindeutige Charaktere. Wenn nur Gesamt-/Rollen-Score und aktuelle Spec vorhanden sind, ehrlich "Charaktere nach Gesamt-/Rollen-Score mit aktuell aktiver Spec" nennen, NICHT Spec-Top-50. Höchster Key oder einzelne schnellste Runs sind andere Ranglisten. Selbst aus Run-Teilnehmern berechnete Scores brauchen nachweislich vollständige relevante Runs und eine offengelegte Scoredefinition; sonst nur "Top 50 der erfassten Stichprobe".

### 2. Blizzard Profile/Game Data APIs [D]

Offizielle Seiten:
- https://develop.battle.net/documentation/world-of-warcraft/profile-apis
- https://develop.battle.net/documentation/world-of-warcraft/game-data-apis
- https://develop.battle.net/documentation/guides/using-oauth/client-credentials-flow
- https://develop.battle.net/documentation/guides/getting-started

Zusätzlich die vom offiziellen Portal selbst geladenen Dokumentations-JSONs direkt gelesen:
- https://community.developer.battle.net/api/pages/content/documentation/world-of-warcraft/profile-apis.json
- https://community.developer.battle.net/api/pages/content/documentation/world-of-warcraft/game-data-apis.json
- https://community.developer.battle.net/api/pages/content/documentation/guides/using-oauth/client-credentials-flow.json
- https://community.developer.battle.net/api/pages/content/documentation/guides/getting-started.json

Öffentliche Charakterendpunkte (jeweils GET, Basis `https://eu.api.blizzard.com`, `namespace=profile-eu`, optional `locale=de_DE`, Bearer-Token):

```
/profile/wow/character/{realmSlug}/{characterName}
/profile/wow/character/{realmSlug}/{characterName}/statistics
/profile/wow/character/{realmSlug}/{characterName}/equipment
/profile/wow/character/{realmSlug}/{characterName}/specializations
/profile/wow/character/{realmSlug}/{characterName}/status
/profile/wow/character/{realmSlug}/{characterName}/mythic-keystone-profile
/profile/wow/character/{realmSlug}/{characterName}/mythic-keystone-profile/season/{seasonId}
```

`characterName` laut Referenz kleingeschrieben, Realm als Slug. Stats-Summary ist NICHT `/achievements/statistics`.

Zugriff: Battle.net-Entwickleraccount und registrierter Client mit Client-ID/Secret; Getting Started fordert angehängten Authenticator/2FA. Token mit `POST https://oauth.battle.net/token`, `grant_type=client_credentials`, HTTP Basic aus Client-ID/Secret. Diese öffentlichen Charakterressourcen erfordern NICHT den persönlichen Login jedes analysierten Spielers. Geschützte `/profile/user/wow`-Ressourcen dagegen Authorization Code Flow mit `wow.profile` – für diese Aufgabe unnötig. Nichts registriert oder authentifiziert.

Die Referenz bestätigt Endpunktzwecke, aber keine hier authentifiziert beobachtete aktuelle Antwort mit allen Rating-/Talent-Unterfeldern. Vor Umsetzung Parser gegen echte Antworten testen [O]; Namen wie haste.rating/mastery.value nicht ohne Antwortvertrag als bewiesen festschreiben. Profil/Statistik/Equipment/Spec sind separate, nicht transaktionale Antworten. Downloadzeit ist nicht Ausrüstungs-/Runzeit. Eine historische Raid-Rangliste mit später abgefragten Blizzard-Werten ist nur "heutiges Profil der gerankten Charaktere", nicht "Werte beim Kill".

**Blizzard-M+-Alternative [D/E]:**

```
GET /data/wow/connected-realm/{connectedRealmId}/mythic-leaderboard/index
GET /data/wow/connected-realm/{connectedRealmId}/mythic-leaderboard/{dungeonId}/period/{period}
GET /data/wow/mythic-keystone/season/index
GET /data/wow/mythic-keystone/season/{seasonId}
GET /data/wow/mythic-keystone/period/index
```

Mit `namespace=dynamic-eu`. Dies sind wöchentliche, Connected-Realm-/Dungeon-bezogene Run-Leaderboards, keine direkte EU-Spec-Seasonliste. Eigenaggregation ist technisch denkbar, aber Spec-Abdeckung, Teilnehmerdaten, Trunkierung/Vollständigkeit und Score-Rekonstruktion müssen mit echten Antworten bewiesen werden; derzeit kein belastbarer Ersatz für garantierte Top 50 EU.

**Rechte [D]:** https://www.blizzard.com/legal/a2989b50-5f16-43b1-abec-2ae17cc09dd6/blizzard-developer-api-terms-of-use
- beschränkte widerrufliche Lizenz für registrierte Anwendungen; ausdrücklich "distribute the Data to end users for their personal use via Your Application".
- kein Verkauf/Lizenzieren der Daten an Dritte; keine Werbe-/Datenbrokerweitergabe, auch nicht anonymisiert/aggregiert/abgeleitet.
- keine Premiumversionen mit zusätzlichen bezahlten Funktionen laut API-Bedingungen; keine Gebühren für Datenzugang.
- Blizzard deutlich als Datenquelle nennen, keine Billigung/Affiliation suggerieren; Geheimnisse vertraulich halten.
- maximal 30 Tage TTL für API-Daten; rechtzeitige Erneuerung oder für WoW Statusvalidierung. Kein unbegrenzt gültiger Seed in einem Archiv/Release.
- `/status` beschreibt ausdrücklich Löschen bei 404, `is_valid=false` ODER Charakter-ID ungleich gespeicherter ID. Erfolgreiche normale Profilantwort ersetzt nicht die statusbasierte Prüfung aller Charakterdaten.
- Limit aktuell dokumentiert: 36.000 Requests/Stunde, 100/Sekunde. 429/Fehler behandeln, Limits nicht durch Dritte umgehen.
- Bei Kündigung/Sperre Nutzung beenden und Kopien löschen.

Ergänzende offizielle Erklärung: https://us.forums.blizzard.com/en/blizzard/t/data-protection-notice-and-faq/609 (älter, direkte Betreiber-FAQ). Anonymisieren wird darin ausdrücklich nicht als genereller Ersatz der 30-Tage-Regel gebilligt. Produktentscheidung: generierte Addondaten brauchen Ablauf-/Erneuerungs-/Löschkonzept, nicht nur einen Hinweis "veraltet".

### 3. Warcraft Logs / RPGLogs / Archon [I; Livezugriff blockiert]

Primär-URLs:
- https://www.warcraftlogs.com/api/docs
- https://www.archon.gg/wow/articles/help/api-documentation (Indexdatum 02.12.2025)
- https://www.warcraftlogs.com/v2-api-docs/warcraft/encounter.doc.html
- https://www.warcraftlogs.com/v2-api-docs/warcraft/character.doc.html
- https://www.warcraftlogs.com/v2-api-docs/warcraft/report.doc.html
- https://www.warcraftlogs.com/v2-api-docs/warcraft/characterrankingmetrictype.doc.html
- https://www.archon.gg/wow/articles/help/rpg-logs-api-terms-of-service (Indexdatum 28.04.2025)

Transparenz: direkte HTTP- und Browserabrufe lieferten Cloudflare/403. Offizielle Dokumentationsauszüge einschließlich vollständiger GraphQL-Signaturen waren im Web-Suchindex zugänglich. Sie sind verifizierte veröffentlichte Doku, aber kein heutiger authentifizierter API-Test und kein vollständig live gelesenes Rechtsdokument. Archivsuche fand Encounter-Doku von 2022; diese wurde bewusst NICHT als aktueller Beleg benutzt.

**API:** öffentliche GraphQL-API `POST https://www.warcraftlogs.com/api/v2/client`, OAuth Client Credentials (Client-ID, Client-Secret -> Bearer-Token). Private, autorisierte Nutzerdaten über `/api/v2/user`, nicht für öffentliche Toplisten erforderlich. Keine OAuth-Apps/Secrets verwendet. V1 ist als veraltet dokumentiert.

Dokumentierter Ranking-Einstieg:

```
worldData {
  encounter(id: ENCOUNTER_ID) {
    characterRankings(
      difficulty: DIFFICULTY_ID,
      partition: PARTITION_ID,
      serverRegion: "EU",
      className: "CLASS_SLUG",
      specName: "SPEC_SLUG",
      metric: dps,
      page: 1,
      includeCombatantInfo: true
    )
  }
}
```

Dies ist ein Dokumentationsmuster, KEIN ausgeführter Request. IDs/Slugs/Regiontoken-Großschreibung gegen Metadaten/echte Antwort validieren. Signatur bestätigt `bracket`, `difficulty`, `filter`, `page`, `partition`, `serverRegion`, `serverSlug`, `size`, `leaderboard`, `hardModeLevel`, `metric`, `includeCombatantInfo`, `includeOtherPlayers`, `className`, `specName`, `externalBuffs`, historische Covenant/Soulbind-Filter. Region allein filtert die gesamte Region. Rückgabe ist `JSON`, ausdrücklich nicht eingefroren/stabil garantiert. Nicht `size=50` zur Datensatzanzahl verwenden: `size` ist Raidgröße; für Top 50 paginieren, Charaktere deduplizieren, dann schneiden.

Passende Logdetails:

```
reportData {
  report(code: REPORT_CODE) {
    playerDetails(fightIDs: [FIGHT_ID], includeCombatantInfo: true)
    events(fightIDs: [FIGHT_ID], dataType: CombatantInfo) {
      data
    }
  }
}
```

`playerDetails` dokumentiert Spec/Talente/Gear; `includeCombatantInfo` zusätzliche Kampfinformationen/Gear. Events sind paginiert; `Report.events` liefert `ReportEventPaginator`. Die Betreiberforen erklären CombatantInfo als Snapshot zu Encounterbeginn mit Stats/Gear/Spec/Talenten: https://forums.combatlogforums.com/t/api-v2-info-documentation/9975?page=2 . Diese Erklärung ist älter; ob aktuelle 12.1-Logs alle gewünschten Rohwerte vollständig liefern, ist OFFEN. Nicht fehlende Ratings aus allgemeinen DPS-/HPS-Rangdaten erfinden. `reportCode + fightID + actorID + Zeit/Build` als Snapshotidentität; aktuelles Armory-Profil nicht stillschweigend unter diesen Snapshot mischen.

**Metriken [I/E]:** Enum belegt `dps`, `hps`, `bossdps`, `wdps`, `playerscore` (WoW Mythic dungeons), `playerspeed`; `krsi` veraltet/nur ältere WoW-Zonen. `rdps/ndps/cdps` laut Enum FFXIV-spezifisch, NICHT pauschal WoW-Augmentation-Lösung.
- Raid zunächst bossbezogen, Mythic getrennt von Heroic, aktuelle Partition/Patch, gleiche Spec. DPS für DD, HPS für Heiler als klar benannter Leistungsindikator, nicht universeller Spielerskill. Tank-DPS misst keinen Überlebensskill; Tankrangliste so kennzeichnen, nicht alte KRSI erfinden.
- Tierweite "Top 50" braucht eigene transparente bossnormalisierte Aggregation, Mindestabdeckung und Gleichstandsregel. Durchschnitte roher DPS über verschiedene Bosse sind ungeeignet. Character.zoneRankings eines bekannten Charakters ist nicht automatisch ein global enumerierbarer Zoneleaderboard-Endpoint.
- M+ via WCL `playerscore`/Log-Leaderboards ist eine mögliche andere Population/Metrik. Nicht Raider.IO-Saisonscore oder vollständige EU-Population behaupten. Abdeckung und Rückgabesemantik müssten authentifiziert verifiziert werden.

**Rechteblocker [I]:** Offizielle API-ToS enthalten (Suchindex, auch identische Betreiberartikel unter /classic-mop und /classic-sod):
> Unless expressly permitted by the content owner or by applicable law ...
> Scrape, build databases, or otherwise create permanent copies ... or keep cached copies longer than permitted by the cache header;
> Present content substantially unchanged through a new channel, including ... in-game add-ons ...

Weitere offizielle Indexauszüge: kommerzielle Nutzung (auch Ads/Subscriptions) braucht vorherige Genehmigung über advertising@archon.gg; Attribution nach Doku; nach Ende Kopien löschen. Derivations-/Distributionsbeschränkungen sind ebenfalls indiziert. Eine Statistik aus Logs zu mitteln ist NICHT automatisch eine Lizenzumgehung. **Vor Addonexport, periodischem Cache, öffentlichem Seed und Verteilung schriftlich genauen Zweck/Transformation/Dauer/Attribution genehmigen lassen.** Kein Rechts-Go allein weil Token zugänglich ist.

### 4. Murlok [D]

https://murlok.io/
https://murlok.io/mage/fire/mm+

Seite sagt ausdrücklich: "top 50 Fire Mage DPS across the US, EU, KR, and TW regions", Refresh alle acht Stunden via Blizzard API, Patch 12.1/Midnight Season 2. Geprüfter Moduskatalog: Solo/2v2/3v3/Blitz/RBG/M+; kein Raid. Footer "All rights reserved". Keine öffentliche Datenlizenz/API für unseren Bulk-/Seed-Zweck bestätigt. Nur als Markt-/Semantikbeleg untersucht, keine Tabellen kopiert/weiterverteilt. EU-Filter auf diese globale Kohorte würde europäische Ränge außerhalb der globalen 50 fehlen lassen. Hero-Talent-Filter ist außerdem nicht zwingend exakte Talentbuild-Gleichheit.

## 4000 Haste, Statkonsistenz und Mastery

**Build [D]:** Blizzards eigenes öffentliches Versionsmanifest `http://us.patch.battle.net:1119/wow/versions` lieferte EU `12.1.0.69933`. Dieser Patchservice spricht hier HTTP; der HTTPS-Versuch scheiterte protokollbedingt. https://wago.tools/api/builds ist eine sekundäre Metadatenquelle, nicht Quelle einer maximalen Statobergrenze.

**Antwort:** Aus einem isolierten Wert 4000 keine Unmöglichkeit ableiten. Heute/12.1, Charakterlevel, Roh-Rating vs Prozent, PvE/PvP/Scaling, temporäre Effekte, passive Talente, Rasse, Equipmentstand und alte Expansionsdaten müssen bekannt sein. Gear-/Level-Squish macht alte Grenzwerte besonders unbrauchbar. In dieser Recherche wurde weder ein vollständiger legaler maximaler 12.1-Haste-Loadout noch ein echter Charakter-/Logsnapshot mit 4000 geprüft. Eine Behauptung "unmöglich" wäre daher erfunden.

**Sinnvolle Validatoren [E]:**
1. Herkunft, Abrufzeit UND Beobachtungszeit, Region/Charakter-ID, Season, Spec-ID, Level, Build/Partition und Rohdatenvertrag verpflichtend. "Build unbekannt" ist nicht "Build stimmt".
2. Nur endliche Zahlen, erwartete Einheit/Typ, Rating nicht mit Prozent/DPS verwechseln; fehlend/gesperrt/unlesbar von 0 trennen.
3. Vollständige Equipmentvarianten inklusive Itemlevel, Bonus-IDs, Gems, Enchants und temporärer Zustände soweit verfügbar. Nicht Item-ID allein. Gleicher Charakter/Spec/Zeitbezug aller Quellen, große zeitliche Abstände ausschließen/kennzeichnen.
4. Rekonstruktion aus Gear nur mit bestätigter semantischer Abdeckung, ohne Doppelzählung von Gem-/Enchant-Stats. Unbekannte Procs, Buffs, Passives oder Scaling ergeben "nicht vollständig prüfbar", nicht "falsch".
5. Rating->Prozent nur mit build-/levelgebundenen Umrechnungen, Diminishing Returns, passiven und multiplikativen Effekten; keine lineare universelle Division. Gleichzeitiger Client-Gegentest out of combat/ohne Procs ist eine stärkere Referenz als mehrere Armoryabfragen.
6. Robuste Kohorten-Ausreißerprüfung (Median/Quantile bzw. MAD) ist Warnung, kein physikalischer Unmöglichkeitsnachweis. Nicht auf 50 auffüllen, wenn nur weniger qualifizierte Datensätze bleiben. Populationsgröße und Ausschlussgründe zeigen; Aussortieren eines Top-50-Spielers darf nicht heimlich Top 51 als weiterhin exakt Top 50 ausgeben.
7. Kein Statmittel als persönliches Optimum/Statgewicht verkaufen. Kohortenstatistik beschreibt erfolgreiche beobachtete Ausrüstung, nicht kausale Verbesserung für den eigenen Charakter.

**Mastery [direkt gelesener Blizzard-UI-Code in Communitymirror; nicht offizieller Hostingdienst]:**
https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_UIPanels_Game/Mainline/PaperDollFrame.lua
https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/PaperDollInfoDocumentation.lua

Gelesener PaperDoll-Code: `PaperDollFrame_SetMastery` zeigt `GetMasteryEffect()`; Tooltip holt `mastery, bonusCoeff = GetMasteryEffect()`, `GetSecondaryBonus(CR_MASTERY, mastery, bonusCoeff)` und getrennt `GetCombatRating(CR_MASTERY)`; Spezialisierung liefert Masteryspells. Haste zeigt `GetHaste()` und getrennt `GetCombatRating(CR_HASTE_MELEE)`. Daraus folgt: Roh-Mastery-Rating, Masterypunkte und specspezifischer Effekt-/Tooltip-Prozentwert sind verschiedene Größen. Einen Web-`mastery.value`-Wert NICHT ungeprüft mit Charakterfenster-Effektprozent vergleichen oder specsübergreifend mitteln. Gleichnamige Ratingwerte machen Effektwerte nicht vergleichbar. Datenmodell sollte `rating`, `percent/effect`, `semanticKind`, `specId`, `level`, `build`, `source` auseinanderhalten. Prozentwert bei ungeklärter APIsemantik lieber "nicht vergleichbar".

"Entsprechende Skillung" wird hier als Spezialisierung interpretiert. Exakter Talentbuild ist eine zusätzliche Auswahl über Klasse-/Spec-/Hero-Talente, Ränge/Choices und versionsgebundene Baumdefinition. Gleiche Spec oder gleicher Hero-Baum garantiert keinen gleichen Build. Noch kein Beleg für 50 EU-Spieler je exaktem Talentbuild; diese strengere Kohorte nicht versprechen.

## Entscheidungsvorlage / nächste Gates (keine Aktion ausgeführt)

1. Addon/Provider-Interface darf vorbereitet werden, aber keine Demo-/Fakekohorte als echte Werte. Status "Quelle/Datensatz noch nicht verifiziert".
2. M+: offiziell erlaubten, vollständigen EU-Spec-Rankingfeed von Raider.IO klären; sonst WCL/Blizzard-Eigenaggregation explizit als anderes/noch unbewiesenes Produkt.
3. Raid: WCL-Bedingungen vollständig prüfen und ausdrückliche Erlaubnis für Aggregation + Addoncache/-verteilung; dann eigener OAuth-Client und kleiner echter EU-Spec-Query/CombatantInfo-Probe. Kein Profilersatz als Kill-Snapshot.
4. Blizzardprofil kann legale ergänzende aktuelle Statistikquelle sein, wenn registrierte App, Attribution, vertrauliche Credentials und TTL/Statuslöschung umgesetzt werden. Kein Secret im Lua/ZIP.
5. Quelle vollständig bis 50 eindeutige, qualifizierte Charaktere erheben; Rankingsnapshot und Beobachtungs-/Statistik-Snapshot getrennt versionieren. Coverage/Qualitätsstatus anzeigen und beim Scheitern keine Vollständigkeit behaupten.

Recherchegrenzen: WCL/Archon Cloudflare; Blizzard/WCL authentifizierte Nutzdaten ausdrücklich nicht abgerufen; keine Anbieterfreigabe erteilt; kein aktuelles Rating-Maximum hergeleitet. Sämtliche Empfehlungen sind davon getrennt gekennzeichnet.
