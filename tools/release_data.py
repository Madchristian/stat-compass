"""Check a generated Data.lua with the addon's own runtime and place it into StatCompass/ for a release.

The repository keeps StatCompass/Data.lua empty; a release ships the Data.lua of the latest
successful weekly refresh. Fail-closed: the dataset must pass Core.lua's ValidateDataset for the
TOC interface, the live client build recorded in the dataset, level 90 and the current time, cover
at least --min-cohorts specs, and stay valid for at least --min-days.

    python tools/release_data.py path/to/Data.lua --min-days 7
"""
import argparse
import re
import shutil
import sys
import time
from pathlib import Path

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "StatCompass"


def check(data_path, *, now, min_days, min_cohorts, level=90):
    toc = (ADDON / "StatCompass.toc").read_text(encoding="utf-8")
    interface = int(re.search(r"(?m)^## Interface:\s*(\d+)", toc).group(1))
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("StatCompass = {}")
    lua.execute(Path(data_path).read_text(encoding="utf-8"))
    lua.execute((ADDON / "Core.lua").read_text(encoding="utf-8"))
    data = lua.eval("StatCompass.releaseData")
    if data is None or data.clientBuild is None:
        raise ValueError("dataset is empty")
    if not lua.eval("StatCompass.ValidateDataset")(data, interface, data.clientBuild, level, now):
        raise ValueError("dataset rejected by Core.ValidateDataset (interface, build, level, time or shape)")
    days_left = (data.expiresAt - now) / 86400
    if days_left < min_days:
        raise ValueError(f"dataset expires in {days_left:.1f} days, need at least {min_days}")
    cohorts = sum(1 for _ in data.cohorts.keys())
    if cohorts < min_cohorts:
        raise ValueError(f"only {cohorts} spec cohorts, need at least {min_cohorts}")
    return {"clientBuild": data.clientBuild, "cohorts": cohorts, "daysLeft": round(days_left, 1),
            "expiresAt": time.strftime("%Y-%m-%d", time.gmtime(data.expiresAt))}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data", type=Path)
    parser.add_argument("--min-days", type=float, default=7)
    parser.add_argument("--min-cohorts", type=int, default=35)
    parser.add_argument("--install", action="store_true", help="copy it to StatCompass/Data.lua after the check")
    args = parser.parse_args()
    info = check(args.data, now=int(time.time()), min_days=args.min_days, min_cohorts=args.min_cohorts)
    if args.install:
        shutil.copyfile(args.data, ADDON / "Data.lua")
    print(info)


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.exit(f"release data blocked: {exc}")
