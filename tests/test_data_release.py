"""Automatic data release planning (issue #10): weekly cadence, gate, version, changelog pair."""
import json
import time
from datetime import datetime, timezone
import os
import subprocess
import sys
import textwrap
import shlex

import pytest

from tests.test_tools import ROOT, load_tool
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


def utc(text):
    return int(datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())


@pytest.mark.parametrize("now, published, expected, next_due", [
    ("2026-10-07T06:29:59Z", "2026-10-04T17:00:51Z", False, "2026-10-07T06:30:00Z"),
    ("2026-10-07T06:30:00Z", "2026-10-04T17:00:51Z", True, "2026-10-07T06:30:00Z"),
    ("2026-10-08T12:00:00Z", "2026-10-04T17:00:51Z", True, "2026-10-07T06:30:00Z"),
    ("2026-10-07T12:00:00Z", "2026-10-07T06:30:00Z", False, "2026-10-14T06:30:00Z"),
    ("2026-10-13T23:59:59Z", "2026-10-07T15:00:00Z", False, "2026-10-14T06:30:00Z"),
    ("2026-10-14T06:30:00Z", "2026-10-13T23:59:59Z", True, "2026-10-14T06:30:00Z"),
    ("2026-10-28T06:30:00Z", "2026-10-25T17:00:51Z", True, "2026-10-28T06:30:00Z"),
    ("2027-01-06T06:30:00Z", "2026-12-31T17:00:51Z", True, "2027-01-06T06:30:00Z"),
])
def test_weekly_release_window_and_late_catch_up(now, published, expected, next_due):
    tool = load_tool("data_release")
    result = tool.due([release("synthetic-release", utc(published))], utc(now))
    assert result["due"] is expected
    assert result["nextDueAt"] == utc(next_due)


def test_weekly_planning_ignores_drafts_and_requires_a_first_release():
    tool = load_tool("data_release")
    now = utc("2026-10-07T12:00:00Z")
    assert tool.due([], now)["due"] is False
    releases = [release("synthetic-draft", now, draft=True),
                release("synthetic-release", utc("2026-10-04T17:00:51Z"))]
    assert tool.due(releases, now)["due"] is True


@pytest.mark.parametrize("automatic, event, published, refreshed, expected", [
    (True, "schedule", "2026-10-04T17:00:51Z", "2026-10-04T12:00:00Z", (True, True)),
    (True, "schedule", "2026-10-07T07:00:00Z", "2026-10-07T06:47:00Z", (False, False)),
    (True, "workflow_dispatch", "2026-10-07T07:00:00Z", "2026-10-07T06:47:00Z", (True, False)),
    (False, "schedule", "2026-10-04T17:00:51Z", "2026-10-04T12:00:00Z", (True, False)),
    (False, "schedule", "2026-10-04T17:00:51Z", "2026-10-07T06:47:00Z", (False, False)),
])
def test_plan_respects_automatic_switch_and_skips_completed_week(automatic, event, published, refreshed, expected):
    tool = load_tool("data_release")
    # Thursday execution must still catch up a missing Wednesday.
    result = tool.plan([release("synthetic-release", utc(published))], utc("2026-10-08T12:00:00Z"),
                       automatic=automatic, event=event, last_refresh=utc(refreshed))
    assert (result["refresh"], result["release_due"]) == expected


def test_plan_does_not_bootstrap_a_release_or_refresh_before_the_window():
    tool = load_tool("data_release")
    now = utc("2026-10-07T06:29:59Z")
    previous = utc("2026-10-01T12:00:00Z")
    assert tool.plan([], now, automatic=True, last_refresh=previous)["release_due"] is False
    result = tool.plan([release("synthetic-release", previous)], now,
                       automatic=False, last_refresh=previous)
    assert (result["refresh"], result["release_due"]) == (False, False)


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
    result = tool.prepare([release("v2026.10.3", now - 8 * DAY)], REPORT, dataset(tmp_path, now), ["v2026.10.3"],
                          SHA, now, out_dir=out)
    assert result["release"] and result["tag"] == "v" + result["version"] and len(result["idempotencyKey"]) == 64
    generator = load_tool("generate_changelog")
    monkeypatch.setattr(generator, "SOURCE", out)
    notes = generator.load()[result["version"]]
    assert "week 1083 of season 18" in notes["en"] and "36 specializations" not in notes["en"]
    assert "40 Spezialisierungen und 1 Heldentalente" in notes["de"]
    assert "—" not in notes["en"] + notes["de"]


def test_prepare_does_not_publish_twice_in_the_same_reset_week(tmp_path):
    tool = load_tool("data_release")
    now = int(time.time())
    result = tool.prepare([release("v2026.10.3", now - 600)], REPORT, dataset(tmp_path, now), [], SHA, now,
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
    releases = [release("v2026.10.3", now - 8 * DAY)]
    releases[0]["published_at_epoch"] = now - 8 * DAY
    report = json.loads(json.dumps(REPORT))
    data = dataset(tmp_path, now)
    change(releases, report, data)
    with pytest.raises(tool.release_gate.GateBlocked, match=message):
        tool.prepare(releases, report, data, [], SHA, now, out_dir=tmp_path)
    assert not list(tmp_path.glob("CHANGELOG-*"))


def test_prepare_publishes_after_reset_even_with_a_recent_sunday_release(tmp_path):
    tool = load_tool("data_release")
    now = utc("2026-10-07T12:00:00Z")
    result = tool.prepare([release("synthetic-release", utc("2026-10-04T17:00:51Z"))],
                          REPORT, dataset(tmp_path, now), [], SHA, now, out_dir=tmp_path)
    assert result["release"] is True and result["tag"] == "v2026.10.7"
    assert len(list(tmp_path.glob("CHANGELOG-*"))) == 2


@pytest.mark.parametrize("automatic, event, new_release, new_data, expected", [
    ("true", "schedule", False, False, "refresh=true\nrelease_due=true\n"),
    ("true", "schedule", True, True, "refresh=false\nrelease_due=false\n"),
    ("false", "schedule", False, True, "refresh=false\nrelease_due=false\n"),
    ("false", "schedule", False, False, "refresh=true\nrelease_due=false\n"),
    ("true", "workflow_dispatch", True, True, "refresh=true\nrelease_due=false\n"),
])
def test_workflow_decide_step_emits_real_job_outputs(tmp_path, automatic, event, new_release, new_data, expected):
    # Run the actual workflow shell block and production CLIs. Only GitHub's network boundary is fake.
    lines = (ROOT / ".github/workflows/refresh-mplus-data.yml").read_text().splitlines()
    decide = lines.index("      - name: Decide")
    start = lines.index("        run: |", decide) + 1
    end = next(i for i in range(start, len(lines)) if lines[i].strip() and not lines[i].startswith("          "))
    script = textwrap.dedent("\n".join(lines[start:end]))
    now = int(time.time())
    published = now if new_release else now - 8 * DAY
    refreshed = now if new_data else now - 8 * DAY
    responses = {
        "repos/synthetic/repo/releases?per_page=30": [release("synthetic-release", published)],
        "repos/synthetic/repo/actions/workflows/refresh-mplus-data.yml/runs?branch=main&status=success&per_page=30": {
            "workflow_runs": [{"id": 1, "conclusion": "success", "head_branch": "main", "created_at": iso(refreshed)}]},
        "repos/synthetic/repo/actions/runs/1/artifacts": {"artifacts": [{"name": "mplus-data-1", "expired": False}]},
    }
    fixture = tmp_path / "github.json"
    fixture.write_text(json.dumps(responses))
    binaries = tmp_path / "bin"
    binaries.mkdir()
    python = binaries / "python"
    python.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n')
    python.chmod(0o755)
    gh = binaries / "gh"
    gh.write_text(f"#!{sys.executable}\nimport json,os,sys\n"
                  "with open(os.environ['GITHUB_FIXTURE']) as fixture:\n"
                  "    print(json.dumps(json.load(fixture)[sys.argv[-1]]))\n")
    gh.chmod(0o755)
    output, summary = tmp_path / "output", tmp_path / "summary"
    env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ["PATH"], AUTO=automatic,
               GITHUB_EVENT_NAME=event, GITHUB_REPOSITORY="synthetic/repo", GITHUB_FIXTURE=str(fixture),
               RUNNER_TEMP=str(tmp_path), GITHUB_OUTPUT=str(output), GITHUB_STEP_SUMMARY=str(summary))
    result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script], cwd=ROOT, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert output.read_text() == expected
    assert "release window:" in summary.read_text()
