# Arbeitsweise für Agenten im Team

Diese Regeln gelten für alle Agenten, die an Stat Compass arbeiten: Codex, Claude und weitere. `CLAUDE.md` bindet diese Datei ein. Was hier steht, hat Vorrang vor eigenen Gewohnheiten. Entscheidungen des Nutzers im Chat haben Vorrang vor dieser Datei. Gehören sie dauerhaft dazu, werden sie hier nachgetragen.

## Rollen und Zuständigkeiten

| Rolle | Zuständig für | Fasst nicht an |
|---|---|---|
| **Daten-Agent** | `tools/` (Provider, Generator, Datenvertrag), der Datenteil von `StatCompass/Core.lua` (Validierung, `GetTarget`, `Snapshot`-Felder), `StatCompass/Data.lua`, `.github/workflows/`, `docs/data-contract.md`, `docs/blizzard-acquisition.md` | Optik in `UI.lua`, `Controls.lua`, `Locales.lua` |
| **UI-Agent** | `StatCompass/UI.lua`, `Controls.lua`, `Locales.lua`, Optik und Layout, UI-Tests, Design-Dokumente in `docs/` | Datenlage, Provider, Datenvertrag, Workflows |
| **Orchestrator / Review** | Planung in Issue #1, Meilensteine, unabhängige Prüfung, Abnahme | Umsetzung, solange ein Agent daran arbeitet |

Berührt eine Aufgabe die Dateien einer anderen Rolle, setzt du sie nicht selbst um. Du legst ein Follow-up-Issue an (siehe unten). Ausnahme: Testerwartungen, die nur wegen deiner eigenen, gewollten Änderung brechen, darfst du in bereits committeten Dateien anpassen. Das begründest du im PR.

## Arbeitsplatz

- **Jeder Agent arbeitet in seinem eigenen Git-Worktree.** Der UI-Agent z. B. unter `C:\Users\Christian\orca\workspaces\stat-compass\UI-optimierungen`. Im Worktree eines anderen Agenten wechselst du nie den Branch und änderst keine Dateien.
- Kurzlebige Hilfs-Worktrees legst du außerhalb des Repos an und entfernst sie nach dem Merge (`git worktree remove`).
- Temporäre Dateien, Rohdaten und Logs liegen im Scratch-Ordner des Agenten, nie im Repo.

## Branches, Commits, Pull Requests

1. **Branch immer frisch von `origin/main`** (`git fetch` vorher). Namen: `feat/…`, `fix/…`, `ci/…`, `docs/…`.
2. **Kleine, thematisch geschlossene PRs.** Ein Thema pro PR.
3. **Vor dem PR:** die volle Testsuite lokal grün (`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`). Neue Funktionen bekommen Tests.
4. **Commit-Nachrichten** erklären das Warum, nicht nur das Was. Agenten schreiben eine Attributionszeile, z. B. `Co-Authored-By: …`.
5. **PR-Beschreibung** enthält: *Why*, *Changes* bzw. *What*, *Test plan* als Checkliste, Messwerte bei Performance- oder Datenänderungen, verknüpfte Issues.
6. **Merge:** Seinen **eigenen** PR mergt der Agent selbst (`gh pr merge --merge`), sobald `Tests` und GitGuardian grün sind. Bei roten Checks nie. PRs anderer Agenten mergst du nur auf ausdrücklichen Auftrag.
7. **Nach dem Merge** prüfst du, ob alle Commits in `main` angekommen sind. Wurde ein PR gemergt, während noch Commits auf seinem Branch lagen, bekommen diese einen neuen PR.
8. Nie Force-Push auf `main`, nie `--no-verify`. Unveröffentlichte eigene Commits dürfen per `--amend` korrigiert werden, z. B. eine falsche Commit-Nachricht.

## Übergaben zwischen Agenten: Follow-up-Issues

Übergaben gehen **nicht** als Text in den Chat, sondern als GitHub-Issue. Alle Agenten lesen GitHub mit.

- **Meilenstein:** Das Issue kommt in den passenden Meilenstein (UI-Arbeit → *M3 - Kompaktes UI und zwei Skins*, Daten → *M1*, Kern → *M2*, Abnahme und Releases → *M4*), Label `enhancement` bzw. `bug`.
- **Erst suchen:** Gibt es schon ein passendes Issue, ergänze dort per Kommentar, statt ein Duplikat anzulegen.
- **Aufbau:**
  - **Hintergrund:** Entscheidung des Nutzers mit Datum, Grund.
  - **Datenvertrag:** Felder mit Beispielwerten, Verweis auf den PR, der sie liefert.
  - **Aufgaben:** Checkliste mit konkreten Dateien und Stellen.
  - **Abnahme:** prüfbare Kriterien, z. B. Tests und Gegenprobe im Spiel.
- Dem Nutzer schreibst du nur den Link und einen Satz.

## Issues und Meilensteine pflegen

- **Fortschritt:** Erreichte Kriterien in der Issue-Beschreibung abhaken, jeweils mit kurzer Begründung.
- **Nachweise als Kommentar:** PR-Links, Workflow-Läufe, Messwerte, Testanzahl.
- **Schließen** nur, wenn alle Abnahmekriterien mit überprüfbarem Nachweis erfüllt sind, und zwar mit Abschluss-Kommentar. Offene Reste wandern mit Verweis in ein anderes Issue.
- **Nutzerentscheidungen**, die ein Kriterium ändern (z. B. „30 statt 50“, „kein Raid“), mit Datum ins Issue übernehmen.
- **Meilenstein-Titel und -Beschreibung** aktuell halten. Issue #1 ist die Gesamtübersicht.
- **Ehrlich bleiben:** Blocker, fehlende Rechte oder Zugänge als Blocker benennen. Nichts als erledigt melden, was nicht nachgewiesen ist.

## Datenvertrag und gemeinsame Schnittstellen

- Die Schnittstelle zwischen Daten und UI ist `snapshot` aus `A.Snapshot()` mit `target`, `ratingComparison`, `shareComparison`, `ratingTarget` und weiteren Feldern. Beschrieben ist sie in `docs/data-contract.md`.
- Änderungen sind **additiv**: neue Felder ja, bestehende umbenennen oder entfernen nur mit Follow-up-Issue für die andere Rolle.
- Jede Vertragsänderung aktualisiert `docs/data-contract.md` und bringt Tests mit.

## Daten, Geheimnisse, Datenschutz

- **Zugangsdaten:** `BLIZZARD_CLIENT_ID` und `BLIZZARD_CLIENT_SECRET` stehen lokal in der git-ignorierten `.env`, in Actions als Repository-Secrets. **Nie ausgeben, nie loggen, nie committen.** `.env` nicht mit `cat` o. Ä. anzeigen.
- **Keine Charakter-Identitäten** (Namen, Realms, IDs) im Repo, in Artefakten, Logs oder Issues. Rohantworten und `--state`/`--cache-dir` liegen außerhalb des Repos.
- **Blizzard-Regeln:** Daten höchstens 30 Tage aufbewahren, `/status` prüfen, gelöschte oder geänderte Charaktere verwerfen.
- **Keine erfundenen Werte:** Keine Platzhalter- oder Testdaten in einer ausgelieferten `Data.lua`. Fixtures sind synthetisch und als solche gekennzeichnet.

## Lokaler Test im Spiel

- **Ziel:** Kopien gehen nach `D:\World of Warcraft\_retail_\Interface\AddOns\StatCompass`. WoW darf dabei laufen, danach `/reload`.
- **Vorher Backup** des installierten Ordners anlegen, außerhalb von `AddOns`.
- **SavedVariables** (`WTF\…\StatCompassDB`) bleiben unberührt.
- **Nur getestete Dateien kopieren.** Dateien, an denen gerade ein anderer Agent arbeitet, nicht ohne Absprache überschreiben.
- Eine im Spiel getestete `Data.lua` ist **kein Release**. Im Repo bleibt `StatCompass/Data.lua` leer, bis ein geprüfter Daten-Release freigegeben ist (#10).

## GitHub Actions

- **`Tests`:** bei jedem PR und jedem Push auf `main`. Muss vor dem Merge grün sein.
- **`Refresh M+ cohort data`:** jeden Mittwoch 06:30 UTC und manuell. Er nutzt den inkrementellen Zustand der abgeschlossenen Wochen aus dem Actions-Cache und lädt als Artefakt Report, Beobachtungen und eine `Data.lua`-Kandidatin hoch, alles ohne Identitäten.
- **Budget:** Blizzard erlaubt 36.000 Anfragen pro Stunde. Neue Abfragen brauchen eine Kostenschätzung und, wenn möglich, eine lokale Messung, bevor sie in den Workflow kommen.

## Releases

- Releases entstehen nur über Tags `v<CalVer>` (z. B. `v2026.10.3`) und `.github/workflows/release.yml`. Der BigWigs-Packager legt das GitHub-Release an, CurseForge und Wago importieren es per Webhook. Ablauf und Prüfungen: `docs/releasing.md`.
- Jede Version braucht ein Changelog-Paar `changelog/CHANGELOG-<version>-en.md` und `-de.md`. `CHANGELOG.md` erzeugt nur `tools/generate_changelog.py`.
- Ein Release packt die `Data.lua` des letzten erfolgreichen Wochenlaufs. `StatCompass/Data.lua` im Repo bleibt leer.
- Tags setzt ein Agent nur auf ausdrücklichen Auftrag des Nutzers.

## Texte für Menschen

Changelogs, Release-Notes, README, Store-Beschreibungen und Issue-Texte gehen vor dem Veröffentlichen durch den **humanizer** (Skill bzw. dieselben Regeln): keine Floskeln, keine „nicht X, sondern Y“-Kontraste ohne Grund, keine Gedankenstriche als Allzweck-Verbindung, keine fett gesetzten Etiketten vor jedem Punkt. Inhalt und Fakten bleiben dabei unverändert.

## Kommunikation

- Mit dem Nutzer auf **Deutsch**. Issues und Nutzerdokumentation auf Deutsch, Code, Kommentare und technische `docs/` auf Englisch, wie im bestehenden Code.
- **Messen statt vermuten:** Antwortformate, Spieldaten und Performance an echten Daten prüfen, Annahmen als Annahmen kennzeichnen.
- **Fehler offen benennen:** auch eigene. Mit Korrektur, nicht still überschreiben.
