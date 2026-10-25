"""Headless autopilot runs. Scores a route without opening a window.

    .venv/bin/python run_route.py --seeds 0-9 --stations 4

Reports per seed whether every station was reached, how many contacts occurred
and how long it took. This is the harness the graded evaluation runs on: swap
the depth source and re-run the same seeds to get the ablation.
"""
import argparse
import numpy as np
import mujoco
import room as roommod
from policy import ReactivePolicy

CAM_W, CAM_H = 320, 240
ARRIVE_RADIUS, CRUISE_ALT = 0.7, 1.2
DT, MAX_TIME = 0.05, 120.0


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def sample_stations(meta, n, rng):
    """Free points, spread out, away from obstacles and walls."""
    half, out = meta["room"] / 2, []
    for _ in range(4000):
        if len(out) == n:
            break
        p = rng.uniform(-half + 1.2, half - 1.2, 2)
        if any(np.hypot(p[0] - o["x"], p[1] - o["y"]) < o["r"] + 0.8 for o in meta["obstacles"]):
            continue
        if any(np.linalg.norm(p - q) < 2.5 for q in out):
            continue
        out.append(p)
    return [np.array([p[0], p[1], CRUISE_ALT]) for p in out]


def run(seed, n_stations, obstacles, room, depth_fn=None, grid_pitch=2.5,
        fovy=70, fallback='rotate', **policy_kw):
    xml, meta = roommod.build(seed=seed, room=room, n_obstacles=obstacles,
                              grid_pitch=grid_pitch, fovy=fovy,
                              cam_w=CAM_W, cam_h=CAM_H)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    r = mujoco.Renderer(model, CAM_H, CAM_W)
    rgb_r = mujoco.Renderer(model, CAM_H, CAM_W) if depth_fn is not None else None
    pol = ReactivePolicy(fovy, CAM_W, CAM_H, **policy_kw)

    rng = np.random.default_rng(seed + 9973)
    stations = sample_stations(meta, n_stations, rng)
    pos, yaw = meta["start"].copy(), 0.0
    idx, collisions, t, recover, touching = 0, 0, 0.0, 0.0, False
    min_clear = np.inf

    def write(p, y):
        data.qpos[0:3] = p
        data.qpos[3:7] = [np.cos(y / 2), 0, 0, np.sin(y / 2)]
        data.qvel[:] = 0
        mujoco.mj_forward(model, data)

    write(pos, yaw)
    while t < MAX_TIME and idx < len(stations):
        r.enable_depth_rendering()
        r.update_scene(data, camera="fpv")
        depth = r.render()
        if depth_fn is not None:
            # The estimator needs the colour image. The true depth goes with it so
            # an oracle alignment arm is possible, and so the harness can score
            # depth error along the same trajectory the aircraft actually flew.
            rgb_r.update_scene(data, camera="fpv")
            depth = depth_fn(rgb_r.render(), depth)

        wp = stations[idx]
        to = wp[:2] - pos[:2]
        if np.linalg.norm(to) < ARRIVE_RADIUS:
            idx += 1
            continue
        bearing = wrap(np.arctan2(to[1], to[0]) - yaw)
        f, s, c, y, info = pol(depth, bearing, wp[2] - pos[2], DT)
        min_clear = min(min_clear, info["min_front"])
        if recover > 0:
            recover -= DT
            f, y = -0.5, (np.sign(info["heading"]) or 1.0) * 1.6

        cy, sy = np.cos(yaw), np.sin(yaw)
        step = np.array([cy * f - sy * s, sy * f + cy * s, c]) * DT
        cand_p, cand_y = pos + step, yaw + y * DT

        def clear(p, a):
            write(p, a)
            return data.ncon == 0

        if clear(cand_p, cand_y):
            touching = False
            pos, yaw = cand_p, cand_y
        else:
            # Refusing the whole move leaves a wedged aircraft unable even to
            # turn away, and since the view never changes it reissues the same
            # command forever. Fall back to rotating alone, then to translating
            # alone, so it can always work itself free.
            if not touching:          # count contact events, not frames in contact
                collisions += 1
            touching = True
            recover = 0.6
            if fallback != 'none' and clear(pos, cand_y):
                yaw = cand_y                       # rotating free is safe
            elif fallback == 'both' and clear(cand_p, yaw):
                pos = cand_p
            else:
                write(pos, yaw)
        t += DT

    return dict(seed=seed, reached=idx, total=len(stations), collisions=collisions,
                time=t, timeout=t >= MAX_TIME, min_clear=float(min_clear))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0-9", help="e.g. 0-49 or 3,7,11")
    ap.add_argument("--stations", type=int, default=4)
    ap.add_argument("--obstacles", type=int, default=9)
    ap.add_argument("--room", type=float, default=10.0)
    args = ap.parse_args()

    if "-" in args.seeds and "," not in args.seeds:
        a, b = args.seeds.split("-")
        seeds = range(int(a), int(b) + 1)
    else:
        seeds = [int(x) for x in args.seeds.split(",")]

    rows = [run(s, args.stations, args.obstacles, args.room) for s in seeds]
    print(f"{'seed':>5}{'stations':>10}{'contacts':>10}{'time(s)':>9}{'min clear':>11}  result")
    for r in rows:
        ok = r["reached"] == r["total"] and r["collisions"] == 0
        verdict = "clean" if ok else ("contact" if r["collisions"] else "timeout")
        print(f"{r['seed']:>5}{r['reached']:>6}/{r['total']:<3}{r['collisions']:>10}"
              f"{r['time']:>9.1f}{r['min_clear']:>11.2f}  {verdict}")

    n = len(rows)
    full = sum(r["reached"] == r["total"] for r in rows)
    clean = sum(r["reached"] == r["total"] and r["collisions"] == 0 for r in rows)
    print(f"\nroute completed {full}/{n}   collision-free completion {clean}/{n} "
          f"({100*clean/n:.0f}%)   mean contacts {np.mean([r['collisions'] for r in rows]):.1f}")


if __name__ == "__main__":
    main()
