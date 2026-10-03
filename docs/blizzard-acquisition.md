# Blizzard Mythic+ cohort acquisition

Stat Compass builds its Mythic+ comparison cohorts from Blizzard's official APIs only: the Game Data API (`dynamic-eu`, `static-eu`) and the Profile API (`profile-eu`), with OAuth client credentials. No third-party ranking site is involved. Tool: `tools/providers/blizzard_mplus.py`.

## Ranking: exact top 30 per specialization

1. **Leaderboards.** Every EU connected realm × season dungeon × season week (`/data/wow/connected-realm/{id}/mythic-leaderboard/{dungeon}/period/{week}`). Each listed run carries Blizzard's run rating (`mythic_rating`) and every member's specialization ID. Season 18 has 92 connected realms, 8 dungeons and 8 weeks, so 5,888 boards with about 2.4 million member entries.
2. **Spec score.** Per character and spec, the sum over dungeons of the best run rating *played in that spec*. This follows Blizzard's season rating, which is the sum of the best run per dungeon; it was checked against a season profile (3680.43 vs 3680.5). Off-spec runs never count.
3. **Interval bounds.** Boards hold at most 500 runs, and 4,429 of 5,888 boards were full, so a weaker run can fall off. A cross-realm run is listed on the board of *every* member's connected realm (22 of 22 checked). That gives a hard bound: a missing timed run is rated at most the lowest entry of a full board of the character's connected realm for that dungeon in that week. Untimed runs never appear on boards; their ceiling is the highest untimed rating seen in any fetched season profile (320 in season 18).
   - lower bound: the sum of the best known in-spec run per dungeon
   - upper bound: the sum of `max(known, board floor, untimed ceiling, pre-filter rating)` per dungeon
4. **Resolution.** The official season profile (`/mythic-keystone-profile/season/{id}`) lists each dungeon's best timed and untimed runs with every member's spec. The certifier fetches it for the selected players and for anyone whose upper bound exceeds the current 30th place. After the profile, a dungeon is exact when its best run was played in the spec. Otherwise that best run is the upper bound.
5. **Eligibility.** The certifier walks the ranking and keeps a player only if:
   - `/status` is valid and the ID matches,
   - the active spec is the ranked spec,
   - the character is at maximum level,
   - the statistics are complete,
   - the item level is not more than 10 below the cohort median.

   Excluded players are replaced from further down the ranking. The item level rule stops a top player who is currently wearing an alt or PvP set from setting the minimum alone.
6. **Certificate.** A spec is `certified` when the 30 selected players are eligible, no unselected eligible character has an upper bound above the 30th lower bound, and a character absent from every board cannot reach it either (`unseenBound`, 2,560 in season 18, against thresholds of about 3,400–3,950). The report states, per spec, the threshold, how many profiles were fetched, how many scores are exact and how many characters remain open.

A `--min-run-rating` pre-filter (default 300) drops weak runs while scanning. Its value is added to every upper bound, so a dropped run can never hide a contender.

## Hero talent cohorts

`/specializations` returns the active specialization and `active_hero_talent_tree` (ID and name). The certifier reads it first for every candidate; a player of the wrong spec or tree costs one request. For every hero tree seen among a spec's checked players, the same certification runs restricted to that tree, walking at most `--hero-walk` (150) ranked players. A tree with fewer than 20 usable players gets no cohort of its own: at the top, Brewmaster is almost entirely Master of Harmony (10 of 11), so a Shado-Pan cohort would compare against far weaker players. The spec cohort records the tree mix (`heroMix`). Like the stats, the tree is the one equipped now, not the one used in the ranked runs.

## Plausibility (issue #4)

Two stages, both fail-closed and reported with a reason; nothing is clipped.

- **Hard checks per player**, reason `invalid`:
  - every number must be finite and non-negative (otherwise no statistics at all);
  - all four ratings must be present;
  - crit must be at most 100 %, because it is a probability;
  - the four ratings must not all be zero.

  There is no fixed rating cutoff: no verified build, level or equipment bound exists, so a value like 4,000 haste rating is judged by the cohort, not by its size.
- **Cohort checks on the players picked so far** (from 10 players on), run after the item level filter:
  - `outlier`: a stat's share of the secondary rating budget is more than 30 points and more than 5 robust z (median/MAD) from the cohort median. The player is quarantined and the walk takes the next ranked player.
  - Above 3.5 robust z the player is only marked (`flags`, counted as `flagged` in the report) and stays in.
  - `inconsistent`: a percentage lies further from the cohort's rating-to-percent line (Theil-Sen) than both 15 points and the stat's median value. That is the signature of a unit mix-up, such as a rating stored as a percentage.

Calibration on the season 18 cohorts (1,200 players):

- Budget shares sit a median 2.8 and at most 15.4 points (99th percentile) from their cohort median.
- Percent residuals are under 0.02 points for 90 % of values. Windwalker reaches about 37 points, because a spec effect raises haste.
- Result: one player was quarantined (an Augmentation Evoker with 9 % mastery share against a cohort median of 48 %), 70 players were only flagged.
- Real build variants stay in. Protection Paladin's mastery build (34 % share) scores about 3.2.

## Statistics

`/profile/wow/character/{realm}/{name}/statistics`, with the Character-window semantics:

- Crit is the highest of melee, ranged and spell crit `value` (PaperDoll rule).
- Haste is the haste `value`.
- Versatility is `versatility_damage_done_bonus`.
- Mastery `value` is the mastery **effect percent**: `value − rating_bonus` is constant per spec (that spec's base mastery).
- Ratings come from `rating_normalized` (crit, haste, mastery) and from `versatility`.

Mistweaver's mastery `value` is several hundred (314–984 in the season 18 cohort; about 249.5 + 0.678 × rating). It is exactly what the game returns from `GetMasteryEffect()`: 755.22 at 746 rating, checked in game against the predicted 755.3. The addon reads the player's own value through the same function, so Mistweaver mastery compares like every other spec; only the number exceeds 100. Retribution haste of 86–104 % and Windwalker haste up to 62 % are reported by Blizzard as is and should be checked against the Character window.

The values describe the gear a player has **equipped now**, not their gear during the ranked runs. Blizzard provides no per-run statistics.

## Outputs

- `--output report.json`: identity-free report with per-spec certification, exclusion reasons, percentage and rating ranges, means and item level range.
- `--observations observations.json`: identity-free per-spec rows (stats, ratings, item level, observation time) for the generator.
- `tools/blizzard_dataset.py --observations observations.json --output Data.lua`:
  - writes a schema 3 candidate (see the [data contract](data-contract.md)) with 30 rows per spec and opaque row IDs (`{spec}-{rank}`),
  - reads interface and client build from Blizzard's EU version table,
  - sets the expiry to 30 days after the oldest observation.

  Replacing `StatCompass/Data.lua` with it is a reviewed release step.

## Credentials, privacy and retention

- `BLIZZARD_CLIENT_ID` and `BLIZZARD_CLIENT_SECRET` come from the environment, or locally from the git-ignored `.env` in the repository root. They are never printed.
- Character names, realms and IDs exist only in memory, in an optional `--cache-dir`, and in the optional `--state`. Both must lie outside the repository. Blizzard's terms allow keeping API data for at most 30 days, with `/status` checks for deleted or changed characters.
- `--state` stores the aggregated best runs of **closed** weeks (gzip JSON). It is discarded after 27 days, on a new season, or when the pre-filter changes. A run then fetches only weeks missing from the state plus the current week.

## GitHub Actions

`.github/workflows/refresh-mplus-data.yml` runs weekly on Wednesday 06:30 UTC, after the EU reset, and on demand. `full_scan` ignores the state. It:

1. runs the test suite,
2. restores the state from the repository's private Actions cache,
3. certifies all specs,
4. saves the state (also on failure, because closed weeks are stored before the current week is fetched),
5. generates the `Data.lua` candidate,
6. writes a job summary,
7. uploads report, observations and candidate as a 30-day artifact.

The artifact contains no identities. Required repository secrets: `BLIZZARD_CLIENT_ID` and `BLIZZARD_CLIENT_SECRET`.

Cost estimate: a full scan is about 10,000–15,000 requests and 10–20 minutes, mostly waiting on the network. An incremental week is 736 boards plus certification.

## Transport

- Allowlisted host and namespaces, no redirects, 8 MiB response cap, at most 40 requests per second.
- Retries on 429/5xx with `Retry-After`, and on transport failures: connection errors, read timeouts, truncated bodies.
- A 404 is a documented answer (missing week, deleted character), not a failure.
