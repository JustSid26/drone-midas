"""Real indoor RGB-D data for testing the depth estimators outside the simulator.

Three public datasets, chosen to cover different questions:

    nyu      NYU Depth V2 labelled set. Kinect depth in 1449 homes and offices.
             The standard indoor benchmark, so numbers compare with the literature.
             Evaluated on the official 654 test images, calibrated on train images.
    diode    DIODE indoor validation set. Laser scanner depth, accurate to far range.
    tum_*    TUM RGB-D sequences. Continuous video moving through a room, which is
             the closest thing here to what the aircraft camera sees in flight.

Download once with  .venv/bin/python indoor_data.py --download
Everything lands in data/, which git ignores.

Every frame comes out as a dict with rgb (H,W,3 uint8), depth (H,W float32 metres,
0 where invalid) and fy, the vertical focal length in pixels.
"""
import argparse, glob, os, subprocess, tarfile
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

URLS = {
    "nyu/nyu_depth_v2_labeled.mat":
        "http://horatio.cs.nyu.edu/mit/silberman/nyu_depth_v2/nyu_depth_v2_labeled.mat",
    # The official copy of the split file is gone from the NYU server.
    "nyu_splits/splits.mat":
        "https://raw.githubusercontent.com/cleinc/bts/master/utils/splits.mat",
    "diode/val.tar.gz": "http://diode-dataset.s3.amazonaws.com/val.tar.gz",
    "tum/fr1_room.tgz":
        "https://cvg.cit.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_room.tgz",
    "tum/fr2_pioneer_360.tgz":
        "https://cvg.cit.tum.de/rgbd/dataset/freiburg2/rgbd_dataset_freiburg2_pioneer_360.tgz",
}

TUM_SEQ = {"tum_room": "rgbd_dataset_freiburg1_room",
           "tum_pioneer": "rgbd_dataset_freiburg2_pioneer_360"}
TUM_FY = {"tum_room": 516.5, "tum_pioneer": 521.0}

# Eigen crop, the region every NYU result in the literature is scored on.
NYU_CROP = (45, 471, 41, 601)
NYU_FY = 519.47
DIODE_FY = 927.06                # fx is 886.81; the policy needs the vertical one


def download():
    for rel, url in URLS.items():
        path = os.path.join(DATA, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print("fetching", rel, flush=True)
        subprocess.run(["curl", "-L", "-C", "-", "-o", path, url], check=True)
    _extract(os.path.join(DATA, "diode/val.tar.gz"), os.path.join(DATA, "diode"),
             member_prefix="val/indoors/")
    for seq in TUM_SEQ:
        name = "fr1_room" if seq == "tum_room" else "fr2_pioneer_360"
        _extract(os.path.join(DATA, f"tum/{name}.tgz"), os.path.join(DATA, "tum"))


def _extract(archive, dest, member_prefix=""):
    with tarfile.open(archive) as tf:
        members = [m for m in tf.getmembers() if m.name.startswith(member_prefix)]
        tf.extractall(dest, members=members, filter="data")


def despeckle(depth, tol=0.25):
    """Drop isolated returns. Laser scanners and Kinects leave stray points at
    object edges; the policy takes a minimum per column, so a single stray
    point at 0.3 m reads as an obstacle, and in inverse depth it also outweighs
    a whole wall in any fit. A pixel more than tol away from its 5x5 median,
    relatively, is marked invalid."""
    d = depth.astype(np.float32)
    med = cv2.medianBlur(d, 5)
    bad = (d > 0) & (np.abs(d - med) > tol * np.maximum(med, 1e-3))
    return np.where(bad, 0.0, d).astype(np.float32)


# NYU --------------------------------------------------------------------------

def nyu(split="test", limit=None):
    """Official split. The .mat stores images transposed, column-major."""
    import h5py, scipy.io as sio
    idx = sio.loadmat(os.path.join(DATA, "nyu_splits/splits.mat"))
    ndx = idx["testNdxs" if split == "test" else "trainNdxs"].ravel() - 1
    if limit:
        ndx = ndx[:limit]
    y0, y1, x0, x1 = NYU_CROP
    with h5py.File(os.path.join(DATA, "nyu/nyu_depth_v2_labeled.mat"), "r") as f:
        for i in ndx:
            rgb = np.ascontiguousarray(f["images"][i].transpose(2, 1, 0))
            depth = np.ascontiguousarray(f["depths"][i].T).astype(np.float32)
            crop = np.zeros(depth.shape, bool)
            crop[y0:y1, x0:x1] = True
            yield dict(id=f"nyu{i + 1}", rgb=rgb, depth=despeckle(np.where(crop, depth, 0.0)),
                       fy=NYU_FY, group="nyu")


# DIODE ------------------------------------------------------------------------

def diode_scenes():
    return sorted(glob.glob(os.path.join(DATA, "diode/val/indoors/scene_*")))


def diode(scenes):
    for sc in scenes:
        for rgb_path in sorted(glob.glob(os.path.join(sc, "*", "*.png"))):
            stem = rgb_path[:-4]
            depth = np.load(stem + "_depth.npy", allow_pickle=False)[..., 0]
            mask = np.load(stem + "_depth_mask.npy", allow_pickle=False) > 0
            rgb = cv2.cvtColor(cv2.imread(rgb_path), cv2.COLOR_BGR2RGB)
            yield dict(id=os.path.basename(stem), rgb=rgb,
                       depth=despeckle(np.where(mask, depth, 0.0)),
                       fy=DIODE_FY, group=os.path.basename(sc))


# TUM --------------------------------------------------------------------------

def _tum_list(path):
    out = []
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        t, f = line.split()[:2]
        out.append((float(t), f))
    return out


def tum_pairs(seq, stride=3, max_dt=0.02):
    """Pair each colour frame with the depth frame nearest in time."""
    root = os.path.join(DATA, "tum", TUM_SEQ[seq])
    rgbs = _tum_list(os.path.join(root, "rgb.txt"))
    deps = _tum_list(os.path.join(root, "depth.txt"))
    dt = np.array([t for t, _ in deps])
    pairs = []
    for t, f in rgbs[::stride]:
        j = int(np.argmin(np.abs(dt - t)))
        if abs(dt[j] - t) < max_dt:
            pairs.append((os.path.join(root, f), os.path.join(root, deps[j][1])))
    return pairs


def tum(seq, pairs):
    for rgb_path, d_path in pairs:
        rgb = cv2.cvtColor(cv2.imread(rgb_path), cv2.COLOR_BGR2RGB)
        depth = cv2.imread(d_path, cv2.IMREAD_UNCHANGED).astype(np.float32) / 5000.0
        yield dict(id=os.path.basename(rgb_path), rgb=rgb, depth=despeckle(depth),
                   fy=TUM_FY[seq], group=seq)


# The simulator, scored exactly like the real data ---------------------------------

def sim(style, seeds, per_seed, rng_seed):
    from bench_midas import sample_frames, CAM_H, FOVY
    fy = CAM_H / 2 / np.tan(np.radians(FOVY) / 2)
    for sd in seeds:
        rgbs, deps = sample_frames([sd], per_seed=per_seed, rng_seed=rng_seed * 1000 + sd, style=style)
        for k, (rgb, d) in enumerate(zip(rgbs, deps)):
            yield dict(id=f"sim{sd}_{k}", rgb=rgb, depth=d.astype(np.float32), fy=fy, group=f"sim_{style}")


# Calibration and test splits ----------------------------------------------------

def splits(name):
    """(calibration frames, test frames, note). Calibration always comes from the
    same place as the test frames but never overlaps them: the most generous
    setting a frozen calibration can get."""
    if name == "nyu":
        return (lambda: nyu("train", limit=100), lambda: nyu("test"),
                "calibrate on 100 train images, test on the official 654")
    if name == "diode":
        sc = diode_scenes()
        return (lambda: diode(sc[:1]), lambda: diode(sc[1:]),
                f"calibrate on scene {os.path.basename(sc[0])}, test on the other {len(sc) - 1}")
    if name.startswith("sim_"):
        style = name[4:]
        return (lambda: sim(style, range(200, 206), 5, 1), lambda: sim(style, range(210, 240), 6, 2),
                "simulator: calibrate on 30 frames from seeds 200-205, test on 180 from seeds 210-239")
    if name in TUM_SEQ:
        pairs = tum_pairs(name)
        k = max(10, len(pairs) * 15 // 100)
        return (lambda: tum(name, pairs[:k]), lambda: tum(name, pairs[k:]),
                f"calibrate on the first {k} frames of the video, test on the remaining {len(pairs) - k}")
    raise KeyError(name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args()
    if args.download:
        download()
    for name in ["nyu", "diode", "tum_room", "tum_pioneer"]:
        try:
            cal, test, note = splits(name)
            n = sum(1 for _ in test())
            print(f"{name:12s} {n:5d} test frames   {note}")
        except Exception as e:
            print(f"{name:12s} not available: {e}")
