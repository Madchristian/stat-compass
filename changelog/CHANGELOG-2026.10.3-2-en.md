# Stat Compass 2026.10.3-2

- During combat, the panel keeps the last readable values from before combat and labels them "Pre-combat snapshot". Stat Compass does not scan new character stats during combat.
- Validated comparison data is cached. The full dataset is not revalidated during combat; expired or mismatched comparison data stays unavailable.
- When combat ends, the panel immediately refreshes with current values.
