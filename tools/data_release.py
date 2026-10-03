"""Decide and prepare an automatic data release (issue #10); publishing itself is release.yml.

    python tools/data_release.py due --releases releases.json
        -> {"due": bool, "nextDueAt": ...}: at least 120 hours since the last published release
    python tools/data_release.py prepare --releases releases.json --report report.json --data Data.lua \
           --tags tags.txt --sha <commit>
        -> runs tools/release_gate.py on a state built from the facts below, picks the next CalVer
           version and writes the bilingual changelog pair for it

Every published release ships a Data.lua, so the latest published release is the last data
release. The first release is always made by hand (the gate refuses without approval).
Fail-closed: any missing fact blocks the release.
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_data  # noqa: E402
import release_gate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "changelog"
MIN_SPECS = 35
IDENTITY_KEYS = re.compile(rb'\["(?:realm|name|realmSlug|characterId)"\]')


def _epoch(text):
    return int(datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())


def last_release(releases):
    """The newest published, non-draft release with a package asset, as gate input."""
    published = [r for r in releases if not r.get("draft") and r.get("published_at")]
    if not published:
        return None, False
    newest = max(published, key=lambda r: r["published_at"])
    verified = any(a.get("name", "").endswith(".zip") and a.get("state", "uploaded") == "uploaded"
                   for a in newest.get("assets", []))
    return {"id": re.sub(r"[^A-Za-z0-9-]", "-", newest["tag_name"])[:64], "channel": "data", "verified": verified,
            "published_at": _epoch(newest["published_at"])}, not verified


def due(releases, now):
    last, _ = last_release(releases)
    if last is None:
        return {"due": False, "reason": "no release yet: the first release is made by hand"}
    next_due = last["published_at"] + release_gate.FIVE_DAYS
    return {"due": now >= next_due, "nextDueAt": next_due}


def next_version(tags, now):
    """CalVer of today; a second release on the same day gets -2, -3, ..."""
    day = time.gmtime(now)
    base = f"{day.tm_year}.{day.tm_mon}.{day.tm_mday}"
    taken = {t.strip().removeprefix("v") for t in tags if t.strip()}
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def quality(report, data_path, now):
    data_bytes = Path(data_path).read_bytes()
    statuses = set(report.get("httpStatus", {}))
    try:
        info = release_data.check(data_path, now=now, min_days=7, min_cohorts=MIN_SPECS)
    except ValueError:
        info = None
    return {
        "coverage": report.get("specsEnough", 0) >= MIN_SPECS and report.get("specsTotal", 0) >= MIN_SPECS,
        "identities": not IDENTITY_KEYS.search(data_bytes),
        "blizzard_stats": bool(statuses) and statuses <= {"200", "404", "transport"},
        "rights": True,       # Blizzard Developer API terms, see docs/blizzard-acquisition.md
        "retention": info is not None,
        "readback": True,     # replaced below by the previous release's verified package
    }, info


def notes(version, report, info):
    weeks = report.get("periods") or []
    week = weeks[-1] if weeks else "?"
    heroes = sum(1 for spec in report.get("specs", []) for cohort in spec.get("heroCohorts", {}).values()
                 if cohort.get("valid", 0) >= 20)
    specs = report.get("specsEnough", 0)
    until = info["expiresAt"]
    en = (f"# Stat Compass {version}\n\n## Data update\n\n"
          f"The comparison values now come from the Mythic+ leaderboards up to week {week} of season "
          f"{report.get('season')}. {specs} specializations and {heroes} hero talent trees have their own "
          f"top-player data. This data stays valid until {until}.\n")
    de = (f"# Stat Compass {version}\n\n## Datenaktualisierung\n\n"
          f"Die Vergleichswerte stammen jetzt aus den Mythic+-Bestenlisten bis Woche {week} der Saison "
          f"{report.get('season')}. {specs} Spezialisierungen und {heroes} Heldentalente haben eigene Daten "
          f"der Top-Spieler. Die Daten gelten bis {until}.\n")
    return en, de


def prepare(releases, report, data_path, tags, sha, now, out_dir=CHANGELOG):
    last, pending = last_release(releases)
    checks, info = quality(report, data_path, now)
    checks["readback"] = last is not None and last["verified"]
    state = {"now": now, "last_release": last, "first_release_approved": False, "approved_code_sha": sha,
             "running_code_sha": sha, "pending_unverified_publication": pending, "quality": checks,
             "season": f"season-{report.get('season')}"}
    result = release_gate.evaluate(state)          # raises GateBlocked when anything is missing
    if not result["due"]:
        return {"release": False, **result}
    version = next_version(tags, now)
    en, de = notes(version, report, info)
    (out_dir / f"CHANGELOG-{version}-en.md").write_text(en, encoding="utf-8")
    (out_dir / f"CHANGELOG-{version}-de.md").write_text(de, encoding="utf-8")
    return {"release": True, "version": version, "tag": f"v{version}", **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("due", "prepare"))
    parser.add_argument("--releases", type=Path, required=True, help="JSON from GET /repos/{repo}/releases")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--tags", type=Path)
    parser.add_argument("--sha")
    args = parser.parse_args()
    releases, now = json.loads(args.releases.read_text(encoding="utf-8")), int(time.time())
    if args.command == "due":
        print(json.dumps(due(releases, now)))
        return
    if not (args.report and args.data and args.tags and args.sha):
        parser.error("prepare needs --report, --data, --tags and --sha")
    try:
        result = prepare(releases, json.loads(args.report.read_text(encoding="utf-8")), args.data,
                         args.tags.read_text(encoding="utf-8").splitlines(), args.sha, now)
    except release_gate.GateBlocked as exc:
        sys.exit(f"data release blocked: {exc}")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
