"""Validate an authorized offline cohort manifest and emit Lua 5.1 data.

Validation cannot authenticate a provider or grant redistribution rights.
"""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

STATS = ("crit", "haste", "mastery", "versatility")
RATINGS = {stat: stat + "Rating" for stat in STATS}
MIN_COHORT, MAX_COHORT = 20, 50
MAX_TTL = 30 * 86400  # Upper bound only; a provider may require a shorter cache.
MAX_OBSERVATION_SPREAD = 86400
MAX_ROW_AGE = 30 * 86400  # Provider terms may impose a shorter limit.


def clean_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing {label}")
    if any(ord(ch) < 32 or 127 <= ord(ch) <= 159 or 0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise ValueError(f"control or surrogate in {label}")
    return value


def epoch(value, label):
    if type(value) is not int or not 1000000000 <= value <= 9999999999:
        raise ValueError(f"invalid {label} epoch")
    return value


def positive_int(value, label, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"invalid {label}")
    return value


def checked(manifest: dict, raw: bytes, *, now: int | None = None) -> dict:
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    now = epoch(int(time.time()) if now is None else now, "current time")
    interface = positive_int(manifest.get("interface"), "interface", 999999)
    client_build = positive_int(manifest.get("clientBuild"), "clientBuild", 9999999)
    level = positive_int(manifest.get("level"), "level", 1000)
    collected = epoch(manifest.get("collectedAt"), "collectedAt")
    observed = epoch(manifest.get("observedAt"), "observedAt")
    expires = epoch(manifest.get("expiresAt"), "expiresAt")
    if observed > collected or collected > now or expires <= now or expires <= collected or expires > collected + MAX_TTL:
        raise ValueError("future, expired, or overlong data retention")
    source_url = clean_text(manifest.get("sourceURL"), "sourceURL")
    permission = clean_text(manifest.get("permission"), "permission")
    if not source_url.startswith("https://"):
        raise ValueError("sourceURL must be HTTPS")
    cohorts = manifest.get("cohorts")
    if not isinstance(cohorts, list) or not cohorts:
        raise ValueError("no cohorts")
    result = dict(schema=3, interface=interface, clientBuild=client_build, level=level,
                  collectedAt=collected, observedAt=observed, expiresAt=expires,
                  sourceURL=source_url, rawSHA256=hashlib.sha256(raw).hexdigest(),
                  permission=permission, cohorts={})
    for cohort in cohorts:
        if not isinstance(cohort, dict):
            raise ValueError("cohort must be object")
        if cohort.get("region") != "EU" or cohort.get("mode") not in ("raid", "mythic"):
            raise ValueError("requires EU raid or mythic cohort")
        spec_id = positive_int(cohort.get("specID"), "specID", 1000000)
        for field, expected in (("interface", interface), ("clientBuild", client_build), ("level", level),
                                ("unit", "percentPoints"), ("semanticKind", "masteryEffectPercent")):
            if cohort.get(field) != expected:
                if field == "unit":
                    raise ValueError("ratings and mixed units are unsupported")
                raise ValueError(f"cohort {field} mismatch")
        for field in ("season", "rankingMetric", "difficulty", "partition"):
            clean_text(cohort.get(field), field)
        cohort_observed = epoch(cohort.get("observedAt"), "cohort observedAt")
        if cohort_observed > collected or cohort_observed > now:
            raise ValueError("future cohort observation")
        rows = cohort.get("observations")
        if not isinstance(rows, list) or not MIN_COHORT <= len(rows) <= MAX_COHORT:
            raise ValueError(f"cohort needs {MIN_COHORT} to {MAX_COHORT} observations")
        if cohort.get("selectedCount") != len(rows) or cohort.get("validCount") != len(rows):
            raise ValueError("cohort counts must equal its observations")
        seen = set()
        latest_row = 0
        for rank, row in enumerate(rows, 1):
            if not isinstance(row, dict) or row.get("rank") != rank:
                raise ValueError("rank invalid")
            row_id = clean_text(row.get("id"), "row id")
            if row_id in seen:
                raise ValueError("duplicate identity")
            seen.add(row_id)
            for field, expected in (("region", "EU"), ("mode", cohort["mode"]), ("specID", spec_id),
                                    ("interface", interface), ("clientBuild", client_build), ("level", level),
                                    ("unit", "percentPoints"), ("semanticKind", "masteryEffectPercent")):
                if row.get(field) != expected:
                    raise ValueError(f"row {field} mismatch")
            row_observed = epoch(row.get("observedAt"), "row observedAt")
            if row_observed > collected or row_observed > now:
                raise ValueError("future row observation")
            if row_observed < collected - MAX_ROW_AGE:
                raise ValueError("row exceeds collection age limit")
            if not cohort_observed - MAX_OBSERVATION_SPREAD <= row_observed <= cohort_observed:
                raise ValueError("row outside observation window")
            latest_row = max(latest_row, row_observed)
            for stat in STATS:
                value = row.get(stat)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError(f"invalid {stat} percent")
                if stat == "crit" and value > 100:
                    raise ValueError("crit exceeds probability ceiling")
                rating = row.get(RATINGS[stat])
                if isinstance(rating, bool) or not isinstance(rating, (int, float)) or not math.isfinite(rating) or rating < 0:
                    raise ValueError(f"invalid {stat} rating")
        modes = result["cohorts"].setdefault(spec_id, {})
        if latest_row != cohort_observed:
            raise ValueError("cohort observedAt summary mismatch")
        if cohort["mode"] in modes:
            raise ValueError("duplicate spec/mode cohort")
        modes[cohort["mode"]] = cohort

    if max(cohort["observedAt"] for modes in result["cohorts"].values() for cohort in modes.values()) != observed:
        raise ValueError("dataset observedAt summary mismatch")
    return result


def lua_value(value):
    if isinstance(value, dict):
        return "{" + ",".join(f"[{lua_value(k)}]={lua_value(v)}" for k, v in sorted(value.items(), key=lambda item: str(item[0]))) + "}"
    if isinstance(value, list):
        return "{" + ",".join(lua_value(item) for item in value) + "}"
    if isinstance(value, str):
        clean_text(value, "Lua text")
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return repr(value)
    raise ValueError("unsupported Lua value")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--raw-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = checked(json.loads(args.manifest.read_text(encoding="utf-8")), args.raw_source.read_bytes())
    args.output.write_text("-- Reviewed, authorized offline release dataset.\nStatCompass.releaseData = " + lua_value(data) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
