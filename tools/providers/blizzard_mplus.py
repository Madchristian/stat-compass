"""Blizzard-only EU Mythic+ spec cohort analysis (local only, official Game Data and Profile APIs).

Pipeline: current season and its periods -> every EU connected realm -> every dungeon leaderboard
per period -> runs with member specialization -> per-spec score (sum of best run rating per dungeon
played in that spec) -> top candidates checked against status, character summary (active spec,
level) and statistics. The report contains counts and stat ranges only, no character identities.
"""
import argparse
import base64
import gzip
import http.client
import json
import math
import os
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_HOST = "eu.api.blizzard.com"
TOKEN_URL = "https://oauth.battle.net/token"
MAX_BYTES = 8 * 1024 * 1024
REPOSITORY = Path(__file__).resolve().parents[2]
STAT_KEYS = ("crit", "haste", "mastery", "versatility")


class BlizzardError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise BlizzardError("redirect refused")


def _read(response, max_bytes):
    body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise BlizzardError("response size limit")
    return json.loads(body)


def fetch_token(client_id, client_secret, *, opener=None, timeout=15):
    if not client_id or not client_secret:
        raise BlizzardError("BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET are required")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    request = Request(TOKEN_URL, data=b"grant_type=client_credentials", method="POST",
                      headers={"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with (opener or build_opener(NoRedirect())).open(request, timeout=timeout) as response:
            payload = _read(response, 64 * 1024)
    except HTTPError as exc:
        raise BlizzardError(f"token HTTP {exc.code}") from None
    except URLError:
        raise BlizzardError("network unavailable") from None
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise BlizzardError("token response without access_token")
    return token


def load_env_file(path, environ=os.environ):
    """Fill missing BLIZZARD_* variables from a git-ignored KEY=VALUE file; real environment wins."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() in ("BLIZZARD_CLIENT_ID", "BLIZZARD_CLIENT_SECRET") and not environ.get(key.strip()):
            environ[key.strip()] = value.strip().strip("\"'")


def api_url(path, namespace):
    if not path.startswith(("/data/wow/", "/profile/wow/character/")) or ".." in path or "?" in path:
        raise BlizzardError("path outside endpoint allowlist")
    if namespace not in ("static-eu", "dynamic-eu", "profile-eu"):
        raise BlizzardError("namespace outside allowlist")
    return f"https://{API_HOST}{path}?" + urlencode(dict(namespace=namespace, locale="en_GB"))


class Client:
    """Rate-limited, optionally cached GET client. 404 returns None (a documented, meaningful answer)."""

    def __init__(self, token, *, opener=None, cache_dir=None, max_requests=30000, rps=40, timeout=20,
                 max_attempts=3, wait_budget=120, sleep=time.sleep, clock=time.monotonic):
        if cache_dir is not None:
            cache_dir = Path(cache_dir).resolve()
            if cache_dir.is_relative_to(REPOSITORY):
                raise BlizzardError("cache holds character identities and must stay outside the repository")
        if not 0 < rps <= 90 or not 1 <= max_requests <= 36000 or not 1 <= max_attempts <= 5:
            raise BlizzardError("invalid transport bounds")
        self.token, self.opener, self.cache_dir = token, opener or build_opener(NoRedirect()), cache_dir
        self.max_requests, self.interval, self.timeout = max_requests, 1 / rps, timeout
        self.max_attempts, self.wait_budget, self.sleep, self.clock = max_attempts, wait_budget, sleep, clock
        self.lock, self.next_slot, self.requests, self.cache_hits = threading.Lock(), 0.0, 0, 0
        self.status_counts = Counter()

    def _cache_path(self, url):
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", urlsplit(url).path.strip("/") + "_" + urlsplit(url).query)
        return self.cache_dir / (name[:200] + ".json")

    def _slot(self):
        with self.lock:
            if self.requests >= self.max_requests:
                raise BlizzardError("request budget exhausted")
            self.requests += 1
            now = self.clock()
            wait = max(0.0, self.next_slot - now)
            self.next_slot = max(now, self.next_slot) + self.interval
        if wait:
            self.sleep(wait)

    def get(self, path, namespace):
        url = api_url(path, namespace)
        cached = self._cache_path(url) if self.cache_dir else None
        if cached and cached.exists():
            self.cache_hits += 1
            return json.loads(cached.read_text(encoding="utf-8"))["body"]
        for attempt in range(self.max_attempts):
            self._slot()
            try:
                request = Request(url, headers={"Authorization": "Bearer " + self.token, "Accept": "application/json",
                                                "User-Agent": "StatCompass-local-analysis/0.1"})
                with self.opener.open(request, timeout=self.timeout) as response:
                    if response.status != 200:
                        raise BlizzardError("unexpected status")
                    body = _read(response, MAX_BYTES)
                    self.status_counts[200] += 1
                    break
            except HTTPError as exc:
                self.status_counts[exc.code] += 1
                if exc.code == 404:
                    body = None
                    break
                if exc.code not in (429, 500, 502, 503, 504) or attempt + 1 == self.max_attempts:
                    raise BlizzardError(f"HTTP {exc.code} for {urlsplit(url).path}") from None
                delay = _retry_after(exc.headers.get("Retry-After", ""), default=2 ** attempt)
                if delay > self.wait_budget:
                    raise BlizzardError("retry wait budget exceeded") from None
                with self.lock:
                    self.wait_budget -= delay
                self.sleep(delay)
            except (URLError, OSError, http.client.HTTPException, json.JSONDecodeError):
                # HTTPError is handled above; this covers refused connections, read timeouts and truncated bodies
                self.status_counts["transport"] += 1
                if attempt + 1 == self.max_attempts:
                    raise BlizzardError("network unavailable") from None
                self.sleep(2 ** attempt)
        if cached:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps({"url": url, "body": body}, ensure_ascii=False), encoding="utf-8")
        return body


def _retry_after(value, default):
    if not value:
        return default
    if value.isdecimal():
        return int(value)
    try:
        return max(0, math.ceil((parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        raise BlizzardError("invalid Retry-After") from None


def _id(value):
    return value if type(value) is int and value > 0 else None


def _href_id(ref):
    href = ref.get("href") if isinstance(ref, dict) else None
    match = re.search(r"/(\d+)\?", href or "")
    return int(match.group(1)) if match else None


def current_season(client):
    index = client.get("/data/wow/mythic-keystone/season/index", "dynamic-eu")
    season_id = _id((index or {}).get("current_season", {}).get("id"))
    if not season_id:
        raise BlizzardError("no current season in season index")
    season = client.get(f"/data/wow/mythic-keystone/season/{season_id}", "dynamic-eu") or {}
    periods = sorted({p.get("id") for p in season.get("periods", []) if _id(p.get("id"))})
    if not periods:
        raise BlizzardError("season without periods")
    return season_id, periods


def eu_connected_realms(client):
    index = client.get("/data/wow/connected-realm/index", "dynamic-eu") or {}
    ids = sorted({i for i in map(_href_id, index.get("connected_realms", [])) if i})
    if not ids:
        raise BlizzardError("empty connected realm index")
    return ids


def playable_specs(client):
    index = client.get("/data/wow/playable-specialization/index", "static-eu") or {}
    specs = {}
    for ref in index.get("character_specializations", []):
        spec_id = _id(ref.get("id"))
        if not spec_id:
            continue
        detail = client.get(f"/data/wow/playable-specialization/{spec_id}", "static-eu") or {}
        specs[spec_id] = {"name": ref.get("name") or detail.get("name"),
                          "class": (detail.get("playable_class") or {}).get("name"),
                          "role": (detail.get("role") or {}).get("type")}
    if not specs:
        raise BlizzardError("empty specialization index")
    return specs


def parse_leaderboard(payload, dungeon_id, period):
    """Normalize one weekly leaderboard into run records; malformed members are counted, not guessed."""
    runs, rejected = [], 0
    for group in payload.get("leading_groups", []) if isinstance(payload, dict) else []:
        level, completed = group.get("keystone_level"), group.get("completed_timestamp")
        rating = (group.get("mythic_rating") or {}).get("rating")
        rating = rating if type(rating) in (int, float) and math.isfinite(rating) and rating >= 0 else None
        members = []
        for member in group.get("members", []):
            profile = member.get("profile") or {}
            realm = profile.get("realm") or {}
            char_id, spec_id = _id(profile.get("id")), _id((member.get("specialization") or {}).get("id"))
            if not char_id or not spec_id or not isinstance(profile.get("name"), str) or not isinstance(realm.get("slug"), str):
                rejected += 1
                continue
            members.append({"id": char_id, "name": profile["name"], "realm": realm["slug"], "realmId": _id(realm.get("id")),
                            "spec": spec_id})
        if type(level) is not int or level < 2 or not members:
            rejected += 1
            continue
        runs.append({"dungeon": dungeon_id, "period": period, "level": level, "rating": rating,
                     "duration": group.get("duration"), "completed": completed, "members": members})
    return runs, rejected


class SpecRanker:
    """Streaming per-spec score: sum over dungeons of the best run played in that spec.

    Taking the maximum is idempotent, so a run listed on several realm boards needs no dedupe.
    Uses the run's Blizzard mythic_rating when present; otherwise the keystone level (flagged)."""

    def __init__(self, min_rating=0.0):
        self.best, self.identity, self.fallback, self.runs = defaultdict(dict), {}, False, 0
        self.min_rating, self.dropped = min_rating, 0

    def add(self, run):
        value = run["rating"]
        if value is None:
            value, self.fallback = float(run["level"]), True
        elif value < self.min_rating:
            # Pre-filter: weak runs only matter far below any top cohort. Certification adds the
            # filter rating to every upper bound, so a dropped run can never hide a contender.
            self.dropped += 1
            return
        self.runs += 1
        for m in run["members"]:
            slot = self.best[(m["spec"], m["id"])]
            slot[run["dungeon"]] = max(slot.get(run["dungeon"], 0.0), value)
            self.identity[m["id"]] = (m["realm"], m["name"], m.get("realmId"))

    def ranking(self):
        ranking = defaultdict(list)
        for (spec_id, char_id), dungeons in self.best.items():
            realm, name, _ = self.identity[char_id]
            ranking[spec_id].append({"id": char_id, "realm": realm, "name": name,
                                     "score": round(sum(dungeons.values()), 3), "dungeons": len(dungeons)})
        for rows in ranking.values():
            rows.sort(key=lambda r: (-r["score"], r["id"]))
        return dict(ranking)


def rank_specs(runs):
    ranker = SpecRanker()
    for run in runs:
        ranker.add(run)
    return ranker.ranking(), ranker.fallback


def new_scan_stats():
    return {"leaderboardRequests": 0, "missing": Counter(), "present": Counter(), "sizes": Counter(),
            "rejected": 0, "lowestLevel": Counter(), "floors": [], "dungeons": []}


def scan(client, realms, periods, ranker, *, workers=8, progress=None, stats=None):
    """Fetch every realm x dungeon x period leaderboard and stream its runs into the ranker."""
    indexes = {}
    with ThreadPoolExecutor(workers) as pool:
        for realm, index in zip(realms, pool.map(lambda r: client.get(f"/data/wow/connected-realm/{r}/mythic-leaderboard/index", "dynamic-eu"), realms)):
            indexes[realm] = sorted({_id(b.get("id")) or _href_id(b.get("key")) for b in (index or {}).get("current_leaderboards", [])} - {None})
    dungeons = sorted({d for ds in indexes.values() for d in ds})
    jobs = [(r, d, p) for r in realms for d in (indexes[r] or dungeons) for p in periods]
    stats = stats if stats is not None else new_scan_stats()
    stats["leaderboardRequests"] += len(jobs)

    def one(job):
        realm, dungeon, period = job
        payload = client.get(f"/data/wow/connected-realm/{realm}/mythic-leaderboard/{dungeon}/period/{period}", "dynamic-eu")
        if payload is None:
            return job, None, 0, 0
        parsed, rejected = parse_leaderboard(payload, dungeon, period)
        return job, parsed, rejected, len(payload.get("leading_groups", []))

    with ThreadPoolExecutor(workers) as pool:
        for done, ((realm, dungeon, period), parsed, rejected, size) in enumerate(pool.map(one, jobs), 1):
            if progress and done % 500 == 0:
                progress(f"{done}/{len(jobs)} leaderboards")
            if parsed is None:
                stats["missing"][period] += 1
                continue
            stats["present"][period] += 1
            stats["sizes"][size] += 1
            stats["rejected"] += rejected
            if parsed:
                stats["lowestLevel"][min(r["level"] for r in parsed)] += 1
                ratings = [r["rating"] for r in parsed if r["rating"] is not None]
                stats["floors"].append((realm, dungeon, size, min(ratings) if ratings else None))
            for run in parsed:
                ranker.add(run)
    stats["dungeons"] = sorted(set(stats["dungeons"]) | set(dungeons))
    return stats


def board_bounds(floors, cap=None):
    """Highest rating a timed run could have and still be missing from a connected realm's boards.

    A board shorter than the cap lists every timed run, so it hides nothing. A full board hides only
    runs rated at most its lowest listed rating. Per (connected realm, dungeon) the bound is the
    maximum over all weeks. Cross-realm runs are listed on every member's connected realm board."""
    cap = cap or max((size for _, _, size, _ in floors), default=0)
    bounds = defaultdict(float)
    for realm, dungeon, size, floor in floors:
        if size >= cap:
            bounds[(realm, dungeon)] = max(bounds[(realm, dungeon)], floor if floor is not None else math.inf)
    return dict(bounds), cap


def realm_map(client, connected_realms):
    """Map realm IDs (as listed on members) to their connected realm ID."""
    mapping = {}
    for cr in connected_realms:
        for realm in (client.get(f"/data/wow/connected-realm/{cr}", "dynamic-eu") or {}).get("realms", []):
            if _id(realm.get("id")):
                mapping[realm["id"]] = cr
    return mapping


def season_profile_bounds(payload, char_id, spec_id):
    """Per-dungeon facts from the official season profile.

    Returns ({dungeon: best in-spec run rating}, {dungeon: best run rating in any spec}, max untimed rating).
    The season rating counts the best run per dungeon regardless of spec, so the any-spec best is an
    upper bound for the in-spec best; when that best run was played in the spec, the value is exact."""
    in_spec, any_spec, untimed = {}, {}, 0.0
    for run in (payload or {}).get("best_runs", []):
        dungeon = _id((run.get("dungeon") or {}).get("id"))
        rating = (run.get("mythic_rating") or {}).get("rating")
        if not dungeon or type(rating) not in (int, float) or not math.isfinite(rating) or rating < 0:
            continue
        any_spec[dungeon] = max(any_spec.get(dungeon, 0.0), rating)
        if run.get("is_completed_within_time") is False:
            untimed = max(untimed, rating)
        me = next((m for m in run.get("members", []) if (m.get("character") or {}).get("id") == char_id), None)
        if me and (me.get("specialization") or {}).get("id") == spec_id:
            in_spec[dungeon] = max(in_spec.get(dungeon, 0.0), rating)
    return in_spec, any_spec, untimed


class Certifier:
    """Exact top-k per spec with interval bounds.

    lower bound = sum over dungeons of the best known in-spec run (boards, then season profile)
    upper bound = sum over dungeons of the best value that could still be hidden:
                  before the profile: max(known, realm board floor, untimed ceiling)
                  after the profile:  max(known, best run of that dungeon in any spec)
    The cohort is certified when every unselected character not known to be ineligible has an
    upper bound not above the lowest selected lower bound, and an unseen character cannot reach it."""

    def __init__(self, client, ranker, dungeons, bounds, realm_to_cr, *, season_id, max_level, ilvl_gap,
                 max_profiles=600, workers=8):
        self.client, self.ranker, self.dungeons, self.bounds = client, ranker, dungeons, bounds
        self.realm_to_cr, self.season_id, self.max_level, self.ilvl_gap = realm_to_cr, season_id, max_level, ilvl_gap
        self.max_profiles, self.workers, self.untimed_ceiling = max_profiles, workers, 0.0
        self.lock, self.profiles, self.checks = threading.Lock(), {}, {}

    def profile(self, char_id):
        if char_id not in self.profiles:
            realm, name, _ = self.ranker.identity[char_id]
            payload = self.client.get(character_path(realm, name, f"/mythic-keystone-profile/season/{self.season_id}"), "profile-eu")
            if payload is not None and (payload.get("character") or {}).get("id") not in (None, char_id):
                payload = None  # renamed or recreated character: board facts stay the only evidence
            with self.lock:
                self.profiles[char_id] = payload
                self.untimed_ceiling = max(self.untimed_ceiling, season_profile_bounds(payload, char_id, 0)[2])
        return self.profiles[char_id]

    def interval(self, spec_id, char_id):
        known = self.ranker.best.get((spec_id, char_id), {})
        payload = self.profiles.get(char_id)
        if payload is not None:
            in_spec, any_spec, _ = season_profile_bounds(payload, char_id, spec_id)
            lower = {d: max(known.get(d, 0.0), in_spec.get(d, 0.0)) for d in self.dungeons}
            upper = {d: max(lower[d], any_spec.get(d, 0.0)) for d in self.dungeons}
        else:
            cr = self.realm_to_cr.get(self.ranker.identity[char_id][2])
            lower = {d: known.get(d, 0.0) for d in self.dungeons}
            upper = {d: max(lower[d], self.bounds.get((cr, d), 0.0) if cr else math.inf, self.untimed_ceiling,
                            self.ranker.min_rating) for d in self.dungeons}
        return sum(lower.values()), sum(upper.values())

    def unseen_bound(self):
        """Upper bound for a character with no in-spec run on any board (cannot be enumerated)."""
        crs = set(self.realm_to_cr.values()) or {None}
        return max(sum(max(self.bounds.get((cr, d), 0.0), self.untimed_ceiling, self.ranker.min_rating)
                       for d in self.dungeons) for cr in crs)

    def check(self, char_id, spec_id):
        key = (char_id, spec_id)
        if key not in self.checks:
            realm, name, _ = self.ranker.identity[char_id]
            stats, reason = verify(self.client, {"id": char_id, "realm": realm, "name": name}, spec_id, self.max_level)
            self.checks[key] = stats if stats is not None else reason
        return self.checks[key]

    def run(self, spec_id, *, target):
        chars = [c for (s, c) in self.ranker.best if s == spec_id]
        excluded, profiles_used = {}, 0
        while True:
            scored = {c: self.interval(spec_id, c) for c in chars}
            order = sorted(chars, key=lambda c: (-scored[c][0], c))
            chosen, walked, excluded = self._walk(order, spec_id, target)
            tau = scored[chosen[-1]][0] if len(chosen) == target else 0.0
            chosen_set = set(chosen)
            # selected players get their profile too, so their scores (and order) become exact
            unresolved = sorted((c for c in chars if c not in self.profiles and (c in chosen_set or (
                                 c not in excluded and scored[c][1] > tau))), key=lambda c: (-scored[c][1], c))
            if not unresolved or profiles_used >= self.max_profiles:
                break
            batch = unresolved[:self.max_profiles - profiles_used]
            with ThreadPoolExecutor(self.workers) as pool:
                list(pool.map(self.profile, batch))
            profiles_used += len(batch)
        # still above the threshold after the profile: only an eligibility check can rule them out
        open_chars = [c for c in chars if c not in chosen_set and c not in excluded and scored[c][1] > tau]
        if len(open_chars) <= 100:  # beyond that the bounds are too loose to be worth resolving one by one
            open_chars = [c for c in open_chars if isinstance(self.check(c, spec_id), dict)]
        reasons = Counter(excluded.values())
        observations = [dict(self.check(c, spec_id), rank=i, score=round(scored[c][0], 3),
                             exact=scored[c][0] == scored[c][1]) for i, c in enumerate(chosen, 1)]
        unseen = self.unseen_bound()
        return observations, reasons, {
            "threshold": round(tau, 3), "candidatesTried": walked, "profilesFetched": profiles_used,
            "openAboveThreshold": len(open_chars), "unseenBound": round(unseen, 3),
            "exactScores": sum(o["exact"] for o in observations),
            "certified": len(chosen) == target and not open_chars and unseen <= tau}

    def _walk(self, order, spec_id, target):
        """Walk the ranking by lower bound; ineligible players are replaced from further down."""
        picked, excluded, walked = [], {}, 0
        for c in order:
            if len(self._item_level_filter(picked, spec_id)) >= target:
                break
            walked += 1
            result = self.check(c, spec_id)
            if isinstance(result, dict):
                picked.append(c)
            else:
                excluded[c] = result
        kept = self._item_level_filter(picked, spec_id)
        for c in set(picked) - set(kept):
            excluded[c] = "itemLevel"
        return kept[:target], walked, excluded

    def _item_level_filter(self, picked, spec_id):
        levels = [self.checks[(c, spec_id)]["itemLevel"] for c in picked if type(self.checks[(c, spec_id)]["itemLevel"]) is int]
        floor = _median(levels) - self.ilvl_gap if levels and self.ilvl_gap else None
        return [c for c in picked if floor is None or (type(self.checks[(c, spec_id)]["itemLevel"]) is int
                                                       and self.checks[(c, spec_id)]["itemLevel"] >= floor)]


STATE_VERSION = 1
STATE_MAX_AGE = 27 * 86400  # identities may be kept at most 30 days under Blizzard's terms


def current_period(client):
    index = client.get("/data/wow/mythic-keystone/period/index", "dynamic-eu") or {}
    period = _id((index.get("current_period") or {}).get("id"))
    if not period:
        raise BlizzardError("no current period")
    return period


def save_state(path, ranker, *, season_id, closed, floors, dungeons, created_at):
    """Aggregated best runs of closed weeks. Contains character identities: private cache only."""
    payload = {"version": STATE_VERSION, "season": season_id, "createdAt": created_at, "minRating": ranker.min_rating,
               "closed": sorted(closed), "dungeons": sorted(dungeons), "floors": floors,
               "best": [[spec, char, {str(d): r for d, r in dungeons_.items()}] for (spec, char), dungeons_ in ranker.best.items()],
               "identity": {str(c): list(v) for c, v in ranker.identity.items()}}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    tmp.replace(path)


def load_state(path, *, season_id, min_rating, now):
    """Return (ranker, closed periods, floors, dungeons, createdAt) or None when unusable."""
    if path is None or not path.is_file():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    if (payload.get("version") != STATE_VERSION or payload.get("season") != season_id
            or payload.get("minRating") != min_rating or not isinstance(payload.get("createdAt"), int)
            or now - payload["createdAt"] > STATE_MAX_AGE):
        return None
    ranker = SpecRanker(min_rating=min_rating)
    for spec, char, dungeons in payload["best"]:
        ranker.best[(spec, char)] = {int(d): r for d, r in dungeons.items()}
    ranker.identity = {int(c): tuple(v) for c, v in payload["identity"].items()}
    floors = [tuple(f) for f in payload["floors"]]
    return ranker, set(payload["closed"]), floors, payload["dungeons"], payload["createdAt"]


def _pct(block):
    value = block.get("value") if isinstance(block, dict) else block
    return float(value) if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def _rating(block):
    value = (block.get("rating_normalized", block.get("rating"))) if isinstance(block, dict) else block
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def extract_stats(payload):
    """Map the statistics summary onto the four Character-window secondaries.

    Crit follows the PaperDoll rule (highest of melee/ranged/spell). Mastery `value` semantics
    (effect percent vs. mastery points) are unverified and kept separately from the rating."""
    if not isinstance(payload, dict):
        return None
    crits = [c for c in (_pct(payload.get(k)) for k in ("melee_crit", "ranged_crit", "spell_crit")) if c is not None]
    hastes = [h for h in (_pct(payload.get(k)) for k in ("melee_haste", "ranged_haste", "spell_haste")) if h is not None]
    out = {"crit": max(crits) if crits else None, "haste": max(hastes) if hastes else None,
           "mastery": _pct(payload.get("mastery")), "versatility": _pct(payload.get("versatility_damage_done_bonus")),
           "ratings": {"crit": max([r for r in (_rating(payload.get(k)) for k in ("melee_crit", "ranged_crit", "spell_crit")) if r is not None], default=None),
                       "haste": max([r for r in (_rating(payload.get(k)) for k in ("melee_haste", "ranged_haste", "spell_haste")) if r is not None], default=None),
                       "mastery": _rating(payload.get("mastery")), "versatility": _rating(payload.get("versatility"))},
           "hasteSpread": (max(hastes) - min(hastes)) if hastes else None}
    return out if all(out[k] is not None for k in STAT_KEYS) else None


def character_path(realm, name, suffix=""):
    return f"/profile/wow/character/{quote(realm.lower(), safe='')}/{quote(name.lower(), safe='')}{suffix}"


def verify(client, row, spec_id, max_level):
    """Return (stats, None) for a usable observation or (None, reason)."""
    status = client.get(character_path(row["realm"], row["name"], "/status"), "profile-eu")
    if status is None or status.get("is_valid") is not True or status.get("id") != row["id"]:
        return None, "status"
    summary = client.get(character_path(row["realm"], row["name"]), "profile-eu")
    if summary is None:
        return None, "summary"
    if (summary.get("active_spec") or {}).get("id") != spec_id:
        return None, "activeSpec"
    if max_level and summary.get("level") != max_level:
        return None, "level"
    stats = extract_stats(client.get(character_path(row["realm"], row["name"], "/statistics"), "profile-eu"))
    if stats is None:
        return None, "statistics"
    stats["itemLevel"] = summary.get("equipped_item_level")
    stats["observedAt"] = int(time.time())
    return stats, None


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def analyze_spec(client, rows, spec_id, *, target, max_candidates, max_level, ilvl_gap=10):
    """Collect usable observations in ranking order until `target` survive the item level filter.

    A ranked player currently wearing far weaker gear than the cohort (e.g. an alt or PvP set)
    would alone define a minimum; observations below median item level minus `ilvl_gap` are dropped
    and the walk continues further down the ranking. The median is robust to those outliers."""
    valid, reasons, tried = [], Counter(), 0

    def split():
        levels = [v["itemLevel"] for v in valid if type(v["itemLevel"]) is int]
        floor = _median(levels) - ilvl_gap if levels and ilvl_gap else None
        keep = [v for v in valid if floor is None or (type(v["itemLevel"]) is int and v["itemLevel"] >= floor)]
        return keep, len(valid) - len(keep)

    for row in rows[:max_candidates]:
        if len(split()[0]) >= target:
            break
        tried += 1
        stats, reason = verify(client, row, spec_id, max_level)
        if reason:
            reasons[reason] += 1
        else:
            valid.append({"rank": tried, "score": row["score"], **stats})
    keep, dropped = split()
    if dropped:
        reasons["itemLevel"] += dropped
    return keep[:target], reasons, tried


def _range(values):
    values = [v for v in values if v is not None]
    return [round(min(values), 2), round(max(values), 2)] if values else None


def build_report(*, season_id, periods, realms, specs, scan_stats, ranking, fallback, verified, target, minimum, client):
    rows = []
    for spec_id, meta in sorted(specs.items(), key=lambda kv: ((kv[1]["class"] or ""), kv[1]["name"] or "")):
        ranked = ranking.get(spec_id, [])
        valid, reasons, cert = verified.get(spec_id, ([], Counter(), {}))
        tried = cert.get("candidatesTried", 0) if isinstance(cert, dict) else cert
        rows.append({"specId": spec_id, "class": meta["class"], "spec": meta["name"], "role": meta["role"],
                     "rankedCharacters": len(ranked),
                     "scoreAtTarget": ranked[target - 1]["score"] if len(ranked) >= target else None,
                     "candidatesTried": tried, "valid": len(valid), "excluded": dict(reasons),
                     "enough": len(valid) >= minimum,
                     "certification": cert if isinstance(cert, dict) else None,
                     "statRanges": {k: _range([v[k] for v in valid]) for k in STAT_KEYS},
                     "statMeans": {k: round(sum(v[k] for v in valid) / len(valid), 2) if valid else None for k in STAT_KEYS},
                     "ratingRanges": {k: _range([v["ratings"][k] for v in valid]) for k in STAT_KEYS},
                     "itemLevelRange": _range([v["itemLevel"] for v in valid])})
    sizes = scan_stats["sizes"]
    return {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "region": "EU",
            "season": season_id, "periods": periods, "connectedRealms": len(realms), "dungeons": scan_stats["dungeons"],
            "leaderboards": {"requested": scan_stats["leaderboardRequests"], "present": sum(scan_stats["present"].values()),
                             "missingByPeriod": {str(k): v for k, v in sorted(scan_stats["missing"].items())},
                             "largestSize": max(sizes) if sizes else 0,
                             "atLargestSize": sizes[max(sizes)] if sizes else 0,
                             "rejectedRecords": scan_stats["rejected"],
                             "lowestKeyLevelPerBoard": {str(k): v for k, v in sorted(scan_stats.get("lowestLevel", {}).items())}},
            "rankingMetric": "keystone level fallback (no run rating)" if fallback else
                             "sum of best run mythic_rating per dungeon, played as the spec",
            "target": target, "minimum": minimum,
            "specsEnough": sum(r["enough"] for r in rows), "specsTotal": len(rows),
            "requests": client.requests, "cacheHits": client.cache_hits,
            "weeksFromState": scan_stats.get("weeksFromState", 0),
            "httpStatus": {str(k): v for k, v in sorted(client.status_counts.items())},
            "specs": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", type=int, default=30, help="valid observations wanted per spec")
    parser.add_argument("--minimum", type=int, default=20, help="valid observations that count as enough")
    parser.add_argument("--max-candidates", type=int, default=60, help="ranked characters checked per spec")
    parser.add_argument("--max-level", type=int, default=90, help="required character level (0 disables)")
    parser.add_argument("--min-run-rating", type=float, default=300.0,
                        help="ignore leaderboard runs rated below this; it is added to every upper bound, so results stay exact")
    parser.add_argument("--max-profiles", type=int, default=600, help="season profiles fetched per spec to tighten bounds")
    parser.add_argument("--observations", type=Path, help="identity-free per-spec observations for the Data.lua generator")
    parser.add_argument("--ilvl-gap", type=int, default=10, help="drop observations below cohort median item level minus this (0 disables)")
    parser.add_argument("--periods", type=int, default=0, help="only the last N season periods (0 = all)")
    parser.add_argument("--realms", type=int, default=0, help="only the first N connected realms (0 = all, for smoke tests)")
    parser.add_argument("--max-requests", type=int, default=30000)
    parser.add_argument("--rps", type=float, default=40)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--state", type=Path, help="gzip state of closed weeks (identities!) for incremental runs; private cache only")
    parser.add_argument("--cache-dir", type=Path, help="raw responses incl. identities; outside the repo, delete within 30 days")
    parser.add_argument("--output", type=Path, help="write the identity-free JSON report here")
    args = parser.parse_args()
    if not 1 <= args.minimum <= args.target <= args.max_candidates <= 200:
        parser.error("require 1 <= minimum <= target <= max-candidates <= 200")
    log = lambda message: print(message, file=sys.stderr, flush=True)
    load_env_file(REPOSITORY / ".env")
    client = Client(fetch_token(os.environ.get("BLIZZARD_CLIENT_ID"), os.environ.get("BLIZZARD_CLIENT_SECRET")),
                    cache_dir=args.cache_dir, max_requests=args.max_requests, rps=args.rps)
    season_id, periods = current_season(client)
    if args.periods:
        periods = periods[-args.periods:]
    realms = eu_connected_realms(client)
    if args.realms:
        realms = realms[:args.realms]
    if args.state and args.state.resolve().is_relative_to(REPOSITORY):
        parser.error("the state holds character identities and must stay outside the repository")
    if args.state and (args.periods or args.realms):
        parser.error("--state needs the full scan; do not combine it with --periods or --realms")
    specs = playable_specs(client)
    log(f"season {season_id}, {len(periods)} periods, {len(realms)} connected realms, {len(specs)} specs")
    now = int(time.time())
    week = current_period(client)
    closed = [p for p in periods if p < week]
    state = load_state(args.state, season_id=season_id, min_rating=args.min_run_rating, now=now)
    scan_stats = new_scan_stats()
    if state:
        ranker, done, floors, dungeons, created_at = state
        scan_stats["floors"], scan_stats["dungeons"] = list(floors), list(dungeons)
        log(f"state from {datetime.fromtimestamp(created_at, timezone.utc):%Y-%m-%d}: {len(done)} closed weeks cached")
    else:
        ranker, done, created_at = SpecRanker(min_rating=args.min_run_rating), set(), now
    todo = [p for p in closed if p not in done]
    if todo:
        scan(client, realms, todo, ranker, workers=args.workers, progress=log, stats=scan_stats)
    if args.state:
        # saved before the current week is added: only finished weeks are reusable
        save_state(args.state, ranker, season_id=season_id, closed=done | set(todo), floors=scan_stats["floors"],
                   dungeons=scan_stats["dungeons"], created_at=created_at)
    current = [p for p in periods if p >= week]
    scan(client, realms, current, ranker, workers=args.workers, progress=log, stats=scan_stats)
    scan_stats["weeksFromState"] = len(done & set(closed))
    log(f"pre-filter kept {ranker.runs} and dropped {ranker.dropped} new entries below rating {args.min_run_rating}")
    ranking, fallback = ranker.ranking(), ranker.fallback
    log(f"{ranker.runs} leaderboard entries; certifying top {args.target} per spec")
    if fallback:
        raise BlizzardError("leaderboards without run ratings cannot be certified")
    bounds, cap = board_bounds(scan_stats["floors"])
    certifier = Certifier(client, ranker, scan_stats["dungeons"], bounds, realm_map(client, realms),
                          season_id=season_id, max_level=args.max_level, ilvl_gap=args.ilvl_gap,
                          max_profiles=args.max_profiles, workers=args.workers)
    # a first pass over the strongest profiles sets a realistic untimed ceiling before bounds are used
    seed = sorted({c for s in specs for c in [r["id"] for r in ranking.get(s, [])[:5]]})
    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(certifier.profile, seed))
    log(f"board cap {cap}, untimed ceiling {certifier.untimed_ceiling:.1f}")
    verified = {}
    with ThreadPoolExecutor(4) as pool:
        futures = {s: pool.submit(certifier.run, s, target=args.target) for s in specs}
        for s, f in futures.items():
            verified[s] = f.result()
            log(f"spec {s}: {verified[s][2]}")
    report = build_report(season_id=season_id, periods=periods, realms=realms, specs=specs, scan_stats=scan_stats,
                          ranking=ranking, fallback=fallback, verified=verified, target=args.target,
                          minimum=args.minimum, client=client)
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if args.observations:
        if args.observations.resolve().is_relative_to(REPOSITORY / "StatCompass"):
            parser.error("observations never go into the addon folder")
        args.observations.write_text(json.dumps({
            "season": season_id, "periods": periods, "generatedAt": report["generatedAt"],
            "rankingMetric": "sum over dungeons of the best in-spec run mythic_rating (Blizzard season rules), exact top-k",
            "specs": {str(s): {"certification": verified[s][2], "observations": verified[s][0]} for s in specs}},
            ensure_ascii=False), encoding="utf-8")
    if args.output:
        if args.output.resolve().is_relative_to(REPOSITORY / "StatCompass"):
            parser.error("reports never go into the addon folder")
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    try:
        main()
    except BlizzardError as exc:
        print(f"analysis blocked: {exc}", file=sys.stderr)
        sys.exit(2)
