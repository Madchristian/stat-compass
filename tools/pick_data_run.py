"""Pick the newest successful refresh run on main that still has a data artifact (issue #42).

The daily scheduler also succeeds when it only plans and skips the refresh, so "the latest successful
run" may have no data. This walks the successful runs newest first and returns the first one with a
non-expired `mplus-data-*` artifact.

    python tools/pick_data_run.py --repo owner/name     # prints "<run id> <artifact name>"
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone


def pick(runs, artifacts_of):
    """runs: newest first, dicts with id/conclusion/head_branch; artifacts_of(run_id) -> artifact dicts."""
    skipped = []
    for run in runs:
        if run.get("conclusion") != "success" or run.get("head_branch") != "main":
            continue
        usable = [a for a in artifacts_of(run["id"])
                  if a.get("name", "").startswith("mplus-data-") and not a.get("expired")]
        if usable:
            return run["id"], usable[0]["name"], skipped
        skipped.append(run["id"])
    raise LookupError(f"no successful refresh run on main with a data artifact (checked {len(runs)} runs)")


def _gh(path):
    return json.loads(subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--workflow", default="refresh-mplus-data.yml")
    parser.add_argument("--timestamp", action="store_true",
                        help="print the successful refresh job's start epoch, or 0 when no data run exists")
    args = parser.parse_args()
    runs = _gh(f"repos/{args.repo}/actions/workflows/{args.workflow}/runs?branch=main&status=success&per_page=30")
    try:
        run_id, name, skipped = pick(runs.get("workflow_runs", []),
                                     lambda rid: _gh(f"repos/{args.repo}/actions/runs/{rid}/artifacts").get("artifacts", []))
    except LookupError as exc:
        if args.timestamp:
            print(0)
            return
        sys.exit(f"release data blocked: {exc}")
    if skipped:
        print(f"skipped runs without data: {skipped}", file=sys.stderr)
    if args.timestamp:
        jobs = _gh(f"repos/{args.repo}/actions/runs/{run_id}/jobs?filter=all&per_page=100")["jobs"]
        refresh = max((j for j in jobs if j["name"] == "refresh" and j["conclusion"] == "success"),
                      key=lambda job: job["started_at"])
        # Creation can precede the actual acquisition by hours (queueing or a rerun).
        print(int(datetime.strptime(refresh["started_at"], "%Y-%m-%dT%H:%M:%SZ")
                  .replace(tzinfo=timezone.utc).timestamp()))
    else:
        print(run_id, name)


if __name__ == "__main__":
    main()
