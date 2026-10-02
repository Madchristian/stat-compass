"""Synthetic Blizzard API cases; no real player identities are shipped in fixtures."""
import importlib.util
import json
from collections import Counter
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("blizzard_mplus", ROOT / "tools/providers/blizzard_mplus.py")
bz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bz)


def member(char_id, spec_id, realm="synthetic-realm"):
    return {"profile": {"name": f"Synthetic{char_id}", "id": char_id, "realm": {"id": 1, "slug": realm}},
            "faction": {"type": "HORDE"}, "specialization": {"id": spec_id}}


def group(level, rating, members, completed=1):
    return {"ranking": 1, "keystone_level": level, "duration": 1000, "completed_timestamp": completed,
            "mythic_rating": {"rating": rating}, "members": members}


def statistics(crit=20.0, haste=15.0, mastery=30.0, vers=8.0):
    return {"melee_crit": {"rating": 100, "value": crit - 5}, "spell_crit": {"rating_normalized": 900, "rating_bonus": crit - 5, "value": crit},
            "ranged_crit": {"rating": 100, "value": crit - 5},
            "melee_haste": {"rating": 700, "value": haste}, "spell_haste": {"rating": 700, "value": haste},
            "ranged_haste": {"rating": 700, "value": haste}, "mastery": {"rating": 800, "value": mastery},
            "versatility": 400, "versatility_damage_done_bonus": vers}


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls = responses, []
        self.requests, self.cache_hits, self.status_counts = 0, 0, Counter()

    def get(self, path, namespace):
        self.calls.append((path, namespace))
        self.requests += 1
        return self.responses.get(path)


def test_parse_dedupe_and_spec_ranking():
    board = {"leading_groups": [group(20, 450.0, [member(1, 62), member(2, 250)], completed=5),
                                group(18, 400.0, [member(1, 63), member(3, 62)], completed=6),
                                {"keystone_level": 15, "members": [{"profile": {"id": 9}}]}]}
    runs, rejected = bz.parse_leaderboard(board, 500, 1001)
    assert len(runs) == 2 and rejected == 2  # malformed member and the then empty group
    client = FakeClient({f"/data/wow/connected-realm/{r}/mythic-leaderboard/index": {"current_leaderboards": [{"id": 500}]} for r in (1, 2)}
                        | {f"/data/wow/connected-realm/{r}/mythic-leaderboard/500/period/1001": board for r in (1, 2)})
    ranker = bz.SpecRanker()
    stats = bz.scan(client, [1, 2], [1001], ranker, workers=2)
    assert ranker.runs == 4 and stats["present"] == Counter({1001: 2})
    second = {"dungeon": 501, "period": 1001, "level": 19, "rating": 420.0, "duration": 1, "completed": 7,
              "members": [{"id": 1, "name": "Synthetic1", "realm": "synthetic-realm", "spec": 62}]}
    ranker.add(second)
    ranking, fallback = ranker.ranking(), ranker.fallback  # duplicates from two boards do not inflate scores
    assert not fallback
    assert [r["id"] for r in ranking[62]] == [1, 3] and ranking[62][0]["score"] == 870.0
    assert ranking[63][0]["score"] == 400.0  # off-spec runs never leak into the main spec score


def test_missing_periods_and_fallback_metric():
    client = FakeClient({"/data/wow/connected-realm/1/mythic-leaderboard/index": {"current_leaderboards": [{"id": 500}]},
                         "/data/wow/connected-realm/1/mythic-leaderboard/500/period/1002":
                             {"leading_groups": [{"keystone_level": 12, "completed_timestamp": 1, "members": [member(1, 62)]}]}})
    ranker = bz.SpecRanker()
    stats = bz.scan(client, [1], [1001, 1002], ranker, workers=1)
    assert stats["missing"] == Counter({1001: 1}) and stats["present"] == Counter({1002: 1})
    assert stats["lowestLevel"] == Counter({12: 1})
    ranking, fallback = ranker.ranking(), ranker.fallback
    assert fallback and ranking[62][0]["score"] == 12.0


def test_extract_stats_uses_paperdoll_crit_and_rejects_incomplete():
    stats = bz.extract_stats(statistics())
    assert stats["crit"] == 20.0 and stats["haste"] == 15.0 and stats["mastery"] == 30.0 and stats["versatility"] == 8.0
    assert stats["ratings"] == {"crit": 900, "haste": 700, "mastery": 800, "versatility": 400}
    broken = statistics()
    broken["mastery"] = {"rating": 1, "value": float("nan")}
    assert bz.extract_stats(broken) is None
    assert bz.extract_stats(None) is None


def character(i, spec_id, *, valid=True, active=None, level=90, stats=True, ilvl=None, hero=(66, "Master of Harmony")):
    base = f"/profile/wow/character/synthetic-realm/synthetic{i}"
    out = {base + "/status": {"id": i, "is_valid": valid},
           base: {"id": i, "level": level, "active_spec": {"id": active or spec_id}, "equipped_item_level": ilvl or 700 + i},
           base + "/specializations": {"active_specialization": {"id": active or spec_id},
                                       "active_hero_talent_tree": {"id": hero[0], "name": hero[1]}}}
    if stats:
        out[base + "/statistics"] = statistics(crit=10.0 + i)
    return out


def test_verification_reasons_and_target_stop():
    rows = [{"id": i, "realm": "synthetic-realm", "name": f"Synthetic{i}", "score": 100 - i} for i in range(1, 8)]
    responses = {}
    responses |= character(1, 62)
    responses |= character(2, 62, valid=False)
    responses |= character(3, 62, active=63)
    responses |= character(4, 62, level=80)
    responses |= character(5, 62, stats=False)
    responses |= character(6, 62)
    responses |= character(7, 62)
    client = FakeClient(responses)
    valid, reasons, tried = bz.analyze_spec(client, rows, 62, target=2, max_candidates=10, max_level=90)
    assert [v["crit"] for v in valid] == [11.0, 16.0] and tried == 6
    assert reasons == Counter({"status": 1, "activeSpec": 1, "level": 1, "statistics": 1})
    # a missing (404) character and a changed character ID both mean "delete", never "use"
    responses["/profile/wow/character/synthetic-realm/synthetic1/status"] = {"id": 99, "is_valid": True}
    valid, reasons, _ = bz.analyze_spec(FakeClient(responses), rows[:1], 62, target=1, max_candidates=1, max_level=90)
    assert not valid and reasons == Counter({"status": 1})


def test_item_level_outliers_are_replaced_from_further_down():
    rows = [{"id": i, "realm": "synthetic-realm", "name": f"Synthetic{i}", "score": 100 - i} for i in range(1, 7)]
    responses = {}
    for i, ilvl in zip(range(1, 7), (330, 279, 331, 329, 332, 290)):
        responses |= character(i, 62, ilvl=ilvl)
    valid, reasons, tried = bz.analyze_spec(FakeClient(responses), rows, 62, target=3, max_candidates=6, max_level=90)
    assert [v["itemLevel"] for v in valid] == [330, 331, 329] and reasons == Counter({"itemLevel": 1}) and tried == 4
    valid, reasons, _ = bz.analyze_spec(FakeClient(responses), rows, 62, target=3, max_candidates=6, max_level=90, ilvl_gap=0)
    assert [v["itemLevel"] for v in valid] == [330, 279, 331] and not reasons


def test_report_is_identity_free_and_flags_thin_specs():
    rows = [{"id": i, "realm": "synthetic-realm", "name": f"Synthetic{i}", "score": 100 - i} for i in range(1, 4)]
    responses = {}
    for i in range(1, 4):
        responses |= character(i, 62)
    client = FakeClient(responses)
    client.status_counts.update({200: 5, 404: 1, "transport": 2})  # mixed keys must not break the report
    verified = {62: bz.analyze_spec(client, rows, 62, target=3, max_candidates=3, max_level=90)}
    report = bz.build_report(season_id=17, periods=[1001], realms=[1], specs={62: {"name": "Arcane", "class": "Mage", "role": "DAMAGE"},
                             250: {"name": "Blood", "class": "Death Knight", "role": "TANK"}},
                             scan_stats={"leaderboardRequests": 1, "missing": Counter(), "present": Counter({1001: 1}),
                                         "sizes": Counter({500: 1}), "rejected": 0, "dungeons": [500]},
                             ranking={62: rows}, fallback=False, verified=verified, target=3, minimum=2, client=client)
    text = json.dumps(report)
    assert "Synthetic" not in text and "synthetic-realm" not in text
    arcane = next(s for s in report["specs"] if s["specId"] == 62)
    blood = next(s for s in report["specs"] if s["specId"] == 250)
    assert arcane["enough"] and arcane["statRanges"]["crit"] == [11.0, 13.0] and arcane["scoreAtTarget"] == 97
    assert not blood["enough"] and blood["rankedCharacters"] == 0
    assert report["specsEnough"] == 1 and report["leaderboards"]["atLargestSize"] == 1
    assert report["httpStatus"] == {"200": 5, "404": 1, "transport": 2}


class Response(BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Opener:
    def __init__(self, outcomes):
        self.outcomes, self.requests = list(outcomes), []

    def open(self, request, timeout):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, int):
            raise HTTPError(request.full_url, outcome, "synthetic", {"Retry-After": "1"}, None)
        return Response(json.dumps(outcome).encode())


def test_client_transport_bounds(tmp_path):
    sleeps = []
    opener = Opener([429, {"ok": 1}, 404])
    client = bz.Client("token", opener=opener, sleep=sleeps.append, clock=lambda: 0.0, rps=1)
    assert client.get("/data/wow/mythic-keystone/season/index", "dynamic-eu") == {"ok": 1}
    assert client.get("/data/wow/mythic-keystone/season/1", "dynamic-eu") is None
    assert 1 in sleeps and client.status_counts == Counter({429: 1, 200: 1, 404: 1})
    assert opener.requests[0].get_header("Authorization") == "Bearer token"
    assert "access_token" not in opener.requests[0].full_url
    for path, namespace in (("/oauth/token", "dynamic-eu"), ("/data/wow/../x", "dynamic-eu"), ("/data/wow/x", "profile-us")):
        with pytest.raises(bz.BlizzardError):
            client.get(path, namespace)
    with pytest.raises(bz.BlizzardError, match="outside the repository"):
        bz.Client("token", cache_dir=ROOT / "cache")
    cached = bz.Client("token", opener=Opener([{"cached": True}]), cache_dir=tmp_path, clock=lambda: 0.0, sleep=lambda s: None)
    assert cached.get("/data/wow/connected-realm/index", "dynamic-eu") == {"cached": True}
    assert cached.get("/data/wow/connected-realm/index", "dynamic-eu") == {"cached": True} and cached.cache_hits == 1
    budget = bz.Client("token", opener=Opener([{}, {}]), max_requests=1, clock=lambda: 0.0, sleep=lambda s: None)
    budget.get("/data/wow/connected-realm/index", "dynamic-eu")
    with pytest.raises(bz.BlizzardError, match="budget"):
        budget.get("/data/wow/connected-realm/1", "dynamic-eu")


def test_env_file_fills_only_missing_blizzard_keys(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('﻿BLIZZARD_CLIENT_ID=abc\nBLIZZARD_CLIENT_SECRET="s=cret"\nPATH=evil\n# comment\n', encoding="utf-8")
    environ = {"BLIZZARD_CLIENT_ID": "from-shell"}
    bz.load_env_file(env_file, environ)
    assert environ == {"BLIZZARD_CLIENT_ID": "from-shell", "BLIZZARD_CLIENT_SECRET": "s=cret"}
    bz.load_env_file(tmp_path / "missing.env", environ)


def test_env_file_is_git_ignored():
    assert ".env" in (ROOT / ".gitignore").read_text(encoding="utf-8").split()


def test_character_path_encodes_names():
    assert bz.character_path("Die-Aldor", "Ärztin", "/status") == "/profile/wow/character/die-aldor/%C3%A4rztin/status"


def season_profile(char_id, spec_runs):
    """spec_runs: [(dungeon, rating, spec, timed)]"""
    return {"character": {"id": char_id}, "best_runs": [
        {"dungeon": {"id": d}, "mythic_rating": {"rating": r}, "is_completed_within_time": timed,
         "members": [{"character": {"id": char_id}, "specialization": {"id": spec}}]} for d, r, spec, timed in spec_runs]}


def certifier_fixture(profiles, *, floors, target=2, extra=None):
    ranker = bz.SpecRanker()
    # board facts: char 1 strong on both dungeons, char 2 only one dungeon (its other run fell off a full board)
    for run in [dict(dungeon=1, rating=400.0, level=20, members=[dict(id=1, name="Synthetic1", realm="synthetic-realm", realmId=11, spec=62)]),
                dict(dungeon=2, rating=390.0, level=20, members=[dict(id=1, name="Synthetic1", realm="synthetic-realm", realmId=11, spec=62)]),
                dict(dungeon=1, rating=420.0, level=21, members=[dict(id=2, name="Synthetic2", realm="synthetic-realm", realmId=11, spec=62)]),
                dict(dungeon=1, rating=380.0, level=19, members=[dict(id=3, name="Synthetic3", realm="synthetic-realm", realmId=11, spec=62)]),
                dict(dungeon=2, rating=380.0, level=19, members=[dict(id=3, name="Synthetic3", realm="synthetic-realm", realmId=11, spec=62)])] + (extra or []):
        ranker.add(dict(run, period=1, duration=1, completed=1))
    responses = {}
    for i in (1, 2, 3, 4):
        responses |= character(i, 62, ilvl=330)
    for char_id, payload in profiles.items():
        responses[f"/profile/wow/character/synthetic-realm/synthetic{char_id}/mythic-keystone-profile/season/18"] = payload
    bounds, cap = bz.board_bounds(floors)
    client = FakeClient(responses)
    return bz.Certifier(client, ranker, [1, 2], bounds, {11: 100}, season_id=18, max_level=90, ilvl_gap=10), client


def test_board_bounds_only_count_full_boards():
    bounds, cap = bz.board_bounds([(100, 1, 500, 300.0), (100, 1, 500, 350.0), (100, 2, 120, 200.0), (101, 1, 499, 10.0)])
    assert cap == 500 and bounds == {(100, 1): 350.0}


def test_certifier_finds_run_hidden_by_truncated_board():
    # char 2's dungeon-2 run (410) fell off a full board; the profile reveals it and lifts char 2 to rank 1
    profiles = {2: season_profile(2, [(1, 420.0, 62, True), (2, 410.0, 62, True)]),
                3: season_profile(3, [(1, 380.0, 62, True), (2, 380.0, 62, True)]),
                1: season_profile(1, [(1, 400.0, 62, True), (2, 390.0, 62, True)])}
    cert, client = certifier_fixture(profiles, floors=[(100, 2, 500, 395.0), (100, 1, 500, 370.0)])
    observations, reasons, info = cert.run(62, target=2)
    assert [o["score"] for o in observations] == [830.0, 790.0]
    assert all(o["exact"] for o in observations)
    assert info["certified"] and info["openAboveThreshold"] == 0 and info["threshold"] == 790.0
    assert info["unseenBound"] == 765.0  # 370 + 395: a character with no listed run cannot reach 790


def test_certifier_refuses_certificate_when_an_unseen_player_could_win():
    profiles = {c: season_profile(c, [(1, 400.0, 62, True), (2, 390.0, 62, True)]) for c in (1, 2, 3)}
    cert, _ = certifier_fixture(profiles, floors=[(100, 1, 500, 450.0), (100, 2, 500, 450.0)])
    _, _, info = cert.run(62, target=2)
    assert not info["certified"] and info["unseenBound"] == 900.0


def test_off_spec_best_run_keeps_interval_open_until_ruled_out():
    # char 3's best dungeon-2 run was played in another spec: in-spec value is only bounded, not known
    profiles = {1: season_profile(1, [(1, 400.0, 62, True), (2, 390.0, 62, True)]),
                2: season_profile(2, [(1, 420.0, 62, True)]),
                3: season_profile(3, [(1, 380.0, 62, True), (2, 450.0, 63, True)])}
    cert, _ = certifier_fixture(profiles, floors=[(100, 2, 500, 445.0)])  # a full board could hide up to 445
    observations, _, info = cert.run(62, target=1)
    assert [o["score"] for o in observations] == [790.0]
    assert info["openAboveThreshold"] == 1 and not info["certified"]  # 380 + up to 450 > 790
    assert bz.season_profile_bounds(profiles[3], 3, 62) == ({1: 380.0}, {1: 380.0, 2: 450.0}, 0.0)


def test_pre_filter_drops_weak_runs_but_keeps_bounds_safe():
    ranker = bz.SpecRanker(min_rating=300.0)
    ranker.add(dict(dungeon=1, rating=250.0, level=8, period=1, duration=1, completed=1,
                    members=[dict(id=5, name="Synthetic5", realm="synthetic-realm", realmId=11, spec=62)]))
    ranker.add(dict(dungeon=1, rating=450.0, level=20, period=1, duration=1, completed=2,
                    members=[dict(id=5, name="Synthetic5", realm="synthetic-realm", realmId=11, spec=62)]))
    ranker.add(dict(dungeon=2, rating=280.0, level=9, period=1, duration=1, completed=3,
                    members=[dict(id=6, name="Synthetic6", realm="synthetic-realm", realmId=11, spec=62)]))
    assert ranker.dropped == 2 and ranker.runs == 1 and (62, 6) not in ranker.best
    cert = bz.Certifier(FakeClient({}), ranker, [1, 2], {}, {11: 100}, season_id=18, max_level=90, ilvl_gap=10)
    lower, upper = cert.interval(62, 5)
    assert lower == 450.0 and upper == 750.0  # the dropped dungeon-2 slot may still hold up to the filter rating
    assert cert.unseen_bound() == 600.0


class TimeoutOpener(Opener):
    def open(self, request, timeout):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if outcome == "timeout":
            raise TimeoutError("The read operation timed out")
        if outcome == "truncated":
            return Response(b'{"leading_groups": [')
        return Response(json.dumps(outcome).encode())


def test_read_timeouts_and_truncated_bodies_are_retried():
    sleeps = []
    client = bz.Client("token", opener=TimeoutOpener(["timeout", "truncated", {"ok": 2}]), sleep=sleeps.append, clock=lambda: 0.0)
    assert client.get("/data/wow/connected-realm/index", "dynamic-eu") == {"ok": 2}
    assert client.status_counts["transport"] == 2 and [s for s in sleeps if s >= 1] == [1, 2]  # backoff, not pacing
    failing = bz.Client("token", opener=TimeoutOpener(["timeout"] * 3), sleep=lambda s: None, clock=lambda: 0.0)
    with pytest.raises(bz.BlizzardError, match="network"):
        failing.get("/data/wow/connected-realm/index", "dynamic-eu")


def test_state_round_trip_and_invalidation(tmp_path):
    ranker = bz.SpecRanker(min_rating=300.0)
    ranker.add(dict(dungeon=7, rating=450.0, level=20, period=1, duration=1, completed=1,
                    members=[dict(id=5, name="Synthetic5", realm="synthetic-realm", realmId=11, spec=62)]))
    path = tmp_path / "state.json.gz"
    bz.save_state(path, ranker, season_id=18, closed={1076, 1077}, floors=[(100, 7, 500, 401.5)], dungeons=[7],
                  created_at=1800000000, heroes={5: (62, 39, "Spellslinger")}, hero_times={5: 1800000100})
    loaded, closed, floors, dungeons, created, heroes, times = bz.load_state(path, season_id=18, min_rating=300.0,
                                                                             now=1800000000 + 86400)
    assert heroes == {5: (62, 39, "Spellslinger")} and times == {5: 1800000100}
    assert loaded.best == {(62, 5): {7: 450.0}} and loaded.identity == {5: ("synthetic-realm", "Synthetic5", 11)}
    assert closed == {1076, 1077} and floors == [(100, 7, 500, 401.5)] and dungeons == [7] and created == 1800000000
    assert bz.load_state(path, season_id=19, min_rating=300.0, now=1800000000) is None  # new season
    assert bz.load_state(path, season_id=18, min_rating=250.0, now=1800000000) is None  # different pre-filter
    assert bz.load_state(path, season_id=18, min_rating=300.0, now=1800000000 + 28 * 86400) is None  # 30-day rule
    path.write_bytes(b"not gzip")
    assert bz.load_state(path, season_id=18, min_rating=300.0, now=1800000000) is None
    assert bz.load_state(None, season_id=18, min_rating=300.0, now=1800000000) is None


def test_job_summary_renders_report():
    from tests.test_tools import load_tool
    tool = load_tool("mplus_summary")
    report = {"season": 18, "specsEnough": 1, "specsTotal": 1, "minimum": 20, "requests": 10, "weeksFromState": 7,
              "specs": [{"class": "Mage", "spec": "Arcane", "valid": 30, "certification": {"certified": True, "threshold": 3925.1},
                         "statRanges": {"crit": [19.15, 30.07], "haste": None, "mastery": [18.1, 38.9], "versatility": [8.6, 18.3]}}]}
    text = tool.summary(report)
    assert "| Mage | Arcane | 30 | ✅ | 3925.1 | 19.15–30.07 | – |" in text and "7 weeks from cached state" in text


def test_workflow_keeps_identities_out_of_artifacts():
    workflow = (ROOT / ".github/workflows/refresh-mplus-data.yml").read_text(encoding="utf-8")
    assert "${{ runner.temp }}" not in workflow.split("steps:")[0]  # runner context is unavailable at job level
    assert "STATE_DIR" not in workflow.split("upload-artifact")[1]
    assert "secrets.BLIZZARD_CLIENT_SECRET" in workflow and "contents: read" in workflow.split("jobs:")[0]


def test_hero_cohorts_split_and_drop_thin_trees():
    profiles = {c: season_profile(c, [(1, 400.0 - c, 62, True), (2, 390.0 - c, 62, True)]) for c in (1, 2, 3, 4)}
    ranker = bz.SpecRanker()
    for c in (1, 2, 3, 4):
        for d in (1, 2):
            ranker.add(dict(dungeon=d, rating=400.0 - c - 10 * (d - 1), level=20, period=1, duration=1, completed=c,
                            members=[dict(id=c, name=f"Synthetic{c}", realm="synthetic-realm", realmId=11, spec=62)]))
    responses = {}
    for c, hero in ((1, (66, "Master of Harmony")), (2, (65, "Shado-Pan")), (3, (66, "Master of Harmony")), (4, (66, "Master of Harmony"))):
        responses |= character(c, 62, ilvl=330, hero=hero)
        responses[f"/profile/wow/character/synthetic-realm/synthetic{c}/mythic-keystone-profile/season/18"] = profiles[c]
    client = FakeClient(responses)
    cert = bz.Certifier(client, ranker, [1, 2], {}, {11: 100}, season_id=18, max_level=90, ilvl_gap=10)
    spec_rows, _, _ = cert.run(62, target=4)
    assert bz.hero_mix(spec_rows) == {"Master of Harmony": 3, "Shado-Pan": 1}
    harmony, reasons, info = cert.run(62, target=3, hero_id=66, minimum=2, max_walk=10)
    assert [r["heroTree"]["id"] for r in harmony] == [66, 66, 66] and [r["rank"] for r in harmony] == [1, 2, 3]
    assert reasons == Counter({"heroTree": 1}) and info["certified"]
    shado, _, info = cert.run(62, target=3, hero_id=65, minimum=2, max_walk=10)
    assert shado == [] and info["insufficient"] == 1  # one Shado-Pan player is no cohort
    statistics_calls = [p for p, _ in client.calls if p.endswith("/statistics")]
    assert len(statistics_calls) == len(set(statistics_calls)) == 4  # checks are cached across cohorts


def test_state_can_store_a_closed_week_snapshot(tmp_path):
    ranker = bz.SpecRanker()
    ranker.add(dict(dungeon=7, rating=450.0, level=20, period=1, duration=1, completed=1,
                    members=[dict(id=5, name="Synthetic5", realm="synthetic-realm", realmId=11, spec=62)]))
    closed_best = {key: dict(value) for key, value in ranker.best.items()}
    ranker.add(dict(dungeon=8, rating=470.0, level=21, period=2, duration=1, completed=2,
                    members=[dict(id=5, name="Synthetic5", realm="synthetic-realm", realmId=11, spec=62)]))
    path = tmp_path / "state.json.gz"
    bz.save_state(path, ranker, season_id=18, closed={1}, floors=[], dungeons=[7, 8], created_at=1800000000,
                  best=closed_best, identity=dict(ranker.identity))
    loaded = bz.load_state(path, season_id=18, min_rating=0.0, now=1800000000)[0]
    assert loaded.best == {(62, 5): {7: 450.0}}  # the current week's run is never cached as closed


def test_hero_popularity_counts_the_unbroken_top():
    rows = [{"id": i} for i in range(1, 7)]
    heroes = {1: (62, 39, "Spellslinger"), 2: (62, 39, "Spellslinger"), 3: (63, 40, "Sunfury"),  # 3 plays Fire now
              4: (62, 40, "Sunfury"), 6: (62, 40, "Sunfury")}  # 5 never looked up: the sample ends there
    assert bz.hero_popularity(rows, heroes, 62) == {"sample": 3, "trees": {"Spellslinger": 2, "Sunfury": 1}}
    from tests.test_tools import load_tool
    assert load_tool("mplus_summary").popularity({"sample": 4, "trees": {"Spellslinger": 3, "Sunfury": 1}}) == \
        "Spellslinger 75 %, Sunfury 25 % (top 4)"


def test_playable_specs_lists_official_hero_trees():
    client = FakeClient({"/data/wow/playable-specialization/index": {"character_specializations": [{"id": 62, "name": "Arcane"}]},
                         "/data/wow/playable-specialization/62": {"playable_class": {"name": "Mage"}, "role": {"type": "DAMAGE"},
                                                                  "hero_talent_trees": [{"id": 40, "name": "Sunfury"},
                                                                                        {"id": 39, "name": "Spellslinger"}]}})
    assert bz.playable_specs(client)[62]["heroTrees"] == [(39, "Spellslinger"), (40, "Sunfury")]
