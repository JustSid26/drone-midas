"""The ablation the project exists to produce.

Identical courses, identical policy, three sources of depth:
perfect from the simulator, estimated by MiDaS from one camera image, and none.
"""
import argparse, numpy as np
from run_route import run
from midas_depth import MidasDepth
from bench_midas import sample_frames


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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="100-129")
    ap.add_argument("--stations", type=int, default=4)
    ap.add_argument("--obstacles", type=int, default=6)
    args = ap.parse_args()
    a, b = args.seeds.split("-")
    seeds = range(int(a), int(b) + 1)

    md = MidasDepth()
    cal_rgb, cal_d = sample_frames(range(200, 206), per_seed=5, rng_seed=1)
    s, t = md.calibrate(cal_rgb, cal_d)
    print(f"frozen calibration  scale {s:.6f}  shift {t:.6f}\n")

    def estimated(rgb, true_depth):
        return md.metric_depth(rgb, true_depth, mode="frozen")

    def blind(rgb, true_depth):
        return np.full_like(true_depth, 8.0)      # no depth information at all

    arms = [("perfect depth (ceiling)", None),
            ("MiDaS estimated depth", estimated),
            ("no depth (floor)", blind)]

    print(f"{'arm':<26}{'complete':>10}{'collision free':>16}{'95% CI':>16}"
          f"{'contacts':>10}{'timeouts':>10}")
    for label, fn in arms:
        rows = [run(sd, args.stations, args.obstacles, 10.0, fovy=100,
                    fallback="both", depth_fn=fn) for sd in seeds]
        r = summarise(rows)
        print(f"{label:<26}{r['complete']:>7}/{r['n']}{r['clean']:>13}/{r['n']}"
              f"{100*r['lo']:>9.0f}-{100*r['hi']:<5.0f}"
              f"{r['contacts']:>10.2f}{r['timeouts']:>10}", flush=True)
