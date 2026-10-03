"""Release tooling: bilingual changelog generator, release data check, packaging configuration."""
import json
import textwrap
import time
from zipfile import ZipFile

import pytest

from tests.test_tools import ROOT, load_tool
from tests.test_blizzard_dataset import observations


def generator(tmp_path, monkeypatch, files):
    tool = load_tool("generate_changelog")
    source = tmp_path / "changelog"
    source.mkdir()
    for name, text in files.items():
        (source / name).write_text(text, encoding="utf-8")
    monkeypatch.setattr(tool, "SOURCE", source)
    monkeypatch.setattr(tool, "OUTPUT", tmp_path / "CHANGELOG.md")
    return tool


def pair(version, en="Better targets for tanks.", de="Bessere Ziele für Tanks."):
    return {f"CHANGELOG-{version}-en.md": f"# Stat Compass {version}\n\n## Changes\n\n{en}\n",
            f"CHANGELOG-{version}-de.md": f"# Stat Compass {version}\n\n## Änderungen\n\n{de}\n"}


def test_changelog_renders_newest_first_english_then_german(tmp_path, monkeypatch):
    tool = generator(tmp_path, monkeypatch, pair("2026.10.3") | pair("2026.10.10", "Hero talents.", "Heldentalente."))
    text = tool.render(tool.load())
    assert text.index("## 2026.10.10") < text.index("## 2026.10.3")           # numeric, not text order
    block = text[text.index("## 2026.10.10"):text.index("## 2026.10.3")]
    assert block.index("### English") < block.index("Hero talents.") < block.index("### Deutsch") < block.index("Heldentalente.")
    assert "#### Changes" in block                                             # note headings demoted


@pytest.mark.parametrize("files, message", [
    ({"CHANGELOG-2026.10.3-en.md": "# Stat Compass 2026.10.3\n\nText here.\n"}, "needs both"),
    ({"CHANGELOG-2026.10.3-en.md": "# Stat Compass 2026.10.3\n\nSame text.\n",
      "CHANGELOG-2026.10.3-de.md": "# Stat Compass 2026.10.3\n\nSame text.\n"}, "identical"),
    ({"CHANGELOG-2026.10.3-en.md": "# Wrong 2026.10.3\n\nText.\n",
      "CHANGELOG-2026.10.3-de.md": "# Stat Compass 2026.10.3\n\nText.\n"}, "first line"),
    ({"notes.md": "x"} | pair("2026.10.3"), "unexpected file"),
    ({"CHANGELOG-2026.10.3-en.md": "# Stat Compass 2026.10.3\n\n## Only a heading\n",
      "CHANGELOG-2026.10.3-de.md": "# Stat Compass 2026.10.3\n\nText.\n"}, "no text"),
])
def test_changelog_fails_closed(tmp_path, monkeypatch, files, message):
    tool = generator(tmp_path, monkeypatch, files)
    with pytest.raises(ValueError, match=message):
        tool.load()


def test_shipped_changelog_is_current_and_covers_its_versions(monkeypatch):
    tool = load_tool("generate_changelog")
    notes = tool.load()
    assert (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") == tool.render(notes)
    assert "2026.10.3" in notes
    for language in ("en", "de"):
        assert "—" not in notes["2026.10.3"][language]                   # humanized: no em dashes


def test_release_data_accepts_valid_and_rejects_empty_or_short_lived(tmp_path):
    tool = load_tool("release_data")
    build = load_tool("build_data")
    dataset = load_tool("blizzard_dataset")
    now = int(time.time())
    source = observations(**{str(s): 30 for s in (62, 63, 64)})
    for entry in source["specs"].values():
        for row in entry["observations"]:
            row["observedAt"] = now - 600
    manifest, _ = dataset.manifest(source, interface=120100, client_build=69933, level=90, now=now)
    data = build.checked(manifest, json.dumps(source).encode(), now=now)
    good = tmp_path / "Data.lua"
    good.write_text("StatCompass.releaseData = " + build.lua_value(data) + "\n", encoding="utf-8")
    info = tool.check(good, now=now, min_days=7, min_cohorts=3)
    assert info["cohorts"] == 3 and info["clientBuild"] == 69933 and info["daysLeft"] > 29
    with pytest.raises(ValueError, match="expires"):
        tool.check(good, now=now, min_days=31, min_cohorts=3)
    with pytest.raises(ValueError, match="cohorts"):
        tool.check(good, now=now, min_days=7, min_cohorts=35)
    with pytest.raises(ValueError, match="empty"):
        tool.check(ROOT / "StatCompass/Data.lua", now=now, min_days=7, min_cohorts=1)
    tampered = tmp_path / "Tampered.lua"
    tampered.write_text(good.read_text(encoding="utf-8").replace('["schema"]=3', '["schema"]=2'), encoding="utf-8")
    with pytest.raises(ValueError, match="rejected"):
        tool.check(tampered, now=now, min_days=7, min_cohorts=3)


@pytest.mark.parametrize("icon_path", ["StatCompass/icon.tga", None, "StatCompass/assets/icon.tga"])
def test_release_archive_gate_requires_icon_at_runtime_path(tmp_path, monkeypatch, icon_path):
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    step = workflow.split("      - name: Verify package\n", 1)[1]
    script = textwrap.dedent(step.split("python - <<'EOF'\n", 1)[1].split("          EOF", 1)[0])
    release = tmp_path / ".release"
    release.mkdir()
    with ZipFile(release / "synthetic-test-only.zip", "w") as archive:
        for name in ("StatCompass.toc", "Core.lua", "Data.lua", "UI.lua", "Locales.lua", "Controls.lua"):
            # Synthetic gate fixture only, never release data or a publishable artifact.
            archive.writestr(f"StatCompass/{name}", b"synthetic-test-only\n" * 6000 if name == "Data.lua" else b"test")
        if icon_path:
            archive.writestr(icon_path, (ROOT / "StatCompass/icon.tga").read_bytes())
    monkeypatch.chdir(tmp_path)
    if icon_path == "StatCompass/icon.tga":
        exec(compile(script, "release.yml:Verify package", "exec"), {})
    else:
        with pytest.raises(SystemExit, match=r"missing=.*StatCompass/icon\.tga"):
            exec(compile(script, "release.yml:Verify package", "exec"), {})


def test_packaging_configuration():
    toc = (ROOT / "StatCompass/StatCompass.toc").read_text(encoding="utf-8")
    assert "## Version: @project-version@" in toc                           # the tag sets the version
    assert "## X-Wago-ID: YK9xO36L" in toc                                   # Wago project
    assert "## X-Curse-Project-ID: 1724016" in toc                          # CurseForge project
    pkgmeta = (ROOT / ".pkgmeta").read_text(encoding="utf-8")
    assert "package-as: StatCompass" in pkgmeta and "StatCompass/StatCompass: StatCompass" in pkgmeta
    for path in ("tools", "tests", "docs", "changelog", "assets", "AGENTS.md"):
        assert f"  - {path}" in pkgmeta
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "tags:\n      - 'v*'" in workflow and "BigWigsMods/packager@v2" in workflow
    assert "release_data.py" in workflow and "--require" in workflow
    assert "CF_API_KEY" not in workflow and "WAGO_API_TOKEN" not in workflow  # hosts import via webhook
    assert "workflow_call:" in workflow and "inputs.tag || github.ref" in workflow
    refresh = (ROOT / ".github/workflows/refresh-mplus-data.yml").read_text(encoding="utf-8")
    assert "vars.AUTO_DATA_RELEASE == 'true'" in refresh                     # off unless the owner enables it
    assert "uses: ./.github/workflows/release.yml" in refresh and "tools/data_release.py prepare" in refresh
