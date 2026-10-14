"""WS follower for P5's Thor-2 runs; it runs in WS tmux, so it survives the laptop's power cuts.

Every 5 minutes:
  1. if the WS can reach Thor-2 itself, copy the finished runs (env/p5_relay_thor2.sh with ON_WS=1); otherwise the
     laptop relays them (env/p5_relay_thor2.sh, also run by env/p5_status.sh);
  2. verify each new run's SHA256SUMS once (-> .p5_verified);
  3. analyse it once: TRF-3 runs with analysis.traffic_validate, cost curves with a per-width summary, and each CAND
     pair (S1 and F4 of one model) with analysis.candidates_traffic;
  4. write ~/work/runs/thor2/STATUS.txt.

    tmux new-session -d -s p5-follow "cd ~/jsw-dev && ~/work/venv-analysis/bin/python env/ws_follow.py"
"""
from __future__ import annotations

import glob
import json
import os
import statistics
import subprocess
import sys
import time

ROOT = os.path.expanduser("~/work/runs/thor2")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # ~/jsw-dev
PY = sys.executable
T = "mayankarya@10.24.24.80"


def sh(cmd, out=None, timeout=3600):
    with open(out, "w") if out else open(os.devnull, "w") as f:
        return subprocess.run(cmd, cwd=HERE, stdout=f, stderr=subprocess.STDOUT, timeout=timeout).returncode


def pull():
    if subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", T, "true"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        sh(["env", "ON_WS=1", "sh", "env/p5_relay_thor2.sh"], os.path.join(ROOT, ".relay.log"))
        return "direct"
    return "laptop relay only"


def verify(d):
    mark = os.path.join(d, ".p5_verified")
    if os.path.exists(mark):
        return open(mark).read().strip()
    if not os.path.exists(os.path.join(d, "SHA256SUMS")):
        res = "no SHA256SUMS (cost curve)" if os.path.exists(os.path.join(d, "costcurve.jsonl")) else "incomplete"
    else:
        rc = subprocess.run(["sha256sum", "--quiet", "-c", "SHA256SUMS"], cwd=d, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
        res = "sha256 ok" if rc == 0 else "SHA256 MISMATCH"
    if res != "incomplete":
        open(mark, "w").write(res + "\n")
    return res


def costcurve_summary(d):
    rows = [json.loads(l) for l in open(os.path.join(d, "costcurve.jsonl")) if l.strip()]
    out = []
    for ctx in sorted({r["ctx"] for r in rows}):
        base = statistics.mean(r["j_per_step"] for r in rows if r["ctx"] == ctx and r["k"] == 1 and r["j_per_step"])
        for k in sorted({r["k"] for r in rows if r["ctx"] == ctx}):
            v = [r["j_per_step"] for r in rows if r["ctx"] == ctx and r["k"] == k and r["j_per_step"]]
            s = [r["s_per_step"] for r in rows if r["ctx"] == ctx and r["k"] == k and r["s_per_step"]]
            if v:
                out.append(f"ctx {ctx:6d}  k {k:2d}  J/step {statistics.mean(v):6.2f}  x{statistics.mean(v) / base:5.2f} "
                           f"of k=1  s/step {statistics.mean(s):.3f}")
    open(os.path.join(d, "p5_costcurve.txt"), "w").write("\n".join(out) + "\n")


def analyse(d, name):
    if os.path.exists(os.path.join(d, ".p5_analysed")):
        return "analysed"
    if name.startswith("trf3-"):
        rc = sh([PY, "-m", "analysis.traffic_validate", "compare", d], os.path.join(d, "p5_validate.txt"))
    elif name.startswith("costcurve-"):
        costcurve_summary(d)
        rc = 0
    else:
        return "-"
    open(os.path.join(d, ".p5_analysed"), "w").write(f"rc={rc} {time.strftime('%F %T')}\n")
    return f"analysed rc={rc}"


def cand_pairs(names):
    lines = []
    for model in ("granite", "gemma"):
        s1 = sorted(n for n in names if n.startswith(f"cand-{model}-s1-"))
        f4 = sorted(n for n in names if n.startswith(f"cand-{model}-f4-"))
        if not (s1 and f4):
            lines.append(f"CAND {model}: waiting (S1 {'done' if s1 else 'not yet'}, F4 {'done' if f4 else 'not yet'})")
            continue
        out = os.path.join(ROOT, f"cand_{model}.txt")
        if not os.path.exists(out):
            sh([PY, "-m", "analysis.candidates_traffic", model, os.path.join(ROOT, s1[-1]), os.path.join(ROOT, f4[-1])], out)
        verdict = [l for l in open(out) if "->" in l or "undecided" in l]
        lines.append(f"CAND {model}: {verdict[-1].strip() if verdict else 'see ' + out}")
    return lines


def main():
    os.makedirs(ROOT, exist_ok=True)
    while True:
        try:
            mode = pull()
            names = sorted(n for n in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, n)) and not n.startswith("."))
            lines = [f"updated {time.strftime('%F %T %Z')}  (copy mode: {mode})", ""]
            done = []
            for n in names:
                d = os.path.join(ROOT, n)
                v = verify(d)
                a = analyse(d, n) if v.startswith(("sha256 ok", "no SHA256SUMS")) else "-"
                if v != "incomplete":
                    done.append(n)
                lines.append(f"{n:45s} {v:28s} {a}")
            lines += [""] + cand_pairs(done)
            logs = os.path.expanduser("~/work/runs/thor2_logs/logs")
            for lg in ("trf3_chain.log", "cand_chain.log"):
                p = os.path.join(logs, lg)
                if os.path.exists(p):
                    lines += ["", f"tail {lg} (as last copied):"] + ["  " + l.rstrip() for l in open(p).readlines()[-3:]]
            open(os.path.join(ROOT, "STATUS.txt"), "w").write("\n".join(lines) + "\n")
        except Exception as e:                       # keep following; the error shows in STATUS.txt
            open(os.path.join(ROOT, "STATUS.txt"), "a").write(f"\nfollower error {time.strftime('%T')}: {e!r}\n")
        time.sleep(300)


if __name__ == "__main__":
    main()
