"""Synthetic local release prerequisites; no publication API calls."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("release_gate", Path(__file__).resolve().parents[1] / "tools/release_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
SHA = "a" * 40
BASE = 1800000000


def state(**changes):
    value = dict(now=BASE+120*3600, last_release=dict(id="synthetic-release", published_at=BASE, channel="data", verified=True),
                 approved_code_sha=SHA, running_code_sha=SHA, season="synthetic-season",
                 pending_unverified_publication=False,
                 quality=dict(coverage=True, identities=True, blizzard_stats=True, rights=True,
                              retention=True, readback=True))
    value.update(changes)
    return value


def test_synthetic_120_hour_clock_boundary_and_idempotency():
    assert gate.evaluate(state(now=BASE+120*3600-1))["due"] is False
    ready = gate.evaluate(state())
    assert ready["due"] is True
    assert ready["idempotencyKey"] == gate.evaluate(state())["idempotencyKey"]
    assert gate.evaluate(state(last_release=dict(id="synthetic-next", published_at=BASE, channel="data", verified=True)))["idempotencyKey"] != ready["idempotencyKey"]


@pytest.mark.parametrize("change", [
    dict(now="bad"), dict(now=BASE-1),
    dict(last_release=dict(published_at=BASE, channel="data", verified=True)),
    dict(last_release=dict(id=None, published_at=BASE, channel="data", verified=True)),
    dict(last_release=dict(id="synthetic-release", published_at="bad", channel="data", verified=True)),
    dict(last_release=dict(id="synthetic-release", published_at=BASE+120*3600+1, channel="data", verified=True)),
    dict(last_release=dict(id="synthetic-release", published_at=BASE, channel="code", verified=True)),
    dict(last_release=dict(id="synthetic-release", published_at=BASE, channel="data", verified=False)),
    dict(running_code_sha="b"*40), dict(approved_code_sha="short"),
    dict(pending_unverified_publication=True),
    dict(quality=dict(coverage=False, identities=True, blizzard_stats=True, rights=True, retention=True, readback=True)),
])
def test_synthetic_fail_closed_prerequisites(change):
    with pytest.raises(gate.GateBlocked):
        gate.evaluate(state(**change))
