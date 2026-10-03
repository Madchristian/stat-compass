"""Check a built addon ZIP before (and after) it is published.

    python tools/verify_package.py            # the single package in .release/
    python tools/verify_package.py path.zip

The package must hold exactly the StatCompass/ folder with every addon file, a filled Data.lua and
nothing from tools/, tests/, docs/ or .github/.
"""
import glob
import sys
import zipfile
from pathlib import Path

REQUIRED = ("StatCompass.toc", "Core.lua", "Data.lua", "UI.lua", "Locales.lua", "Controls.lua", "icon.tga")
FORBIDDEN = ("tools", "tests", "docs", ".github", "changelog", "assets")
MIN_DATA_BYTES = 100_000


def verify(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
    names = [info.filename for info in infos]
    tops = {name.split("/", 1)[0] for name in names}
    missing = sorted(f"StatCompass/{f}" for f in REQUIRED if f"StatCompass/{f}" not in names)
    stray = [name for name in names if "/" in name and name.split("/")[1] in FORBIDDEN]
    sizes = {info.filename: info.file_size for info in infos}
    data = sizes.get("StatCompass/Data.lua", 0)
    problems = []
    if tops != {"StatCompass"}:
        problems.append(f"top-level entries {sorted(tops)}")
    if missing:
        problems.append(f"missing {missing}")
    if stray:
        problems.append(f"stray {stray[:5]}")
    if data < MIN_DATA_BYTES:
        problems.append(f"Data.lua has {data} bytes, expected the release data")
    if problems:
        raise ValueError("bad package: " + "; ".join(problems))
    return sizes


def main():
    paths = sys.argv[1:] or [z for z in glob.glob(".release/*.zip") if "-nolib" not in z]
    if len(paths) != 1:
        sys.exit(f"expected one package, found {paths}")
    try:
        sizes = verify(Path(paths[0]))
    except ValueError as exc:
        sys.exit(str(exc))
    print(f"{paths[0]}: {len(sizes)} files, Data.lua {sizes['StatCompass/Data.lua']} bytes")
    for name, size in sizes.items():
        print(f"{size:>9}  {name}")


if __name__ == "__main__":
    main()
