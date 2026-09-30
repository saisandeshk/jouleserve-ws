"""Build the hand-drawn chart modules for the shareable Claude Doc from report_data.json.

Each function returns the widget `code` string (one line, single quotes inside), with the
numbers as inline rows so the doc chart redraws from its rows.

Usage: python3 -m analysis.doc_charts <chart> > code.txt   (chart: retention | time | concurrency)
"""
from __future__ import annotations

import json
import sys

from analysis.sessions import REPO

DATA = REPO / "reports/2026-10-01-workload-opportunity/report_data.json"

SHORT = {
    "P1 Reflexion · basic (B)": ("p1-refl-b", "P1 Reflexion · basic"),
    "P1 Reflexion · advanced (A)": ("p1-refl-a", "P1 Reflexion · advanced"),
    "P1 Reflexion · AeroEval (D/F)": ("p1-refl-df", "P1 Reflexion · AeroEval"),
    "P1 tool-calling · basic (B)": ("p1-tc-b", "P1 tool-calling · basic"),
    "P1 tool-calling · advanced (A)": ("p1-tc-a", "P1 tool-calling · advanced"),
    "aerogen · low effort (WS)": ("ag-low", "aerogen · low effort"),
    "aerogen · high effort (WS)": ("ag-high", "aerogen · high effort"),
}


def js(v):
    """Python value -> JS literal with single-quoted strings."""
    if isinstance(v, str):
        return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(round(v, 2)) if isinstance(v, float) else str(v)
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}:{js(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ",".join(js(x) for x in v) + "]"
    raise TypeError(v)


def retention():
    d = json.loads(DATA.read_text())
    rows = []
    for r in d["rows"]:
        slug, name = SHORT[r["label"]]
        rows.append({"slug": slug, "workload": name, "family": "aerogen" if slug.startswith("ag") else "P1",
                     "reuse": 100 * r["reuse"], "saving": 100 * r["retention_saving"], "n": r["n"]})
    H = 96 + len(rows) * 34 + 30
    return (
        "export default () => <claude.Visualize data-claude-component='retention-value' "
        f"sources={{{{rows:{{kind:'data', data:{js(rows)}}}}}}}>"
        "{({rows, datum}) => { const left = 196, colw = 240, gap = 44, y0 = 104, rowh = 34; "
        "const xa = v => left + v / 100 * colw, xb = v => left + colw + gap + v / 100 * colw; "
        "const fmt = v => v < 10 ? v.toFixed(1) : v.toFixed(0); "
        "const fill = r => r.family === 'aerogen' ? 'var(--cds-chart-categorical-1)' : 'var(--cds-chart-muted)'; "
        f"return <svg viewBox='0 0 760 {H}' role='img' aria-label='Keeping KV state saves under 1 percent of LLM time for the P1 agents' fontSize='12'>"
        "<text data-claude-text-id='title' x='0' y='22' fontSize='16' fontWeight='600' fill='var(--cds-text-primary)'>Keeping KV state saves under 1% of LLM time for P1's agents</text>"
        "<text data-claude-text-id='subtitle' x='0' y='44' fill='var(--cds-text-secondary)'>Grey: P1 drone agents (Thor traces). Blue: aerogen, an accumulating tool-calling drone agent (workstation).</text>"
        "<text data-claude-text-id='head-reuse' x={left} y='80' fontWeight='600' fill='var(--cds-text-primary)'>Prompt tokens served from cache</text>"
        "<text data-claude-text-id='head-saving' x={left + colw + gap} y='80' fontWeight='600' fill='var(--cds-text-primary)'>LLM time saved by keeping state</text>"
        "<g data-claude-anchor='axes'><line x1={left} x2={left} y1={y0 - 18} y2={y0 + rows.length * rowh - 12} stroke='var(--cds-chart-axis)'/>"
        "<line x1={left + colw + gap} x2={left + colw + gap} y1={y0 - 18} y2={y0 + rows.length * rowh - 12} stroke='var(--cds-chart-axis)'/></g>"
        "{rows.map((r, i) => <g key={r.slug} data-claude-anchor={`row-${r.slug}`}>"
        "<text x={left - 10} y={y0 + i * rowh} textAnchor='end' fill='var(--cds-text-primary)'>{r.workload}</text>"
        "<rect x={left} y={y0 + i * rowh - 13} width={Math.max(1.5, xa(r.reuse) - left)} height='18' rx='3' fill={fill(r)} {...datum(r, 'reuse')}><title>{`${r.workload}: ${fmt(r.reuse)}% of prompt tokens served from cache (${r.n} sessions)`}</title></rect>"
        "<text x={xa(r.reuse) + 6} y={y0 + i * rowh} fill='var(--cds-text-primary)' {...datum(r, 'reuse')}>{`${fmt(r.reuse)}%`}</text>"
        "<rect x={left + colw + gap} y={y0 + i * rowh - 13} width={Math.max(1.5, xb(r.saving) - left - colw - gap)} height='18' rx='3' fill={fill(r)} {...datum(r, 'saving')}><title>{`${r.workload}: keeping state saves ${fmt(r.saving)}% of LLM time (${r.n} sessions)`}</title></rect>"
        "<text x={xb(r.saving) + 6} y={y0 + i * rowh} fill='var(--cds-text-primary)' {...datum(r, 'saving')}>{`${fmt(r.saving)}%`}</text>"
        "</g>)}"
        f"<text data-claude-text-id='scale-note' x={{left}} y='{H - 8}' fill='var(--cds-text-secondary)'>Both panels on a 0 to 100% scale.</text>"
        "</svg>; }}</claude.Visualize>;"
    )


def time_split():
    d = json.loads(DATA.read_text())
    rows = []
    for r in d["rows"]:
        slug, name = SHORT[r["label"]]
        for part, key in [("decode", "share_decode"), ("tool wait", "share_tool"),
                          ("prefill", "share_prefill"), ("other", "share_other")]:
            rows.append({"slug": slug, "workload": name, "part": part, "share": 100 * r[key],
                         "session_min": r["session_s_p50"] / 60})
    n = len(d["rows"])
    H = 92 + n * 34 + 30
    return (
        "export default () => <claude.Visualize data-claude-component='time-split' "
        f"sources={{{{rows:{{kind:'data', data:{js(rows)}}}}}}}>"
        "{({rows, datum}) => { const left = 196, w = 470, y0 = 100, rowh = 34; "
        "const names = rows.filter(r => r.part === 'decode'); "
        "const color = p => p === 'decode' ? 'var(--cds-chart-categorical-1)' : p === 'tool wait' ? 'var(--cds-chart-categorical-2)' : 'var(--cds-chart-muted)'; "
        "const op = p => p === 'other' ? 0.45 : 1; "
        "const parts = rows.filter(r => r.slug === names.at(0).slug); "
        f"return <svg viewBox='0 0 760 {H}' role='img' aria-label='Decoding dominates every workload except low-effort aerogen, which mostly waits on flights' fontSize='12'>"
        "<text data-claude-text-id='title' x='0' y='22' fontSize='16' fontWeight='600' fill='var(--cds-text-primary)'>Decoding dominates every workload except low-effort aerogen, which waits on flights</text>"
        "<text data-claude-text-id='subtitle' x='0' y='44' fill='var(--cds-text-secondary)'>Share of session wall time, pooled over sessions. Right: median session length.</text>"
        "<g data-claude-anchor='legend'>{parts.map((p, k) => <g key={p.part}><rect x={left + k * 110} y='60' width='12' height='12' rx='2' fill={color(p.part)} fillOpacity={op(p.part)}/><text x={left + k * 110 + 18} y='70' fill='var(--cds-text-secondary)'>{p.part}</text></g>)}</g>"
        "<g data-claude-anchor='x-axis'>{[0, 25, 50, 75, 100].map(t => <g key={t}><line x1={left + t / 100 * w} x2={left + t / 100 * w} y1={y0 - 8} y2={y0 + names.length * rowh - 10} stroke='var(--cds-chart-grid)'/><text x={left + t / 100 * w} y={y0 + names.length * rowh + 6} textAnchor='middle' fill='var(--cds-text-secondary)'>{`${t}%`}</text></g>)}</g>"
        "{names.map((nm, i) => { let acc = 0; const segs = rows.filter(r => r.slug === nm.slug); return <g key={nm.slug} data-claude-anchor={`row-${nm.slug}`}>"
        "<text x={left - 10} y={y0 + i * rowh + 13} textAnchor='end' fill='var(--cds-text-primary)'>{nm.workload}</text>"
        "{segs.map(s => { const x = left + acc / 100 * w, wd = s.share / 100 * w; acc += s.share; return <g key={s.part}><rect x={x} y={y0 + i * rowh} width={Math.max(0, wd - 2)} height='18' fill={color(s.part)} fillOpacity={op(s.part)} {...datum(s, 'share')}><title>{`${s.workload}: ${s.part} ${s.share.toFixed(1)}% of session time`}</title></rect>"
        "</g>; })}"
        "<text x={left + w + 12} y={y0 + i * rowh + 13} fill='var(--cds-text-secondary)' {...datum(nm, 'session_min')}>{`${nm.session_min.toFixed(1)} min`}</text>"
        "</g>; })}"
        "</svg>; }}</claude.Visualize>;"
    )


if __name__ == "__main__":
    which = sys.argv[1]
    print({"retention": retention, "time": time_split}[which]())
