# Releases

Releases laufen wie bei weekly-alt-tracker und FolioSwap: Ein Tag `v<CalVer>` startet `.github/workflows/release.yml`. Der BigWigs-Packager baut daraus das ZIP und legt ein GitHub-Release an. CurseForge und Wago holen sich dieses Release über ihre Webhooks. Im Repository liegen dafür keine API-Tokens.

## Ablauf eines Release

1. Für die neue Version ein Changelog-Paar anlegen: `changelog/CHANGELOG-<version>-en.md` und `changelog/CHANGELOG-<version>-de.md`. Die erste Zeile lautet jeweils `# Stat Compass <version>`. Die Texte vor dem Commit mit dem humanizer überarbeiten.
2. `python tools/generate_changelog.py` erzeugt daraus `CHANGELOG.md`. Die Datei wird nie von Hand bearbeitet.
3. Per PR nach `main` bringen.
4. Taggen und pushen, zum Beispiel:

   ```
   git tag v2026.10.3
   git push origin v2026.10.3
   ```

Der Workflow bricht ab, bevor etwas veröffentlicht wird, wenn einer dieser Punkte nicht stimmt:

- Die Tests sind grün.
- Für die Version im Tag gibt es ein Changelog-Paar, und `CHANGELOG.md` entspricht dem Generator.
- Die `Data.lua` aus dem letzten erfolgreichen Wochenlauf (`Refresh M+ cohort data`) besteht `tools/release_data.py`. Das Addon selbst prüft sie dabei mit der TOC-Interface-Version, Stufe 90 und der aktuellen Zeit. Sie muss mindestens 7 Tage gültig bleiben und mindestens 35 Spezialisierungen abdecken.
- Das gepackte ZIP enthält genau den Ordner `StatCompass/` mit allen Addon-Dateien und einer gefüllten `Data.lua`, aber nichts aus `tools/`, `tests/` oder `docs/`.

Die Version im Spiel kommt aus dem Tag: In der TOC steht `## Version: @project-version@`, und der Packager ersetzt das.

## Daten im Release

Im Repository bleibt `StatCompass/Data.lua` leer. Erst der Release-Workflow lädt das Artefakt des letzten erfolgreichen Wochenlaufs und packt dessen `Data.lua` ein. Blizzard erlaubt API-Daten höchstens 30 Tage, deshalb verfallen sie auch im Addon nach 30 Tagen. Ohne neuen Release zeigt Stat Compass danach keine Vergleichswerte mehr. Spätestens alle drei Wochen braucht es also einen Release. Die automatische Variante ist #10.

## Automatische Daten-Releases

`refresh-mplus-data.yml` läuft täglich. Ein kurzer Planungsschritt entscheidet, was passiert:

- Der Datenlauf startet jeden Mittwoch, bei manuellem Start und immer dann, wenn ein Daten-Release fällig ist.
- Ein Daten-Release ist fällig, wenn die Repository-Variable `AUTO_DATA_RELEASE` auf `true` steht und der letzte veröffentlichte Release mindestens 120 Stunden alt ist.

Ist ein Release fällig und der Datenlauf erfolgreich, prüft `tools/data_release.py` mit `tools/release_gate.py`, ob alle Voraussetzungen erfüllt sind. Fehlt eine davon, gibt es keinen Release:

- Der letzte Release ist veröffentlicht und hat ein ZIP.
- Mindestens 35 Spezialisierungen haben Daten.
- Die API hat nur mit 200 oder 404 geantwortet; Netzwerk-Wiederholungen sind erlaubt.
- In der `Data.lua` stehen keine Spielernamen oder Realms.
- Die Daten bleiben mindestens 7 Tage gültig.

Danach schreibt der Workflow ein zweisprachiges Changelog-Paar („Datenaktualisierung“), committet es nach `main`, setzt den Tag (`v<Datum>`, bei einem zweiten Release am selben Tag `-2`) und ruft `release.yml` auf. Das läuft genauso wie bei einem Release von Hand, nur mit den Daten genau dieses Laufs.

Den ersten Release machst du immer selbst per Tag. Ohne einen veröffentlichten Release lehnt das Gate ab. Eingeschaltet wird die Automatik unter Settings → Secrets and variables → Actions → Variables mit `AUTO_DATA_RELEASE` = `true`. Laut #10 erst nach der Abnahme im Spiel.

## Probelauf

Unter Actions → `Release` → `Run workflow` läuft alles wie bei einem echten Release, nur mit `-d`: Hochgeladen wird nichts, das fertige ZIP liegt als Artefakt `stat-compass-dry-run` bei.

## Einrichtung bei CurseForge und Wago

Das ist einmalig und läuft wie bei den anderen Addons:

1. Bei CurseForge und Wago jeweils ein Projekt anlegen und das GitHub-Repository bzw. den Webhook verbinden.
2. Die Projekt-IDs stehen in `StatCompass/StatCompass.toc`: CurseForge `1724016`, Wago `YK9xO36L`.
3. Einen Probelauf starten, danach den ersten Tag setzen.

Das Repository ist privat. Ob ein Host Releases aus einem privaten Repository abholen kann, hängt von der Freigabe ab, die du ihm beim Verbinden gibst.
