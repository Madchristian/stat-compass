"""Turn identity-free Blizzard cohort observations into a reviewed Data.lua candidate.

Input is the `--observations` file of tools/providers/blizzard_mplus.py. It contains no character
names, realms or IDs; rows get opaque per-cohort IDs. The output is validated by build_data.checked.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_data  # noqa: E402

VERSIONS_URL = "http://us.patch.battle.net:1119/wow/versions"  # Blizzard's own patch service speaks HTTP only
SOURCE_URL = "https://develop.battle.net/documentation/world-of-warcraft"
PERMISSION = ("Blizzard Developer API Terms of Use (distribution to end users for personal use, 30-day limit): "
              "https://www.blizzard.com/legal/a2989b50-5f16-43b1-abec-2ae17cc09dd6/blizzard-developer-api-terms-of-use")
# Mistweaver's mastery value is several hundred; it equals the in-game GetMasteryEffect() (755.22 at
# 746 rating, checked in game), so it compares like every other spec's mastery effect.
EXCLUDED_SPECS = {}
DAY = 86400


def parse_versions(text, region="eu"):
    """Return (interface, clientBuild) from the patch service table, e.g. 12.1.0.69933 -> (120100, 69933)."""
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    header = [column.split("!")[0] for column in lines[0].split("|")]
    for line in lines[1:]:
        row = dict(zip(header, line.split("|")))
        if row.get("Region") == region:
            match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", row.get("VersionsName", ""))
            if not match or row.get("BuildId") != match.group(4):
                raise ValueError("unexpected version row")
            major, minor, patch, build = map(int, match.groups())
            return major * 10000 + minor * 100 + patch, build
    raise ValueError(f"region {region} missing from version table")


def fetch_versions(timeout=10):
    with urlopen(Request(VERSIONS_URL, headers={"User-Agent": "StatCompass-local/0.1"}), timeout=timeout) as response:
        return parse_versions(response.read(64 * 1024).decode("utf-8"))


def _cohort(rows, *, spec_id, prefix, observations, interface, client_build, level):
    """One build_data cohort from identity-free rows, or a skip reason."""
    observed = max(r["observedAt"] for r in rows)
    if min(r["observedAt"] for r in rows) < observed - DAY:
        return None, "observations spread over more than 24 hours"
    out = [dict(rank=rank, id=f"{prefix}-{rank}", region="EU", mode="mythic", specID=spec_id,
                interface=interface, clientBuild=client_build, level=level, unit="percentPoints",
                semanticKind="masteryEffectPercent", observedAt=r["observedAt"],
                **{stat: r[stat] for stat in build_data.STATS},
                **{build_data.RATINGS[stat]: r["ratings"][stat] for stat in build_data.STATS})
           for rank, r in enumerate(rows, 1)]
    periods = observations.get("periods") or []
    cohort = dict(region="EU", mode="mythic", specID=spec_id, interface=interface, clientBuild=client_build,
                  level=level, unit="percentPoints", semanticKind="masteryEffectPercent",
                  season=f"Mythic+ season {observations['season']}",
                  rankingMetric=observations["rankingMetric"], difficulty="Mythic+",
                  partition=f"weeks {periods[0]}-{periods[-1]}" if periods else "all weeks",
                  observedAt=observed, selectedCount=len(out), validCount=len(out), observations=out)
    return cohort, None


def _hero_mix(rows):
    mix = {}
    for r in rows:
        name = (r.get("heroTree") or {}).get("name")
        if isinstance(name, str) and name:
            mix[name] = mix.get(name, 0) + 1
    return mix


def manifest(observations, *, interface, client_build, level, now, minimum=20, maximum=30):
    """Build a build_data manifest; returns (manifest, {key: skip reason}).

    Every spec gets a cohort with its hero talent mix; each hero talent tree with at least
    `minimum` usable players additionally gets its own cohort, which the addon prefers."""
    cohorts, hero_cohorts, skipped = [], [], {}
    common = dict(observations=observations, interface=interface, client_build=client_build, level=level)
    for spec_key, entry in sorted(observations["specs"].items(), key=lambda kv: int(kv[0])):
        spec_id = int(spec_key)
        if spec_id in EXCLUDED_SPECS:
            skipped[spec_id] = EXCLUDED_SPECS[spec_id]
            continue
        rows = entry.get("observations", [])[:maximum]
        if len(rows) < minimum:
            skipped[spec_id] = f"only {len(rows)} usable players"
            continue
        cohort, reason = _cohort(rows, spec_id=spec_id, prefix=str(spec_id), **common)
        if reason:
            skipped[spec_id] = reason
            continue
        if _hero_mix(rows):
            cohort["heroMix"] = _hero_mix(rows)
        cohorts.append(cohort)
        for hero_key, hero in sorted((entry.get("heroes") or {}).items(), key=lambda kv: int(kv[0])):
            hero_rows = hero.get("observations", [])[:maximum]
            key = f"{spec_id}/{hero.get('name') or hero_key}"
            if len(hero_rows) < minimum:
                skipped[key] = f"only {len(hero_rows)} usable players"
                continue
            hero_cohort, reason = _cohort(hero_rows, spec_id=spec_id, prefix=f"{spec_id}-{hero_key}", **common)
            if reason:
                skipped[key] = reason
                continue
            hero_cohort.update(heroTreeID=int(hero_key), heroTreeName=hero["name"])
            threshold = (hero.get("certification") or {}).get("threshold")
            if threshold:
                hero_cohort["rankingMetric"] += f"; best {len(hero_rows)} {hero['name']} players, 30th at rating {threshold:,.0f}"
            hero_cohorts.append(hero_cohort)
    if not cohorts:
        raise ValueError("no cohort qualifies")
    every = cohorts + hero_cohorts
    observed = max(c["observedAt"] for c in every)
    oldest = min(r["observedAt"] for c in every for r in c["observations"])
    # Blizzard API data may be kept at most 30 days from retrieval; the oldest row sets the clock.
    result = dict(interface=interface, clientBuild=client_build, level=level, collectedAt=now, observedAt=observed,
                  expiresAt=oldest + 30 * DAY, sourceURL=SOURCE_URL, permission=PERMISSION, cohorts=cohorts)
    if hero_cohorts:
        result["heroCohorts"] = hero_cohorts
    return result, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="candidate Data.lua; review before replacing StatCompass/Data.lua")
    parser.add_argument("--interface", type=int, help="override; default from Blizzard's EU version table")
    parser.add_argument("--client-build", type=int, help="override; default from Blizzard's EU version table")
    parser.add_argument("--level", type=int, default=90)
    parser.add_argument("--minimum", type=int, default=20)
    parser.add_argument("--maximum", type=int, default=30)
    args = parser.parse_args()
    raw = args.observations.read_bytes()
    interface, client_build = (args.interface, args.client_build) if args.interface and args.client_build else fetch_versions()
    now = int(time.time())
    data_manifest, skipped = manifest(json.loads(raw), interface=interface, client_build=client_build, level=args.level,
                                      now=now, minimum=args.minimum, maximum=args.maximum)
    data = build_data.checked(data_manifest, raw, now=now)
    args.output.write_text("-- Generated from Blizzard API observations by tools/blizzard_dataset.py; reviewed before release.\n"
                           "StatCompass.releaseData = " + build_data.lua_value(data) + "\n", encoding="utf-8")
    print(json.dumps({"interface": interface, "clientBuild": client_build, "cohorts": len(data_manifest["cohorts"]),
                      "heroCohorts": len(data_manifest.get("heroCohorts", [])),
                      "skipped": {str(k): v for k, v in skipped.items()},
                      "expiresAt": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(data_manifest["expiresAt"]))}, indent=1))


if __name__ == "__main__":
    main()
