"""S4 parity: the streaming detector fires exactly where the offline analysis does, on P1's recorded calls.

Run: python3 -m pytest tests/test_loop_detector.py -q   (or python3 -m tests.test_loop_detector)
Needs P1's repository clone and our Thor tool-calling copy (data/, git-ignored); skips without them.
"""
import random

from jsw.policies.loop_detector import LoopDetector, detect_offline

SYNTHETIC_LOOP = "The drone moves forward 5 meters and then turns. " * 800
SYNTHETIC_PLAIN = "".join(f"step {i}: fly to waypoint {i * 7 % 101} at altitude {i % 13} m; " for i in range(4000))


def _stream(text, rng):
    d, i = LoopDetector(), 0
    while i < len(text):
        n = rng.choice((1, 3, 17, 250, 999, 1000, 1001, 4096))
        d.feed(text[i:i + n])
        i += n
    return d.fired_at


def test_synthetic():
    rng = random.Random(0)
    assert detect_offline(SYNTHETIC_LOOP) is not None
    assert _stream(SYNTHETIC_LOOP, rng) == detect_offline(SYNTHETIC_LOOP)
    assert detect_offline(SYNTHETIC_PLAIN) is None


def _p1_calls():
    try:
        from analysis import p1_repo
        runs = p1_repo.load("d_thor_gemma_rfx") + p1_repo.load("d_thor_gemma_tc")
    except Exception:  # data not present on this machine
        return []
    return [c for r in runs for c in r["calls"] if c.get("text")]


def test_parity_on_p1_calls():
    from analysis.p1_loops import detect as offline_fraction
    calls = _p1_calls()
    if not calls:
        import pytest
        pytest.skip("P1 data not available")
    rng = random.Random(1)
    flagged_capped = 0
    for c in calls:
        text = c["text"]
        frac = offline_fraction(text)
        got = _stream(text, rng)
        if frac is None:
            assert got is None
        else:
            assert got is not None and abs(got - frac * len(text)) < 1e-6
            flagged_capped += c["capped"]
    # the published counts (reports/2026-10-05-p1-repo §5): 121 of 122 Reflexion + 127 tool-calling capped calls
    assert flagged_capped == 121 + 127


if __name__ == "__main__":
    test_synthetic()
    test_parity_on_p1_calls()
    print("ok")
