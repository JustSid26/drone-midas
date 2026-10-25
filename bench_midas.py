"""Depth quality and speed of MiDaS-small on simulator imagery."""
import time, numpy as np, mujoco, room as R
from midas_depth import MidasDepth, depth_metrics

CAM_W, CAM_H, FOVY = 320, 240, 100


def sample_frames(seeds, per_seed=6, rng_seed=0):
    rng = np.random.default_rng(rng_seed)
    rgbs, deps = [], []
    for sd in seeds:
        xml, meta = R.build(seed=sd, room=10.0, n_obstacles=9, fovy=FOVY,
                            cam_w=CAM_W, cam_h=CAM_H)
        m = mujoco.MjModel.from_xml_string(xml)
        d = mujoco.MjData(m)
        r = mujoco.Renderer(m, CAM_H, CAM_W)
        half = meta["room"] / 2
        for _ in range(per_seed):
            p = np.array([rng.uniform(-half + 1.5, half - 1.5),
                          rng.uniform(-half + 1.5, half - 1.5), 1.2])
            yaw = rng.uniform(-np.pi, np.pi)
            d.qpos[0:3] = p
            d.qpos[3:7] = [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
            d.qvel[:] = 0
            mujoco.mj_forward(m, d)
            r.disable_depth_rendering(); r.update_scene(d, camera="fpv")
            rgbs.append(r.render().copy())
            r.enable_depth_rendering(); r.update_scene(d, camera="fpv")
            deps.append(r.render().copy())
    return rgbs, deps


if __name__ == "__main__":
    print("sampling frames from the simulator ...", flush=True)
    cal_rgb, cal_d = sample_frames(range(200, 206), per_seed=5, rng_seed=1)
    ev_rgb, ev_d = sample_frames(range(210, 220), per_seed=6, rng_seed=2)
    print(f"calibration frames {len(cal_rgb)}   evaluation frames {len(ev_rgb)}\n")

    md = MidasDepth()
    print("device:", md.device, "\n")

    s, t = md.calibrate(cal_rgb, cal_d)
    print(f"frozen calibration  scale {s:.5f}  shift {t:.5f}\n")

    for mode in ("oracle", "frozen"):
        agg = []
        for rgb, dt_ in zip(ev_rgb, ev_d):
            pred = md.metric_depth(rgb, dt_, mode=mode)
            mm = depth_metrics(pred, dt_)
            if mm:
                agg.append(mm)
        k = lambda key: float(np.mean([a[key] for a in agg]))
        print(f"{mode:>7} alignment   AbsRel {k('absrel'):.3f}   RMSE {k('rmse'):.2f} m   "
              f"delta<1.25 {k('d1'):.3f}   delta<1.25^2 {k('d2'):.3f}")

    n = 40
    md.inverse_depth(ev_rgb[0])
    t0 = time.time()
    for i in range(n):
        md.inverse_depth(ev_rgb[i % len(ev_rgb)])
    dt = (time.time() - t0) / n
    print(f"\nspeed on {md.device}: {1000*dt:.1f} ms per frame, {1/dt:.1f} FPS")
