"""Automatic data release planning (issue #10): 120-hour cadence, gate, version, changelog pair."""
import json
import time

import pytest

from tests.test_tools import load_tool
from tests.test_blizzard_dataset import observations

DAY = 86400
SHA = "a" * 40


def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def release(tag, published, assets=("StatCompass-2026.10.3.zip",), draft=False):
    return {"tag_name": tag, "draft": draft, "published_at": iso(published),
            "assets": [{"name": name, "state": "uploaded"} for name in assets]}


def dataset(tmp_path, now, specs=36):
    build, generator = load_tool("build_data"), load_tool("blizzard_dataset")
    source = observations(**{str(100 + s): 30 for s in range(specs)})
    for entry in source["specs"].values():
        for row in entry["observations"]:
            row["observedAt"] = now - 600
    manifest, _ = generator.manifest(source, interface=120100, client_build=69933, level=90, now=now)
    data = build.checked(manifest, json.dumps(source).encode(), now=now)
    path = tmp_path / "Data.lua"
    path.write_text("StatCompass.releaseData = " + build.lua_value(data) + "\n", encoding="utf-8")
    return path


REPORT = {"season": 18, "periods": [1076, 1083], "specsEnough": 40, "specsTotal": 40,
          "httpStatus": {"200": 8800, "404": 3, "transport": 12},
          "specs": [{"heroCohorts": {"66": {"valid": 30}, "65": {"valid": 4}}}]}


def test_cadence_is_120_hours_since_the_last_published_release():
    tool = load_tool("data_release")
    now = 1_800_000_000
    assert tool.due([], now)["due"] is False                                    # first release by hand
    assert tool.due([release("v2026.10.3", now - 4 * DAY)], now)["due"] is False
    assert tool.due([release("v2026.10.3", now - 5 * DAY)], now)["due"] is True
    drafts = [release("v2026.10.9", now - DAY, draft=True), release("v2026.10.3", now - 6 * DAY)]
    assert tool.due(drafts, now)["due"] is True                                 # drafts do not count


def test_versions_are_calver_with_same_day_suffix():
    tool = load_tool("data_release")
    now = int(time.mktime((2026, 10, 8, 12, 0, 0, 0, 0, 0)))
    assert tool.next_version(["v2026.10.3"], now) == "2026.10.8"
    assert tool.next_version(["v2026.10.8", "v2026.10.8-2"], now) == "2026.10.8-3"


def test_prepare_writes_a_pair_the_changelog_generator_accepts(tmp_path, monkeypatch):
    tool = load_tool("data_release")
    now = int(time.time())
    out = tmp_path / "changelog"
    out.mkdir()
    result = tool.prepare([release("v2026.10.3", now - 6 * DAY)], REPORT, dataset(tmp_path, now), ["v2026.10.3"],
                          SHA, now, out_dir=out)
    assert result["release"] and result["tag"] == "v" + result["version"] and len(result["idempotencyKey"]) == 64
    generator = load_tool("generate_changelog")
    monkeypatch.setattr(generator, "SOURCE", out)
    notes = generator.load()[result["version"]]
    assert "week 1083 of season 18" in notes["en"] and "36 specializations" not in notes["en"]
    assert "40 Spezialisierungen und 1 Heldentalente" in notes["de"]
    assert "—" not in notes["en"] + notes["de"]


def test_prepare_is_not_due_before_120_hours(tmp_path):
    tool = load_tool("data_release")
    now = int(time.time())
    result = tool.prepare([release("v2026.10.3", now - 2 * DAY)], REPORT, dataset(tmp_path, now), [], SHA, now,
                          out_dir=tmp_path)
    assert result["release"] is False and not list(tmp_path.glob("CHANGELOG-*"))


@pytest.mark.parametrize("change, message", [
    (lambda r, rep, d: (r.clear(), None), "first release"),                       # no release yet
    (lambda r, rep, d: r.__setitem__(0, release("v2026.10.3", r[0]["published_at_epoch"], assets=())), "quality|verified"),
    (lambda r, rep, d: rep.__setitem__("specsEnough", 20), "quality"),
    (lambda r, rep, d: rep.__setitem__("httpStatus", {"200": 10, "500": 1}), "quality"),
    (lambda r, rep, d: d.write_text(d.read_text(encoding="utf-8") + '\n-- ["realm"]="x"\n', encoding="utf-8"), "quality"),
])
def test_prepare_blocks_on_any_missing_fact(tmp_path, change, message):
    tool = load_tool("data_release")
    now = int(time.time())
    releases = [release("v2026.10.3", now - 6 * DAY)]
    releases[0]["published_at_epoch"] = now - 6 * DAY
    report = json.loads(json.dumps(REPORT))
    data = dataset(tmp_path, now)
    change(releases, report, data)
    with pytest.raises(tool.release_gate.GateBlocked, match=message):
        tool.prepare(releases, report, data, [], SHA, now, out_dir=tmp_path)
    assert not list(tmp_path.glob("CHANGELOG-*"))
