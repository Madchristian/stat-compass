StatCompass = StatCompass or {}
StatCompass.locale = {
  enUS = {
    skin = "Skin", minimap = "Minimap button", shown = "Shown", hidden = "Hidden",
    resetPresentation = "Reset appearance",
    appearanceHelp = "Appearance changes apply immediately. The equipment panel has the same skin controls.",
    minimapHelp = "Left-click: open equipment\nRight-click: options\nDrag: move around the minimap",
    title = "Stat Compass", raid = "Raid", mythic = "Mythic+", default = "Default", spec = "Spec",
    flat = "Flat dark", reset = "Reset", unknown = "Unknown", noData = "No licensed EU top 50 data",
    observed = "Rating reference", current = "Current", min = "Min", mean = "Mean", max = "Max", sample = "Sample", crit = "Crit",
    haste = "Haste", mastery = "Mastery", versatility = "Versatility",
    noSpec = "Specialization unknown", source = "Source", unavailable = "Unavailable",
    observedAt = "Observed", collectedAt = "Collected",
    expiresAt = "Expires", selected = "Selected", valid = "Valid",
    ratingUnit = "rating", verifiedAxis = "Verified rating cap", axisUnavailable = "Verified rating cap unavailable; rating bar hidden.",
    axisUnavailableShort = "Rating axis unavailable", meanShort = "Mean",
    ratingUnavailable = "Current rating unavailable; percent display is separate.", ratingPastAxis = "Rating exceeds the verified cap; bar hidden.",
    sampleUncertainty = "The sample may not represent all players.",
    distributionHelp = "Rating points. The cohort arithmetic mean is descriptive, not a personal optimum or simulation. Color shows distance from the mean within the observed range, not performance.",
    unavailableHelp = "No verified rating cap is available. Current percentages are shown without a rating bar.",
  },
  deDE = {
    skin = "Design", minimap = "Minikartensymbol", shown = "Sichtbar", hidden = "Ausgeblendet",
    resetPresentation = "Darstellung zurücksetzen",
    appearanceHelp = "Änderungen gelten sofort. Das Ausrüstungsfenster bietet dieselbe Designauswahl.",
    minimapHelp = "Linksklick: Ausrüstung öffnen\nRechtsklick: Optionen\nZiehen: an der Minikarte verschieben",
    title = "Stat Compass", raid = "Schlachtzug", mythic = "Mythic+", default = "Standard", spec = "Spez.",
    flat = "Flach dunkel", reset = "Zurücksetzen", unknown = "Unbekannt", noData = "Keine lizenzierten EU-Top-50-Daten",
    observed = "Wertungs-Vergleich", current = "Aktuell", min = "Min", mean = "Mittelwert", max = "Max", sample = "Stichprobe", crit = "Kritisch",
    haste = "Tempo", mastery = "Meisterschaft", versatility = "Vielseitigkeit",
    noSpec = "Spezialisierung unbekannt", source = "Quelle", unavailable = "Nicht verfügbar",
    observedAt = "Beobachtet", collectedAt = "Erfasst",
    expiresAt = "Ablauf", selected = "Ausgewählt", valid = "Gültig",
    ratingUnit = "Wertung", verifiedAxis = "Geprüfte Wertungsgrenze", axisUnavailable = "Geprüfte Wertungsgrenze fehlt; kein Balken.",
    axisUnavailableShort = "Wertungsachse fehlt", meanShort = "Ø",
    ratingUnavailable = "Aktuelle Wertung fehlt; der Prozentwert ist separat.", ratingPastAxis = "Wertung über der geprüften Grenze; kein Balken.",
    sampleUncertainty = "Die Stichprobe muss nicht alle Spieler repräsentieren.",
    distributionHelp = "Wertungspunkte. Der arithmetische Mittelwert beschreibt die Gruppe; er ist kein persönliches Optimum oder eine Simulation. Die Farbe zeigt den Abstand zum Mittelwert innerhalb der beobachteten Spanne, nicht die Leistung.",
    unavailableHelp = "Keine geprüfte Wertungsgrenze verfügbar. Aktuelle Prozentwerte erscheinen ohne Wertungsbalken.",
  },
}
function StatCompass.Text(key, locale)
  local chosen = StatCompass.locale[locale] or StatCompass.locale.enUS
  return chosen[key] or StatCompass.locale.enUS[key] or key
end
