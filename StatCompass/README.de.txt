Stat Compass 0.1.0 — WoW Retail 12.1.0

Nach gesonderter Installationsfreigabe den Ordner StatCompass nach
Interface/AddOns kopieren. Die Charakterausrüstung öffnen, um das
angehängte Fenster zu sehen. Der Vergleich verwendet nur Mythic+.
Standard/Flach dunkel werden dort gewählt. Die +/− Seitentaste am Charakterfenster
klappt das Fenster ein/aus; der Zustand bleibt nach /reload erhalten.
Die Taste bleibt eingeklappt erreichbar und ist auf anderen Charakterseiten verborgen.
Eingeklappt werden keine Werte gelesen oder Zeilen gezeichnet. Ausklappen lädt
aktuelle Werte. Die Spezialisierung erscheint ohne ID. Zurücksetzen stellt Mythic+,
Standard, das ausgeklappte Fenster und die Minikarten-Vorgaben wieder her. Das mitgelieferte Stat-Compass-Icon lässt sich an der Minikarte ziehen.
Linksklick öffnet Ausrüstung, Rechtsklick Optionen > AddOns > Stat Compass.
Dort lassen sich Design und Sichtbarkeit des Symbols wählen oder die
Darstellung zurücksetzen (Ein-/Ausklappzustand bleibt erhalten). Position und
Sichtbarkeit bleiben nach /reload erhalten. Kein weiteres Funktionsfenster.
Deutsch wird bei deDE automatisch verwendet; sonst erscheint Englisch.
Das Fenster folgt der Höhe des Charakterfensters und zeigt vier Wertezeilen.
Zahlen und Balken zeigen Wertungspunkte aus Core.ratingTarget.
Die eigene Wertung steht links groß und statfarben, daneben das beschriftete Ziel.
Die eigene Wertung füllt den Balken. Ein weißer Marker zeigt das Ziel, ein schmaler
Streifen P40 bis P60. Darunter steht zu niedrig / passt / darüber; beide
Spannenränder zählen als passt. Innerhalb und oberhalb der Spanne leuchtet die
Füllung statisch; das bedeutet nicht, dass mehr Wertung besser ist. Alle vier Skalen bleiben bei 0–2000; dieser
Anzeigebereich ist keine technische Grenze. Höhere Werte behalten ihre Zahl und >;
Spannen über dem Rand zeigen Spanne >2000. Eine DR-Beschriftung mit eigenem
Tooltip, aber ohne Balkenmarker, zeigt die ersten DR-Richtwerte nach Nutzervorgabe: Crit 1380, Tempo
1320, Meisterschaft 1380, Vielseitigkeit 1620. Sie erscheinen nur auf Stufe 90 mit
Retail-Interface 120100 und sind keine Ziele oder optimalen Werte. Weitere Wertung
wirkt weiter, bringt aber weniger pro Punkt; prozentuale Buffs zählen nicht dazu.
Ohne geprüftes Ziel bleibt nur eine lesbare eigene Wertung stehen. Zielbeschriftung
und Balkengrafiken verschwinden. Ein unlesbarer eigener Wert lässt die anderen
lesbaren Wertungen stehen. Ziele sind die Ausrüstungswertungs-Mediane der Kohorte
mit P40–P60-Wertungsspanne, keine Umrechnung aktueller Prozentwerte. Die Tooltips
nennen die Median-Prozentwerte der Kohorte zur Einordnung und warnen, wenn die
Ziele zusammen das eigene Budget übersteigen. Prio ordnet die Werte nach dem Sekundär-Budget der Top-Spieler.
Das sind keine simulierten Stat-Gewichte.

Die Data.lua im Repository enthält absichtlich keine Zieldaten. Release-Pakete
verwenden generierte Daten eines erfolgreichen Wochenlaufs für den EU-Top-30-Vergleich.
Ohne gültige Daten bleiben eigene Wertungen sichtbar, Ziele und Balken verborgen.
Die Verteilung garantiert keinen ausgewogenen Build oder dein persönliches Optimum.
Der Nutzer hat den Wächter-Screenshot und das eigene Icon lokal akzeptiert.
Das belegt keine Abnahme aller Clients, des Paladins oder der Performance und
keine öffentliche Veröffentlichung.
