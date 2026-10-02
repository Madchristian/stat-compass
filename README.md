# Stat Compass

## English

Stat Compass is a small World of Warcraft Retail 12.1.0 addon attached to the Character **equipment** page. It shows the current Crit, Haste, Mastery, and Versatility percentages in Blizzard's Character-window order. Raid and Mythic+ are separate comparison contexts. The Default skin uses WoW textures; Flat dark is an original, texture-simple dark design inspired by EllesmereUI, with no dependency on it. Settings are saved as `StatCompassDB` and can be reset in the panel. English is the fallback locale.

**Data status:** The included target dataset is deliberately empty. The full-height panel shows four current-value rows. Rating bars require a verified rating cap and an explicit rating snapshot; without them, percentages remain visible and bars are hidden. The rating reference minimum, arithmetic mean and maximum are **Unknown**. This build does **not** provide meaningful stat recommendations. The [corrected source research](docs/top50-eu-source-research.md) identifies Raider.IO's published EU specialization leaderboard window at `/api/v1/client/character-rivals`. The bounded [local acquisition tool](docs/rio-acquisition.md) can traverse public windows, but the observed Arcane top 50 includes four anonymous ranks, so it cannot provide 50 identifiable players. The [Blizzard-only acquisition](docs/blizzard-acquisition.md) now certifies an exact EU top 30 per specialization from official leaderboards and season profiles, and generates a schema 3 `Data.lua` candidate with percentages and ratings; a weekly GitHub Actions workflow refreshes it. Shipping that candidate is a separate reviewed release step, and the Core still supplies no verified rating cap. Provider coverage, rights and retention must be assessed against its current acquisition results, not the older Raider.IO research. A future cohort's exact minimum and maximum would describe observed players, not an optimum or personal simulation. See [provenance](docs/provenance.md).

To install after approval, copy the `StatCompass` folder from the reproducible ZIP into `World of Warcraft/_retail_/Interface/AddOns/` with the game closed. The resulting path should end in `AddOns/StatCompass/StatCompass.toc`. Open Character → equipment; select Raid or Mythic+ and Default or Flat dark in the attached panel. Reset in the equipment panel restores Raid, Default, and the minimap defaults. The draggable minimap button opens equipment on left-click. Right-click opens Options > AddOns > Stat Compass, where you can choose the same skin, show or hide the minimap button, and reset appearance without changing Raid/Mythic+. No separate feature window is added. This combined controls candidate has not been installed into WoW or tested in game.

Build and check locally with Python 3.11:

```powershell
uv venv --python 3.11 .venv
uv pip install --python .venv/Scripts/python.exe 'lupa==2.6' 'pytest==8.4.2'
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe tools/package.py
.venv/Scripts/python.exe tools/package.py --verify
```

The exact addon ZIP inventory is fixed in `tools/package.py`; it writes `dist/StatCompass-0.1.0.zip` and a SHA-256 manifest. Rebuilding from identical files yields identical bytes. `dist`, `.venv`, and tool caches are ignored. Data updates occur through reviewed addon versions, not an in-game network request. The [offline data contract](docs/data-contract.md) and [rights blocker](docs/provenance.md) are documented. Original research is preserved [verbatim](docs/research-original.md). License terms and upstream attribution are in [LICENSE](LICENSE) and [NOTICE](StatCompass/NOTICE.txt). The [test report](docs/test-report.md) records actual runs; [in-game acceptance](docs/acceptance.md) remains pending.

The ZIP includes short English and German installation/status notes as `README.txt` and `README.de.txt`.

## Deutsch

Stat Compass ist ein kleines Addon für World of Warcraft Retail 12.1.0. Das Fenster hängt an der **Ausrüstungsseite** des Charakterfensters. Es zeigt die aktuellen Prozentwerte für Kritisch, Tempo, Meisterschaft und Vielseitigkeit in der Reihenfolge des Blizzard-Fensters. Schlachtzug und Mythic+ sind getrennte Vergleichskontexte. „Standard“ nutzt WoW-Texturen; „Flach dunkel“ ist eine eigenständige, flache Gestaltung, inspiriert von EllesmereUI, ohne Abhängigkeit. Einstellungen werden in `StatCompassDB` gespeichert und können im Fenster zurückgesetzt werden. Für andere Spielsprachen wird Englisch verwendet.

**Datenstand:** Der mitgelieferte Zieldatensatz ist absichtlich leer. Das Fenster zeigt aktuelle Werte; Zielwerte bleiben **Unbekannt**. Der veröffentlichte Raider.IO-Endpunkt /api/v1/client/character-rivals liefert regionale Spezialisierungsranglisten. Unter den beobachteten ersten 50 Arkan-Rängen sind vier anonym. Der separate Blizzard-Provider erfasst inzwischen Statistiken und Wertungsspannen. Der geprüfte Core liefert weiterhin Prozentwerte, keine Wertungs-Schnittstelle mit geprüfter Obergrenze. Deshalb bleiben Wertungsbalken verborgen. Abdeckung, Nutzungsrechte und Datenlöschung sind anhand der aktuellen Provider-Ergebnisse zu prüfen. Einzelheiten: [Daten- und API-Herkunft](docs/provenance.md).

Nach gesonderter Freigabe den Ordner `StatCompass` aus dem reproduzierbaren ZIP bei geschlossenem Spiel nach `World of Warcraft/_retail_/Interface/AddOns/` kopieren. Der Pfad muss auf `AddOns/StatCompass/StatCompass.toc` enden. Charakter → Ausrüstung öffnen; im angehängten Fenster Schlachtzug oder Mythic+ und Standard oder Flach dunkel wählen. „Zurücksetzen“ im Ausrüstungsfenster stellt Schlachtzug, Standard und die Minikarten-Vorgaben wieder her. Das verschiebbare Minikartensymbol öffnet die Ausrüstung per Linksklick. Rechtsklick öffnet Optionen > AddOns > Stat Compass: Design wählen, Minikartensymbol ein- oder ausblenden und Darstellung zurücksetzen, ohne Schlachtzug/Mythic+ zu ändern. Ein weiteres Funktionsfenster gibt es nicht. Diese zusammengeführte Version mit Minikarten- und Optionssteuerung wurde in WoW weder installiert noch getestet.

Die Befehle zum Testen und Packen stehen im englischen Abschnitt. Der ZIP-Inhalt und die Hashes werden geprüft. Daten werden nur mit einer geprüften Addon-Version aktualisiert, nicht über eine Netzwerkanfrage im Spiel. [Lizenz](LICENSE), [Herkunft](docs/provenance.md), [Testbericht](docs/test-report.md) und [offene Spielprüfung](docs/acceptance.md) dokumentieren den Stand.
