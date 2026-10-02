"""Local prerequisite/due calculation only; this module cannot publish data."""
import hashlib
import json
import re
from datetime import datetime, timezone

REQUIRED_QUALITY = ("coverage", "identities", "blizzard_stats", "rights", "retention", "readback")
FIVE_DAYS = 120 * 3600


class GateBlocked(ValueError):
    pass


def _epoch(value, label):
    if type(value) is not int or not 1000000000 <= value <= 9999999999:
        raise GateBlocked(f"invalid {label}")
    return value


def evaluate(state):
    if not isinstance(state, dict):
        raise GateBlocked("invalid state")
    now = _epoch(state.get("now"), "clock")
    release = state.get("last_release")
    if release is None:
        if state.get("first_release_approved") is not True:
            raise GateBlocked("first release requires approval")
        last, previous = None, None
    else:
        if not isinstance(release, dict) or release.get("channel") != "data" or release.get("verified") is not True:
            raise GateBlocked("last release is not verified data-channel publication")
        last = _epoch(release.get("published_at"), "last verified publication")
        previous = release.get("id")
        if not isinstance(previous, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", previous):
            raise GateBlocked("missing or invalid verified release ID")
        if last > now:
            raise GateBlocked("future publication clock")
    approved, running = state.get("approved_code_sha"), state.get("running_code_sha")
    if not isinstance(approved, str) or not re.fullmatch(r"[0-9a-f]{40}", approved) or running != approved:
        raise GateBlocked("approved full code SHA mismatch")
    if state.get("pending_unverified_publication") is not False:
        raise GateBlocked("unverified publication requires recovery")
    quality = state.get("quality")
    if not isinstance(quality, dict) or any(quality.get(key) is not True for key in REQUIRED_QUALITY):
        raise GateBlocked("quality prerequisites incomplete")
    season = state.get("season")
    if not isinstance(season, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", season) or (previous is not None and (not isinstance(previous, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", previous))):
        raise GateBlocked("invalid release identity")
    key_body = json.dumps([previous, approved, season], separators=(",", ":"))
    key = hashlib.sha256(key_body.encode()).hexdigest()
    return {"due": last is None or now-last >= FIVE_DAYS, "idempotencyKey": key,
            "nextDueAt": None if last is None else last+FIVE_DAYS}


def main():
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path, help="reviewed local JSON state file")
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(args.state.read_text(encoding="utf-8")))
    except (GateBlocked, ValueError) as exc:
        parser.exit(2, f"release blocked: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
