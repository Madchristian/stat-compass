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

## Probelauf

Unter Actions → `Release` → `Run workflow` läuft alles wie bei einem echten Release, nur mit `-d`: Hochgeladen wird nichts, das fertige ZIP liegt als Artefakt `stat-compass-dry-run` bei.

## Einrichtung bei CurseForge und Wago

Das ist einmalig und läuft wie bei den anderen Addons:

1. Bei CurseForge und Wago jeweils ein Projekt anlegen und das GitHub-Repository bzw. den Webhook verbinden.
2. Die Projekt-IDs in `StatCompass/StatCompass.toc` eintragen: `## X-Curse-Project-ID: <id>` und `## X-Wago-ID: <id>`.
3. Einen Probelauf starten, danach den ersten Tag setzen.

Das Repository ist privat. Ob ein Host Releases aus einem privaten Repository abholen kann, hängt von der Freigabe ab, die du ihm beim Verbinden gibst.
