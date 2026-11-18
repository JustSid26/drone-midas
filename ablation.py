"""The ablation the project exists to produce.

Identical courses, identical policy, different sources of depth:

    perfect      the simulator's own depth, the ceiling
    frozen       the network's estimate, scale and offset fitted once on separate
                 frames and never touched again. What fly.py --midas does by default
    + ToF        the same estimate, refitted every frame against a simulated 8x8
                 zone time-of-flight sensor (VL53L5CX class, 4 m range, 3% noise)
    raw          metric networks only: their own metres, no alignment
    none         no depth at all, the floor

    .venv/bin/python ablation.py --seeds 100-129 --obstacles 6
    .venv/bin/python ablation.py --model da2_small --style procedural

Results are also written to data/results/ablation_<style>_<model>.json.
"""
import argparse, json, os
import numpy as np
from run_route import run, CAM_H
from midas_depth import fit_scale_shift, TofAligner
from bench_midas import sample_frames
import estimators as E
import room as R

FOVY = 100


def summarise(rows):
    n = len(rows)
    full = sum(r["reached"] == r["total"] for r in rows)
    clean = sum(r["reached"] == r["total"] and r["collisions"] == 0 for r in rows)
    p = clean / n
    z = 1.96
    lo = (p + z*z/(2*n) - z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n)
    hi = (p + z*z/(2*n) + z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n)
    return dict(n=n, complete=full, clean=clean, lo=lo, hi=hi,
                contacts=float(np.mean([r["collisions"] for r in rows])),
                time=float(np.mean([r["time"] for r in rows])),
                timeouts=sum(r["timeout"] for r in rows))


def estimated(est, s0, t0, mode, fy):
    """A depth source for one flight. Made fresh per course, so the sensor state
    and its noise never carry from one course into the next."""
    tof = TofAligner(s0, t0, fy)

    def fn(rgb, true_depth):
        inv = est.inverse_depth(rgb)
        if mode == "tof":
            s, t, _ = tof(inv, true_depth)
        elif mode == "raw":
            s, t = 1.0, 0.0
        else:
            s, t = s0, t0
        a = s * inv + t
        return np.where(a > 1e-3, 1.0 / np.maximum(a, 1e-3), 1000.0).astype(np.float32)
    return fn


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="100-129")
    ap.add_argument("--stations", type=int, default=4)
    ap.add_argument("--obstacles", type=int, default=6)
    ap.add_argument("--style", choices=R.STYLES, default="photo")
    ap.add_argument("--model", default="midas_small",
                    choices=["midas_small", "midas_hybrid", "da2_small", "da2_metric"])
    ap.add_argument("--arms", default="perfect,frozen,tof,none",
                    help="any of perfect, frozen, tof, raw, none")
    args = ap.parse_args()
    a, b = args.seeds.split("-")
    seeds = range(int(a), int(b) + 1)

    est = E.load(args.model)
    cal_rgb, cal_d = sample_frames(range(200, 206), per_seed=5, rng_seed=1, style=args.style)
    P, Q = [], []
    for rgb, d in zip(cal_rgb, cal_d):
        inv = est.inverse_depth(rgb)
        m = np.isfinite(d) & (d > 0.2) & (d < 10.0)
        P.append(inv[m]); Q.append(1.0 / d[m])
    s0, t0 = fit_scale_shift(np.concatenate(P), np.concatenate(Q))
    fy = CAM_H / 2 / np.tan(np.radians(FOVY) / 2)
    print(f"{est.name}, {args.style} rooms, frozen calibration scale {s0:.6f} shift {t0:.6f}\n")

    arms = {"perfect": ("perfect depth (ceiling)", None),
            "frozen": (f"{est.name}, frozen", lambda: estimated(est, s0, t0, "frozen", fy)),
            "tof": (f"{est.name} + 8x8 ToF", lambda: estimated(est, s0, t0, "tof", fy)),
            "raw": (f"{est.name}, raw metres", lambda: estimated(est, s0, t0, "raw", fy)),
            "none": ("no depth (floor)",
                     lambda: (lambda rgb, true_depth: np.full_like(true_depth, 8.0)))}

    print(f"{'arm':<44}{'complete':>10}{'collision free':>16}{'95% CI':>12}"
          f"{'contacts':>10}{'timeouts':>10}")
    out = dict(model=est.name, style=args.style, seeds=args.seeds, obstacles=args.obstacles,
               stations=args.stations, arms={})
    for key in args.arms.split(","):
        label, make = arms[key]
        rows = [run(sd, args.stations, args.obstacles, 10.0, fovy=FOVY, fallback="both",
                    depth_fn=make() if make else None, style=args.style) for sd in seeds]
        r = summarise(rows)
        out["arms"][key] = dict(label=label, **r, runs=rows)
        print(f"{label:<44}{r['complete']:>7}/{r['n']}{r['clean']:>13}/{r['n']}"
              f"{100*r['lo']:>7.0f}-{100*r['hi']:<4.0f}"
              f"{r['contacts']:>10.2f}{r['timeouts']:>10}", flush=True)
    # Merge with earlier runs of other arms on the same settings.
    path = os.path.join("data", "results", f"ablation_{args.style}_{args.model}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        old = json.load(open(path))
        if all(old.get(k) == out[k] for k in ("seeds", "obstacles", "stations")):
            out["arms"] = {**old["arms"], **out["arms"]}
    json.dump(out, open(path, "w"), indent=1, default=float)
