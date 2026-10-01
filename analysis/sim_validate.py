"""Check the headroom simulator against the live concurrency runs, then estimate headroom.

For each live run (N session slots, KV pool size), simulate the same configuration from
the single-session traces (e1_low_n1) under SGLang-like LRU and compare:
  - excess re-prefilled tokens per mission (live minus the single-session baseline, which
    is nonzero because K2's re-rendered history differs at each turn's think tag);
  - GPU energy per mission; missions per hour.
Then run every policy at those configurations and at larger N.

Usage: python3 -m analysis.sim_validate
"""
from __future__ import annotations

import json
import statistics as st

from analysis.headroom_sim import POLICIES, shared_prefix_estimate, simulate, to_steps
from analysis.report_figures import OUT, WS, calibration, load_ws_run, run_summary
from analysis.sessions import load_aerogen

LIVE = ["e2_low_n2", "e2_low_n4", "e2_low_n8", "e2_low_n4_kv16k", "e2_low_n4_kv13k"]
HEADROOM_IDLE_W = 20.0           # between-call power used for the policy sweep
SENSITIVITY_IDLE_W = (10.0, 30.0)  # measured range: 10 W (N=1) to 20-32 W (concurrent runs)


def excess_reprefill(sessions):
    """Tokens of the previous call's *prompt* that the next call had to prefill again, per
    completed mission. The previous output is left out: K2's re-rendered history differs
    at the think tag (low effort), so it is re-prefilled even with no memory pressure."""
    tot, done = 0, [s for s in sessions if s.status == "done"]
    for s in sessions:
        for a, b in zip(s.calls, s.calls[1:]):
            tot += max(0, min(b["prompt"], a["prompt"]) - b["cached"])
    return tot / max(1, len(done))


def traces_from(sessions, rate):
    """Pressure-free traces from a live run's own missions: same calls and waits, with the
    measured re-prefill time taken out of each call."""
    from analysis.headroom_sim import Step
    out = []
    for s in sessions:
        steps = []
        for i, c in enumerate(s.calls):
            reusable = min(c["prompt"], s.calls[i - 1]["prompt"]) if i else 0
            extra = max(0, reusable - c["cached"]) / rate
            steps.append(Step("call", max(0.05, c["t1"] - c["t0"] - extra), c["prompt"] + c["completion"], reusable))
            if i + 1 < len(s.calls):
                steps.append(Step("wait", max(0.0, s.calls[i + 1]["t0"] - c["t1"])))
        out.append(steps)
    return out


def main():
    cal = calibration(WS / "calib_k2_tp1_gpu0.json")
    rate = cal["prefill_tok_s"]
    base = load_ws_run("e1_low_n1", cal)
    base_sum = run_summary(base, cal)
    # Power while a call runs / while all sessions wait, measured on the single-session run
    # (short tool-call turns do not keep the GPU at full decode power).
    active_w, idle_w = base_sum["call_power_w"], base_sum["idle_power_w"]
    print(f"measured call power {active_w:.0f} W, idle power {idle_w:.0f} W")
    sessions = [s for s in load_aerogen(WS / "e1_low_n1", "e1", rate) if s.success is not None]
    traces = [to_steps(s) for s in sessions]
    shared = shared_prefix_estimate(sessions)
    out = {"shared_prefix": shared, "call_power_w": active_w, "idle_power_w": idle_w, "baseline_reprefill": base_sum["reprefill_tokens_per_mission"],
           "baseline_energy": base_sum["energy_per_mission_j"], "validation": [], "headroom": []}
    print(f"{len(traces)} traces, shared prefix {shared}, single-session excess re-prefill/mission "
          f"{excess_reprefill(base['sessions']):.0f}, energy/mission {base_sum['energy_per_mission_j']:.0f} J")
    for name in LIVE:
        run = load_ws_run(name, cal)
        if not run or "t_end_wall" not in run["manifest"]:
            continue   # only finished runs
        live = run_summary(run, cal)
        if not live:
            continue
        n = run["manifest"]["args"]["concurrency"]
        pool = int(run["manifest"]["server_info"]["max_total_num_tokens"])   # the run's actual pool
        stagger = run["manifest"]["args"]["stagger_s"]
        own = traces_from(run["sessions"], rate)
        # Same-trajectory replay with this run's own measured powers: tests the memory model.
        aw, iw = live["call_power_w"], live["idle_power_w"]
        sims = {p: simulate(own, n, pool, p, rate, aw, iw, len(own),
                            shared=shared, stagger_s=stagger, shuffle=False) for p in POLICIES}
        # Cross-sample prediction from the single-session missions (not the same trajectories).
        pred = simulate(traces, n, pool, "lru", rate, aw, iw, live["missions"],
                        shared=shared, stagger_s=stagger)
        row = {"run": name, "n": n, "pool": pool, "missions": live["missions"],
               "live_excess_reprefill": excess_reprefill(run["sessions"]),
               "pred_from_e1_lru_reprefill": pred["reprefill_tok_per_mission"],
               "pred_from_e1_lru_energy": pred["energy_per_mission_j"],
               "live_errored": live["errored"], "live_energy_per_success": live["energy_per_success_j"],
               "gpu": run["manifest"]["args"]["gpu"], "live_call_w": aw, "live_between_call_w": iw,
               "live_energy": live["energy_per_mission_j"], "live_mph": live["missions_per_hour"],
               "live_reuse": live["reuse"], "live_success": live["success_rate"],
               **{f"sim_{p}_reprefill": sims[p]["reprefill_tok_per_mission"] for p in POLICIES},
               **{f"sim_{p}_energy": sims[p]["energy_per_mission_j"] for p in POLICIES},
               **{f"sim_{p}_mph": sims[p]["missions_per_hour"] for p in POLICIES},
               **{f"sim_{p}_queued": sims[p]["queued_s_per_mission"] for p in POLICIES}}
        out["validation"].append(row)
        print(f"{name}: re-prefill/mission live {row['live_excess_reprefill']:.0f} | same-trajectory sim "
              f"{row['sim_lru_reprefill']:.0f} | predicted from E1 {row['pred_from_e1_lru_reprefill']:.0f} || "
              f"energy/mission live {row['live_energy']:.0f} | sim {row['sim_lru_energy']:.0f} | pred "
              f"{row['pred_from_e1_lru_energy']:.0f} J || missions/h live {row['live_mph']:.1f} sim {row['sim_lru_mph']:.1f}")
    out["headroom_idle_w"] = HEADROOM_IDLE_W
    for pool in (25427, 16384, 13312):
        for n in (1, 2, 4, 8, 16):
            for p in POLICIES:
                r = simulate(traces, n, pool, p, rate, active_w, HEADROOM_IDLE_W, 4 * len(traces),
                             shared=shared, stagger_s=20)
                out["headroom"].append(r)
                for w in SENSITIVITY_IDLE_W:
                    rs = simulate(traces, n, pool, p, rate, active_w, w, 4 * len(traces),
                                  shared=shared, stagger_s=20)
                    rs["idle_w"] = w
                    out.setdefault("sensitivity", []).append(rs)
    (OUT / "sim_validation.json").write_text(json.dumps(out, indent=1))
    for pool in (25427, 16384, 13312):
        print(f"-- pool {pool}")
        for n in (1, 2, 4, 8, 16):
            rs = {r["policy"]: r for r in out["headroom"] if r["pool"] == pool and r["n"] == n}
            print(f"N={n:2d} " + " | ".join(
                f"{p}: {rs[p]['energy_per_mission_j']:6.0f} J {rs[p]['reprefill_tok_per_mission']:6.0f} tok "
                f"{rs[p]['queued_s_per_mission']:5.1f}s q f{rs[p]['failed']}" for p in POLICIES))


def fig_headroom(out, path, pools=(25427, 16384)):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from analysis.report_figures import C1, C2, C3, C4, INK, INK2, SURF, _style
    cols = {"lru": C1, "drop": C2, "keep": C3, "eta": C4}
    names = {"lru": "LRU (SGLang default)", "drop": "drop at every wait",
             "keep": "keep all (pin until resume)", "eta": "drop latest-resuming first (exact flight ETA)"}
    fig, axes = plt.subplots(2, len(pools), figsize=(11.5, 6.6), sharex=True)
    for j, pool in enumerate(pools):
        for i, (key, lab, scale) in enumerate([("energy_per_mission_j", "GPU energy per completed mission (kJ)", 1e-3),
                                                ("mission_s_p50", "median mission time (min)", 1 / 60)]):
            ax = axes[i][j]
            for p in POLICIES:
                rs = sorted((r for r in out["headroom"] if r["pool"] == pool and r["policy"] == p), key=lambda r: r["n"])
                ax.plot([r["n"] for r in rs], [r[key] * scale for r in rs], color=cols[p], lw=2, marker="o",
                        ms=5, markeredgecolor=SURF, markeredgewidth=1.5, label=names[p])
            if i == 0:
                ax.set_title(f"KV pool {pool / 1000:.1f}K tokens", fontsize=10)
            ax.set_xscale("log", base=2)
            ax.set_xticks([1, 2, 4, 8, 16], ["1", "2", "4", "8", "16"])
            if j == 0:
                ax.set_ylabel(lab)
            if i == 1:
                ax.set_xlabel("concurrent drone sessions N")
            ax.set_ylim(bottom=0)
            _style(ax, "y")
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=9, bbox_to_anchor=(0.5, -0.06), frameon=False)
    fig.suptitle("Simulated retention policies: the same 15 single-session aerogen missions replayed as N sessions (LRU and exact-ETA overlap)",
                 x=0.01, ha="left", fontsize=10, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
    out = json.loads((OUT / "sim_validation.json").read_text())
    fig_headroom(out, OUT / "figures" / "headroom.png")
