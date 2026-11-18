"""Can MiDaS steer the aircraft indoors? Tested on real rooms, not the simulator.

For every model and dataset, three ways of turning relative depth into metres:

    frozen   one scale and offset, fitted once on separate frames from the same
             place, then never touched. What fly.py --midas does today.
    tof      refit every frame against an 8x8 zone time-of-flight sensor
             (VL53L5CX class: 45 degree field, 4 m range, a few dollars).
             Simulated from the true depth with 3% noise. A realistic hardware fix.
             Still frames have no previous frame, so when the zones cannot fix
             both numbers the calibration's offset is kept; in flight
             (midas_depth.TofAligner) the last full fit is kept instead.
    oracle   refit every frame against the full true depth. An upper bound no
             aircraft can reach; it isolates the shape error from the scale error.
    raw      metric models only: the network's own metres, no alignment at all.

Two kinds of score. The standard ones (AbsRel, RMSE, delta < 1.25) so the numbers
compare with published results. And the ones the aircraft cares about, computed
by running the real policy's depth processing (policy.py) on both depth maps:

    missed stop   something really is within 1.2 m ahead at flight level, but the
                  estimate says the way is clear. This is a crash.
    false stop    the way is clear, but the estimate says to stop. Lost time.
    bad heading   the heading the policy would pick has an obstacle within 1.2 m.

    .venv/bin/python eval_real.py                 every model, every dataset
    .venv/bin/python eval_real.py --models midas_small --datasets nyu
    .venv/bin/python eval_real.py --speed         timing at the sim camera size
"""
import argparse, json, os
import numpy as np

import indoor_data as D
import estimators as E
from midas_depth import fit_scale_shift, tof_anchor
from policy import ReactivePolicy

OUT = os.path.join(D.DATA, "results")
LO, HI = 0.1, 10.0                    # metres scored, the NYU convention
STOP = 1.2                            # policy safety trip point
BINS = [(0.1, 1.5), (1.5, 3.0), (3.0, 6.0), (6.0, 10.0)]

MODELS = ["midas_small", "midas_hybrid", "da2_small", "da2_metric"]
DATASETS = ["nyu", "diode", "tum_room", "tum_pioneer"]


def valid(gt):
    return np.isfinite(gt) & (gt > LO) & (gt < HI)


def to_depth(inv, s, t):
    """Aligned inverse depth to metres. Anything at or beyond the far cap,
    including a non-positive inverse depth, reads as the cap."""
    a = s * inv + t
    return np.clip(1.0 / np.maximum(a, 1.0 / HI), LO, HI).astype(np.float32)


def standard(pred, gt, m):
    p, g = pred[m], gt[m]
    ratio = np.maximum(p / g, g / p)
    out = dict(absrel=float(np.mean(np.abs(p - g) / g)),
               rmse=float(np.sqrt(np.mean((p - g) ** 2))),
               d1=float(np.mean(ratio < 1.25)))
    for lo, hi in BINS:
        b = (g >= lo) & (g < hi)
        out[f"absrel_{lo:g}_{hi:g}"] = (float(np.mean(np.abs(p[b] - g[b]) / g[b]))
                                        if b.sum() > 200 else None)
    return out


def solid(gt, m):
    """Truth for the stop decision. Sensors leave clusters of stray returns on
    glass, blinds and edges; the policy takes a minimum, so a few stray pixels
    would read as an obstacle. Closing removes nearer patches smaller than 7x7
    pixels and keeps anything larger, such as a fan or a chair leg up close."""
    import cv2
    g = cv2.morphologyEx(np.where(m, gt, HI).astype(np.float32), cv2.MORPH_CLOSE,
                         np.ones((7, 7), np.uint8))
    return np.where(m, g, np.inf)


def flight(pred, gt, m, pol):
    """Run the policy's own depth processing on truth and estimate."""
    fg, rg = pol._free_per_column(solid(gt, m))
    fp, rp = pol._free_per_column(np.where(m, pred, np.inf))
    centre = np.abs(pol.yaw_offset) < np.radians(12.0)
    front_g, front_p = float(fg[centre].min()), float(fp[centre].min())
    # Station straight ahead: the policy's own score, without the commit term.
    pick = lambda f: int(np.argmax(f / pol.max_range + pol.goal_weight * np.cos(pol.yaw_offset)))
    jp, jg = pick(fp), pick(fg)
    # A heading is bad when it runs into something inside the trip point while
    # truth had a clearly open one, at least twice the trip point. The margin
    # keeps near-threshold coin flips from counting.
    return dict(front_g=front_g, front_p=front_p,
                stop_g=front_g < STOP, stop_p=front_p < STOP,
                head_bad=bool(fg[jp] < STOP), head_possible=bool(fg[jg] >= 2 * STOP))


def summarise(rows):
    out = {}
    for k in ["absrel", "rmse", "d1"] + [f"absrel_{lo:g}_{hi:g}" for lo, hi in BINS]:
        v = [r[k] for r in rows if r.get(k) is not None]
        out[k] = float(np.mean(v)) if v else None
    sg = np.array([r["stop_g"] for r in rows]); sp = np.array([r["stop_p"] for r in rows])
    out["frames"] = len(rows)
    out["frames_obstacle_close"] = int(sg.sum())
    out["missed_stop"] = float((sg & ~sp).sum() / max(sg.sum(), 1))
    fg = np.array([r["front_g"] for r in rows]); fp = np.array([r["front_p"] for r in rows])
    # Truth inside the trip point, estimate more than twice it: flies in at speed.
    out["gross_miss"] = float((sg & (fp > 2 * STOP)).sum() / max(sg.sum(), 1))
    out["false_stop"] = float((~sg & sp).sum() / max((~sg).sum(), 1))
    poss = np.array([r["head_possible"] for r in rows])
    bad = np.array([r["head_bad"] for r in rows])
    out["bad_heading"] = float((bad & poss).sum() / max(poss.sum(), 1))
    near = fg < 4.0
    out["front_err_m"] = float(np.median(np.abs(fp[near] - fg[near]))) if near.any() else None
    out["front_bias"] = float(np.median((fp[near] - fg[near]) / fg[near])) if near.any() else None
    return out


def evaluate(est, ds, keep_examples=4):
    cal, test, note = D.splits(ds)

    P, Q = [], []
    for fr in cal():
        inv = est.inverse_depth(fr["rgb"])
        m = valid(fr["depth"])
        P.append(inv[m][::7]); Q.append(1.0 / fr["depth"][m][::7])
    s0, t0 = fit_scale_shift(np.concatenate(P), np.concatenate(Q))

    arms = ["frozen", "tof", "oracle"] + (["raw"] if est.metric else [])
    rows = {a: [] for a in arms}
    tof_modes = {"full": 0, "scale": 0, "frozen": 0}
    examples, series = [], {a: [] for a in arms}
    rng = np.random.default_rng(0)
    pol = None
    for k, fr in enumerate(test()):
        rgb, gt, fy = fr["rgb"], fr["depth"], fr["fy"]
        if pol is None:
            h, w = gt.shape
            pol = ReactivePolicy(np.degrees(2 * np.arctan(h / 2 / fy)), w, h)
        m = valid(gt)
        if m.sum() < 1000:
            continue
        inv = est.inverse_depth(rgb)
        st, tt, mode = tof_anchor(inv, gt, fy, s0, t0, rng)
        tof_modes[mode] += 1
        so, to = fit_scale_shift(inv, 1.0 / np.where(m, gt, 1.0), m)
        params = dict(frozen=(s0, t0), tof=(st, tt), oracle=(so, to), raw=(1.0, 0.0))
        preds = {}
        for a in arms:
            pred = to_depth(inv, *params[a])
            preds[a] = pred
            r = standard(pred, gt, m)
            r.update(flight(pred, gt, m, pol))
            rows[a].append(r)
            series[a].append([r["absrel"], r["front_g"], r["front_p"]])
        if k % 97 == 13 and len(examples) < keep_examples:
            examples.append(dict(id=fr["id"], rgb=rgb[::2, ::2], gt=gt[::2, ::2],
                                 **{a: preds[a][::2, ::2] for a in arms}))
    res = dict(model=est.name, dataset=ds, note=note, frozen=dict(scale=s0, shift=t0),
               tof_modes=tof_modes, arms={a: summarise(rows[a]) for a in arms},
               series=series)
    return res, examples


def speed_table():
    import cv2, torch
    rgb = cv2.cvtColor(cv2.imread(os.path.join(D.HERE, "deck", "wireframe.png")), cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (320, 240))       # the simulator's camera size
    out = {}
    for key in MODELS:
        out[key] = {}
        for dev in ["mps", "cpu"]:
            if dev == "mps" and not torch.backends.mps.is_available():
                continue
            if dev == "cpu":
                torch.set_num_threads(4)    # roughly an embedded quad core
            est = E.load(key, dev)
            out[key][dev] = E.speed(est, rgb, n=30 if dev == "mps" else 8)
            print(f"{est.name:42s} {dev:4s} {out[key][dev]:7.1f} ms", flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, "speed.json"), "w"), indent=1)


REAL = ["nyu", "diode", "tum_room", "tum_pioneer"]


def decisions(series):
    """Stop decisions with margins, from per-frame (absrel, true front, estimated
    front). A miss only counts when the truth is clearly inside the trip point,
    so a 1.15 m against 1.25 m coin flip is not scored as a crash."""
    s = np.array(series)
    fg, fp = s[:, 1], s[:, 2]
    clear, close, near = fg >= STOP, fg < 1.0, fg < 2.0
    return dict(frames=len(s), n_clear=int(clear.sum()), n_close=int(close.sum()),
                false_stop=float((clear & (fp < STOP)).sum() / max(clear.sum(), 1)),
                missed=float((close & (fp >= STOP)).sum() / max(close.sum(), 1)),
                gross=float((close & (fp > 2 * STOP)).sum() / max(close.sum(), 1)),
                near_ratio=float(np.median(fp[near] / fg[near])) if near.any() else None)


def summary():
    """Pool every result file into one table, real data and simulator apart."""
    out = {}
    for key in MODELS:
        out[key] = {}
        for ds in REAL + ["sim_photo", "sim_procedural"]:
            path = os.path.join(OUT, f"{key}__{ds}.json")
            if os.path.exists(path):
                r = json.load(open(path))
                out[key][ds] = {a: dict(absrel=v["absrel"], d1=v["d1"], **decisions(r["series"][a]))
                                for a, v in r["arms"].items()}
                out[key]["name"] = r["model"]
        for group, names in [("real", REAL), ("sim_photo", ["sim_photo"]), ("sim_procedural", ["sim_procedural"])]:
            have = [d for d in names if d in out[key]]
            if not have:
                continue
            out[key][f"pooled_{group}"] = {}
            for a in out[key][have[0]]:
                rows = []
                for d in have:
                    rows += json.load(open(os.path.join(OUT, f"{key}__{d}.json")))["series"].get(a, [])
                if rows:
                    out[key][f"pooled_{group}"][a] = dict(
                        absrel_mean_of_datasets=float(np.mean([out[key][d][a]["absrel"] for d in have if a in out[key][d]])),
                        **decisions(rows))
    json.dump(out, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
    return out


def figures(datasets=("nyu", "diode", "tum_room", "sim_photo", "sim_procedural"), per=2):
    """One row per example frame: camera, truth, then estimates on one colour
    scale (0 to 6 m, black where truth is missing)."""
    import cv2
    def colour(d, invalid=None):
        v = cv2.applyColorMap((255 * np.clip(1 - d / 6.0, 0, 1)).astype(np.uint8), cv2.COLORMAP_INFERNO)
        if invalid is not None:
            v[invalid] = 0
        return v
    def label(img, text):
        img = img.copy()
        (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img, (0, 0), (w + 12, h + 12), (20, 20, 20), -1)
        cv2.putText(img, text, (6, h + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        return img
    rows = []
    for ds in datasets:
        a = os.path.join(OUT, f"midas_small__{ds}_examples.npz")
        b = os.path.join(OUT, f"da2_small__{ds}_examples.npz")
        if not (os.path.exists(a) and os.path.exists(b)):
            continue
        A, B = np.load(a), np.load(b)
        for i in range(per):
            if f"{i}_rgb" not in A:
                break
            gt = A[f"{i}_gt"]
            bad = ~valid(gt)
            tiles = [A[f"{i}_rgb"][..., ::-1], colour(gt, bad), colour(A[f"{i}_frozen"]),
                     colour(A[f"{i}_tof"]), colour(B[f"{i}_tof"])]
            h = 200
            tiles = [cv2.resize(t, (int(t.shape[1] * h / t.shape[0]), h)) for t in tiles]
            names = [ds.replace("_", " "), "true depth", "MiDaS small, frozen", "MiDaS small + ToF",
                     "Depth Anything V2 + ToF"]
            rows.append(np.hstack([label(t, n) for t, n in zip(tiles, names)]))
    w = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 4, 0, w - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]
    os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
    path = os.path.join(OUT, "figures", "examples.jpg")
    cv2.imwrite(path, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--datasets", default=",".join(DATASETS))
    ap.add_argument("--redo", action="store_true", help="ignore cached results")
    ap.add_argument("--speed", action="store_true")
    ap.add_argument("--figures", action="store_true")
    ap.add_argument("--summary", action="store_true", help="pool cached results into summary.json")
    args = ap.parse_args()
    if args.speed:
        speed_table()
        raise SystemExit
    if args.figures:
        print(figures())
        raise SystemExit
    if args.summary:
        print(json.dumps(summary(), indent=1))
        raise SystemExit
    os.makedirs(OUT, exist_ok=True)
    for key in args.models.split(","):
        est = None
        for ds in args.datasets.split(","):
            path = os.path.join(OUT, f"{key}__{ds}.json")
            if os.path.exists(path) and not args.redo:
                continue
            est = est or E.load(key)
            print(f"{est.name} on {ds} ...", flush=True)
            res, ex = evaluate(est, ds)
            json.dump(res, open(path, "w"), indent=1)
            np.savez_compressed(path[:-5] + "_examples.npz",
                                **{f"{i}_{k}": v for i, e in enumerate(ex)
                                   for k, v in e.items()})
            for a, s in res["arms"].items():
                print(f"  {a:7s} AbsRel {s['absrel']:.3f}  d1 {s['d1']:.3f}  "
                      f"missed stop {100 * s['missed_stop']:5.1f}% (gross {100 * s['gross_miss']:4.1f}%) of {s['frames_obstacle_close']}  "
                      f"false stop {100 * s['false_stop']:5.1f}%  bad heading {100 * s['bad_heading']:5.1f}%",
                      flush=True)
