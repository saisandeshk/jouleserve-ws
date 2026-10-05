"""Streaming repetition-loop detector (OPTIONS_PLAN.md S4).

The same rule as the offline analysis (`analysis/p1_loops.detect`, reports/2026-10-04-drone-runaways):
every 1,000 characters, zlib-compress the last W characters for W = 4,000 and 16,000; a window is "low" when
the compressed size is below 10% of W; the detector fires at the first check where either window has been
low for 3 checks in a row. Ordinary reasoning and code compress to 25-35%, a loop to a few percent.

Feed it text as it streams (reasoning, then content, then tool-call arguments, as in the analysis). It
fires at exactly the character position where the offline rule would, whatever the chunking
(tests/test_loop_detector.py checks this on P1's recorded calls).
"""
from __future__ import annotations

import zlib

WINDOWS, THRESHOLD, PERSIST, STEP = (4000, 16000), 0.10, 3, 1000


def ratio(text: str) -> float:
    b = text.encode()
    return len(zlib.compress(b)) / max(1, len(b))


class LoopDetector:
    """Incremental detector for one LLM call. `feed()` returns the firing position in characters once."""

    def __init__(self, windows=WINDOWS, threshold=THRESHOLD, persist=PERSIST, step=STEP):
        self.windows, self.threshold, self.persist, self.step = tuple(windows), threshold, persist, step
        self.keep = max(self.windows)
        self.buf = ""            # the last `keep` characters seen (at least)
        self.n = 0               # characters seen so far
        self.next_check = self.step * -(-min(self.windows) // self.step)
        self.runs = {w: 0 for w in self.windows}
        self.fired_at: int | None = None
        self.checks = 0

    def feed(self, chunk: str) -> int | None:
        """Add streamed text; return the character position where the detector fires (only once)."""
        if self.fired_at is not None or not chunk:
            return None
        self.buf += chunk
        self.n += len(chunk)
        while self.next_check <= self.n:
            end = self.next_check
            off = len(self.buf) - (self.n - end)   # index of `end` inside buf
            for w in self.windows:
                if end < w:
                    continue
                self.runs[w] = self.runs[w] + 1 if ratio(self.buf[off - w:off]) < self.threshold else 0
            self.checks += 1
            self.next_check += self.step
            if any(r >= self.persist for r in self.runs.values()):
                self.fired_at = end
                return end
        # bound memory: every future check ends after n, so it needs at most the last `keep` characters
        if len(self.buf) > 2 * self.keep:
            self.buf = self.buf[-self.keep:]
        return None

    @property
    def fired(self) -> bool:
        return self.fired_at is not None


def detect_offline(text: str) -> int | None:
    """Firing position in characters for a complete text (same answer as feeding it in any chunks)."""
    d = LoopDetector()
    d.feed(text)
    return d.fired_at
