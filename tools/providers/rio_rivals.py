"""Bounded Raider.IO published spec leaderboard window acquisition (local only)."""
import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOST = "raider.io"
PATH = "/api/v1/client/character-rivals"
MAX_BYTES = 256 * 1024


class AcquisitionError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise AcquisitionError("redirect refused")


def request_url(realm, name, spec_id):
    if not all(isinstance(x, str) and x and not any(ord(c) < 32 for c in x) for x in (realm, name)):
        raise AcquisitionError("invalid public seed")
    if type(spec_id) is not int or not 0 < spec_id < 1000000:
        raise AcquisitionError("invalid spec ID")
    return "https://raider.io" + PATH + "?" + urlencode(dict(region="eu", realm=realm, name=name, scope="region", specId=spec_id))


def get_json(url, *, opener=None, timeout=10, max_bytes=MAX_BYTES, max_attempts=2, wait_budget=5, sleep=time.sleep, clock=lambda: datetime.now(timezone.utc)):
    parts = urlsplit(url)
    if (parts.scheme, parts.hostname, parts.path, parts.port, parts.username, parts.password, parts.fragment) != ("https", HOST, PATH, None, None, None, ""):
        raise AcquisitionError("URL outside endpoint allowlist")
    query = parse_qsl(parts.query, keep_blank_values=True)
    if [key for key, _ in query] != ["region", "realm", "name", "scope", "specId"] or query[0][1] != "eu" or query[3][1] != "region" or not query[4][1].isdecimal() or request_url(query[1][1], query[2][1], int(query[4][1])) != url:
        raise AcquisitionError("URL outside endpoint allowlist")
    if not 0 < timeout <= 30 or not 0 < max_bytes <= MAX_BYTES or not 1 <= max_attempts <= 3 or not 0 <= wait_budget <= 30:
        raise AcquisitionError("invalid transport bounds")
    opener = opener or build_opener(NoRedirect())
    for attempt in range(max_attempts):
        try:
            with opener.open(Request(url, headers={"Accept": "application/json", "User-Agent": "StatCompass-local-acquisition/0.1"}), timeout=timeout) as response:
                if response.geturl() != url or response.status != 200:
                    raise AcquisitionError("unexpected response origin or status")
                body = response.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise AcquisitionError("response size limit")
                return json.loads(body)
        except HTTPError as exc:
            if exc.code != 429 or attempt + 1 == max_attempts:
                raise AcquisitionError(f"HTTP {exc.code}") from None
            retry = exc.headers.get("Retry-After", "")
            try:
                delay = int(retry) if retry.isdecimal() else max(0, math.ceil((parsedate_to_datetime(retry) - clock()).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                raise AcquisitionError("invalid Retry-After") from None
            if delay > wait_budget:
                raise AcquisitionError("retry wait budget exceeded") from None
            sleep(delay)
            wait_budget -= delay
        except URLError:
            raise AcquisitionError("network unavailable") from None
    raise AcquisitionError("retry attempts exhausted")


def _validated(payload, season, class_slug, spec_slug, class_id, spec_id):
    rivals = payload.get("rivals") if isinstance(payload, dict) else None
    if not isinstance(rivals, dict):
        raise AcquisitionError("missing rivals window")
    base = f"/mythic-plus-spec-rankings/{season}/eu/{class_slug}/{spec_slug}"
    path = rivals.get("fullRankingPath")
    if rivals.get("scope") != "region" or rivals.get("specId") != spec_id or not isinstance(path, str) or not re.fullmatch(re.escape(base) + r"(?:/[0-9]+)?", path):
        raise AcquisitionError("scope/spec/season ranking path mismatch")
    rows = rivals.get("entries")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 5:
        raise AcquisitionError("invalid window size")
    last_rank, last_score, normalized = 0, math.inf, []
    for row in rows:
        if not isinstance(row, dict):
            raise AcquisitionError("invalid entry")
        rank, score = row.get("rank"), row.get("score")
        if type(rank) is not int or rank <= last_rank or rank < 1 or type(score) not in (int, float) or not math.isfinite(score) or score > last_score or row.get("specId") != spec_id or row.get("classId") != class_id:
            raise AcquisitionError("invalid rank, score, class or spec")
        if last_rank and rank != last_rank + 1:
            raise AcquisitionError("rank gap inside window")
        hidden = row.get("realm") == "Anonymous" and row.get("realmSlug") is None and row.get("regionSlug") is None and row.get("regionRankingPath") is None
        if not hidden:
            if row.get("regionSlug") != "eu" or row.get("regionRankingPath") != base or not isinstance(row.get("name"), str) or not row["name"] or not isinstance(row.get("realmSlug"), str) or not row["realmSlug"]:
                raise AcquisitionError("identity or region mismatch")
        normalized.append({"rank": rank, "score": score, "hidden": hidden,
                           "key": None if hidden else ("eu", row["realmSlug"].casefold(), row["name"].casefold()),
                           "realm": None if hidden else row["realmSlug"], "name": None if hidden else row["name"]})
        last_rank, last_score = rank, score
    if rivals.get("selfRank") not in [r["rank"] for r in normalized]:
        raise AcquisitionError("seed rank absent")
    return normalized, rivals["selfRank"]


def collect(fetch, seed_realm, seed_name, *, season, class_slug, spec_slug, class_id, spec_id, cutoff=50, max_requests=60):
    if type(cutoff) is not int or not 1 <= cutoff <= 100 or type(max_requests) is not int or not 1 <= max_requests <= 100:
        raise AcquisitionError("invalid traversal bounds")
    rows, anchors, requested = {}, {}, set()
    def visit(realm, name):
        if len(requested) >= max_requests:
            raise AcquisitionError("request budget exhausted")
        key = (realm.casefold(), name.casefold())
        if key in requested:
            raise AcquisitionError("anchor loop")
        requested.add(key)
        found, self_rank = _validated(fetch(realm, name), season, class_slug, spec_slug, class_id, spec_id)
        self_row = next(r for r in found if r["rank"] == self_rank)
        if self_row["hidden"] or self_row["key"] != ("eu", *key):
            raise AcquisitionError("seed identity mismatch")
        for row in found:
            rank = row["rank"]
            if rank in rows and (rows[rank]["key"], rows[rank]["score"], rows[rank]["hidden"]) != (row["key"], row["score"], row["hidden"]):
                raise AcquisitionError("overlap drift")
            rows[rank] = row
            if not row["hidden"]:
                anchors[rank] = (row["realm"], row["name"])
        return self_rank
    current = visit(seed_realm, seed_name)
    while current != 1:
        candidates = [r for r in anchors if r < current and (anchors[r][0].casefold(), anchors[r][1].casefold()) not in requested]
        if not candidates:
            raise AcquisitionError("blocked upward traversal")
        previous = min(rows)
        current = visit(*anchors[min(candidates)])
        if min(rows) >= previous and current != 1:
            raise AcquisitionError("no upward progress")
    while max(rows) <= cutoff or any(r not in rows for r in range(1, cutoff+1)):
        candidates = [r for r in anchors if r > current and (anchors[r][0].casefold(), anchors[r][1].casefold()) not in requested]
        if not candidates:
            raise AcquisitionError("blocked downward traversal")
        previous = max(rows)
        current = visit(*anchors[max(candidates)])
        if max(rows) <= previous:
            raise AcquisitionError("no downward progress")
    ordered = [rows[r] for r in range(1, cutoff+1)]
    public = [r for r in ordered if not r["hidden"]]
    all_public = [r for r in rows.values() if not r["hidden"]]
    if len({r["key"] for r in all_public}) != len(all_public):
        raise AcquisitionError("duplicate identity")
    if any(ordered[i]["score"] < ordered[i+1]["score"] for i in range(len(ordered)-1)) or rows[cutoff+1]["score"] > rows[cutoff]["score"]:
        raise AcquisitionError("cross-window score order drift")
    return {"coveredRanks": list(range(1, cutoff+1)), "hiddenRanks": [r["rank"] for r in ordered if r["hidden"]],
            "publicCount": len(public), "strict50Eligible": cutoff == 50 and len(public) == 50,
            "cutoffWitnessRank": cutoff+1, "requestCount": len(requested), "intervalCollection": True,
            "publicEntries": public}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--spec-id", type=int, required=True)
    parser.add_argument("--class-id", type=int, required=True)
    parser.add_argument("--class-slug", required=True)
    parser.add_argument("--spec-slug", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--max-requests", type=int, default=60)
    parser.add_argument("--raw-dir", type=Path, help="scratch-only raw responses; never package or commit")
    args = parser.parse_args()
    if args.raw_dir:
        raw = args.raw_dir.resolve()
        scratch = (Path.home() / "AppData/Local/hermes/cache/scratch").resolve()
        repository = Path(__file__).resolve().parents[2]
        if not raw.is_relative_to(scratch) or raw.is_relative_to(repository):
            parser.error("raw output must be inside the user's Hermes scratch, outside the repository")
    counter = 0
    def fetch(realm, name):
        nonlocal counter
        payload = get_json(request_url(realm, name, args.spec_id))
        if args.raw_dir:
            args.raw_dir.mkdir(parents=True, exist_ok=True)
            (args.raw_dir / f"window-{counter:03}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        counter += 1
        return payload
    result = collect(fetch, args.realm, args.name, season=args.season, class_slug=args.class_slug,
                     spec_slug=args.spec_slug, class_id=args.class_id, spec_id=args.spec_id, max_requests=args.max_requests)
    result.pop("publicEntries")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except AcquisitionError as exc:
        print(f"acquisition blocked: {exc}", file=sys.stderr)
        sys.exit(2)
