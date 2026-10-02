"""Render the identity-free cohort report as a Markdown job summary."""
import json
import sys
from pathlib import Path


def popularity(info):
    if not info or not info.get("sample"):
        return "–"
    shares = ", ".join(f"{name} {round(100 * n / info['sample'])} %" for name, n in info["trees"].items())
    return f"{shares} (top {info['sample']})"


def summary(report):
    lines = [f"## M+ cohorts, season {report['season']}",
             f"{report['specsEnough']}/{report['specsTotal']} specs have at least {report['minimum']} valid players; "
             f"{report['requests']} API requests, {report.get('weeksFromState', 0)} weeks from cached state.", "",
             "| Class | Spec | Valid | Certified | Score #30 | Crit % | Haste % | Mastery % | Vers % | Hero trees (top N) |",
             "| --- | --- | ---: | :---: | ---: | --- | --- | --- | --- | --- |"]
    for spec in report["specs"]:
        cert = spec.get("certification") or {}
        ranges = spec["statRanges"]
        cells = [f"{r[0]}–{r[1]}" if r else "–" for r in (ranges[k] for k in ("crit", "haste", "mastery", "versatility"))]
        lines.append(f"| {spec['class']} | {spec['spec']} | {spec['valid']} | {'✅' if cert.get('certified') else '⚠️'} | "
                     f"{cert.get('threshold', '–')} | " + " | ".join(cells) + f" | {popularity(spec.get('heroPopularity'))} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = Path(sys.argv[1])
    print(summary(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else "No report was produced.\n")
