"""Synthetic provider cases; no player identities are shipped in fixtures."""
import importlib.util
import json
from pathlib import Path

import pytest
from urllib.error import HTTPError
from io import BytesIO
from datetime import datetime, timezone
from email.utils import format_datetime

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rio_rivals", ROOT / "tools/providers/rio_rivals.py")
rio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rio)


def entry(rank, hidden=False):
    return dict(rank=rank, name=f"Synthetic{rank}", realm="Anonymous" if hidden else "Synthetic Realm",
                realmSlug=None if hidden else "synthetic-realm", regionSlug=None if hidden else "eu",
                score=1000-rank, classId=8, specId=62,
                regionRankingPath=None if hidden else "/mythic-plus-spec-rankings/test-season/eu/mage/arcane")


def window(anchor, ranks, hidden=(), page=""):
    return dict(rivals=dict(scope="region", specId=62, selfRank=anchor,
        fullRankingPath="/mythic-plus-spec-rankings/test-season/eu/mage/arcane" + page,
        entries=[entry(r, r in hidden) for r in ranks]))


def test_synthetic_non_rank_one_seed_walk_and_hidden_slots():
    windows = {r: window(r, range(max(1, r-2), min(53, r+3)), hidden={15, 38, 40, 49}, page="/1" if r >= 20 else "") for r in range(1, 53) if r not in {15, 38, 40, 49}}
    called = []
    def fetch(realm, name):
        rank = int(name.removeprefix("Synthetic"))
        called.append(rank)
        return windows[rank]
    result = rio.collect(fetch, "synthetic-realm", "Synthetic22", season="test-season", class_slug="mage", spec_slug="arcane", class_id=8, spec_id=62, cutoff=50, max_requests=60)
    assert result["coveredRanks"] == list(range(1, 51))
    assert result["hiddenRanks"] == [15, 38, 40, 49]
    assert result["publicCount"] == 46 and result["strict50Eligible"] is False
    assert min(called) == 1 and max(called) >= 50
    assert not set(called) & {15, 38, 40, 49}


def test_synthetic_overlap_drift_and_schema_rejected():
    a = window(1, range(1, 6))
    b = window(5, range(3, 8))
    b["rivals"]["entries"][0]["score"] = 1111
    with pytest.raises(rio.AcquisitionError, match="overlap"):
        rio.collect(lambda realm, name: a if name == "Synthetic1" else b,
                    "synthetic-realm", "Synthetic1", season="test-season", class_slug="mage", spec_slug="arcane", class_id=8, spec_id=62, max_requests=2)
    for change in (lambda w: w["rivals"].update(scope="realm"),
                   lambda w: w["rivals"].update(fullRankingPath="/mythic-plus-spec-rankings/other/eu/mage/arcane"),
                   lambda w: w["rivals"]["entries"][0].update(score=float("nan")),
                   lambda w: w["rivals"]["entries"][0].update(classId=9)):
        w = window(1, range(1, 6))
        change(w)
        with pytest.raises(rio.AcquisitionError):
            rio.collect(lambda *_: w, "synthetic-realm", "Synthetic1", season="test-season", class_slug="mage", spec_slug="arcane", class_id=8, spec_id=62)


def test_synthetic_blocked_traversal_and_request_bound():
    w = window(4, range(2, 7), hidden={2, 3})
    with pytest.raises(rio.AcquisitionError, match="blocked"):
        rio.collect(lambda *_: w, "synthetic-realm", "Synthetic4", season="test-season", class_slug="mage", spec_slug="arcane", class_id=8, spec_id=62)
    with pytest.raises(rio.AcquisitionError, match="request budget"):
        rio.collect(lambda *_: window(1, range(1, 6)), "synthetic-realm", "Synthetic1", season="test-season", class_slug="mage", spec_slug="arcane", class_id=8, spec_id=62, max_requests=1)


def test_synthetic_transport_allowlist_size_redirect_and_retry():
    url = rio.request_url("synthetic-realm", "Synthetic1", 62)
    assert "scope=region" in url and "specId=62" in url
    with pytest.raises(rio.AcquisitionError, match="allowlist"):
        rio.get_json("https://other.invalid/api/v1/client/character-rivals")
    class Reply:
        status = 200
        def __init__(self, body, final=url): self.body, self.final = body, final
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def geturl(self): return self.final
        def read(self, limit): return self.body[:limit]
    class Opener:
        def __init__(self, replies): self.replies = iter(replies)
        def open(self, *_args, **_kwargs):
            item = next(self.replies)
            if isinstance(item, Exception): raise item
            return item
    with pytest.raises(rio.AcquisitionError, match="size"):
        rio.get_json(url, opener=Opener([Reply(b"x" * 12)]), max_bytes=10)
    with pytest.raises(rio.AcquisitionError, match="origin"):
        rio.get_json(url, opener=Opener([Reply(b"{}", "https://other.invalid/")]))
    rate = HTTPError(url, 429, "rate", {"Retry-After": "6"}, BytesIO())
    with pytest.raises(rio.AcquisitionError, match="budget"):
        rio.get_json(url, opener=Opener([rate]), wait_budget=5)
    sleeps = []
    rate = HTTPError(url, 429, "rate", {"Retry-After": "2"}, BytesIO())
    assert rio.get_json(url, opener=Opener([rate, Reply(b"{}")]), sleep=sleeps.append) == {}
    assert sleeps == [2]


def test_synthetic_retry_after_http_date_and_safe_network_error():
    url = rio.request_url("synthetic-realm", "Synthetic1", 62)
    from urllib.error import URLError
    class Opener:
        def __init__(self, items): self.items = iter(items)
        def open(self, *_args, **_kwargs):
            item = next(self.items)
            if isinstance(item, Exception): raise item
            return item
    when = format_datetime(datetime(2030, 1, 1, 0, 0, 2, tzinfo=timezone.utc), usegmt=True)
    rate = HTTPError(url, 429, "rate", {"Retry-After": when}, BytesIO())
    class Reply:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def geturl(self): return url
        def read(self, _): return b"{}"
    sleeps = []
    assert rio.get_json(url, opener=Opener([rate, Reply()]), sleep=sleeps.append,
                        clock=lambda: datetime(2030, 1, 1, tzinfo=timezone.utc)) == {}
    assert sleeps == [2]
    with pytest.raises(rio.AcquisitionError, match="network unavailable"):
        rio.get_json(url, opener=Opener([URLError("secret-containing-network-detail")]))


def test_synthetic_transport_rejects_extra_query_or_credentials():
    url = rio.request_url("synthetic-realm", "Synthetic1", 62)
    with pytest.raises(rio.AcquisitionError, match="allowlist"):
        rio.get_json(url + "&access_key=synthetic-secret")
    with pytest.raises(rio.AcquisitionError, match="allowlist"):
        rio.get_json(url.replace("scope=region", "scope=realm"))


def test_synthetic_raw_directory_cannot_be_inside_repository(monkeypatch):
    unsafe = ROOT / "hermes/cache/scratch/synthetic"
    monkeypatch.setattr("sys.argv", ["rio", "--realm", "synthetic-realm", "--name", "Synthetic1",
        "--spec-id", "62", "--class-id", "8", "--class-slug", "mage", "--spec-slug", "arcane",
        "--season", "test-season", "--raw-dir", str(unsafe)])
    def no_network(*_args, **_kwargs):
        raise AssertionError("unsafe raw path reached transport")
    monkeypatch.setattr(rio, "get_json", no_network)
    with pytest.raises(SystemExit) as exc:
        rio.main()
    assert exc.value.code == 2


def test_synthetic_duplicate_public_identity_across_ranks_rejected():
    windows = {r: window(r, range(max(1, r-2), min(8, r+3))) for r in range(1, 7)}
    windows[5]["rivals"]["entries"][-1]["name"] = "Synthetic1"
    with pytest.raises(rio.AcquisitionError, match="duplicate identity"):
        rio.collect(lambda realm, name: windows[int(name.removeprefix("Synthetic"))],
                    "synthetic-realm", "Synthetic1", season="test-season", class_slug="mage", spec_slug="arcane",
                    class_id=8, spec_id=62, cutoff=5, max_requests=10)
