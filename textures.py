"""Procedural textures for the course.

MiDaS infers depth from texture gradients, shading and detail. A world of flat
grey surfaces gives it almost nothing to work with, so the simulator's visual
realism is a measurement variable, not decoration.
"""
import os
import numpy as np
import cv2

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")


def _fractal(h, w, octaves=6, seed=0, persistence=0.55):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = max(2, int(2 ** (o + 1)))
        layer = rng.random((n, n)).astype(np.float32)
        layer = cv2.resize(layer, (w, h), interpolation=cv2.INTER_CUBIC)
        out += amp * layer
        total += amp
        amp *= persistence
    out /= total
    return (out - out.min()) / (np.ptp(out) + 1e-6)


def _tint(gray, lo, hi):
    lo, hi = np.array(lo, np.float32), np.array(hi, np.float32)
    return np.clip(lo + gray[..., None] * (hi - lo), 0, 255).astype(np.uint8)


def plaster(size=512, seed=1):
    g = _fractal(size, size, 7, seed)
    g = 0.55 + 0.45 * g
    g += 0.05 * _fractal(size, size, 3, seed + 99)
    return _tint(np.clip(g, 0, 1), (168, 163, 152), (232, 228, 219))


def concrete(size=512, seed=2):
    g = _fractal(size, size, 6, seed)
    speck = (np.random.default_rng(seed).random((size, size)) > 0.995).astype(np.float32)
    g = np.clip(0.5 + 0.5 * g - 0.25 * speck, 0, 1)
    return _tint(g, (120, 120, 124), (198, 198, 200))


def wood_floor(size=512, seed=3, planks=9):
    rng = np.random.default_rng(seed)
    grain = _fractal(size, size, 7, seed)
    img = 0.45 + 0.5 * grain
    ph = size // planks
    for i in range(planks):
        y0, y1 = i * ph, min((i + 1) * ph, size)
        img[y0:y1] *= 0.86 + 0.28 * rng.random()
        img[y0:y0 + 2] *= 0.55                      # seam between planks
        shift = rng.integers(0, size)
        img[y0:y1] = np.roll(img[y0:y1], shift, axis=1)
    return _tint(np.clip(img, 0, 1), (58, 74, 104), (128, 158, 196))


def painted(size=256, seed=4, base=(120, 150, 120)):
    g = _fractal(size, size, 5, seed)
    g = 0.72 + 0.28 * g
    b = np.array(base, np.float32)
    return np.clip(g[..., None] * b * 1.25, 0, 255).astype(np.uint8)


def generate():
    os.makedirs(DIR, exist_ok=True)
    made = {}
    for name, img in [("wall", plaster()), ("ceiling", concrete()),
                      ("floor", wood_floor()), ("obs_a", painted(seed=5, base=(120, 150, 120))),
                      ("obs_b", painted(seed=6, base=(150, 130, 165))),
                      ("obs_c", painted(seed=7, base=(160, 155, 120)))]:
        p = os.path.join(DIR, name + ".png")
        cv2.imwrite(p, img)
        made[name] = p
    return made


# Photographic textures ---------------------------------------------------------
#
# The procedural maps above are easy for a person to read as a room but sit far
# outside what MiDaS was trained on. These are photographs of real surfaces from
# Poly Haven (CC0, polyhaven.com), fetched once and committed under textures/photo.

PHOTO_DIR = os.path.join(DIR, "photo")

THEMES = {
    "home":      dict(floor="laminate_floor_02", wall="beige_wall_001", ceiling="ceiling_interior"),
    "office":    dict(floor="dirty_carpet", wall="white_plaster_02", ceiling="ceiling_interior"),
    "warehouse": dict(floor="hangar_concrete_floor", wall="concrete_block_wall", ceiling="concrete_slab_wall"),
    "loft":      dict(floor="plank_flooring", wall="whitewashed_brick", ceiling="white_plaster_02"),
    "school":    dict(floor="tiled_floor_001", wall="painted_plaster_wall", ceiling="ceiling_interior"),
}
OBJECTS = ["kitchen_wood", "wood_cabinet_worn_long", "plywood", "fabric_pattern_07",
           "brown_leather", "painted_concrete", "metal_plate", "leather_white"]


def photo_ids():
    ids = {v for t in THEMES.values() for v in t.values()} | set(OBJECTS)
    return sorted(ids)


def fetch_photo(size=512):
    """Download each texture's 1k diffuse map, shrink it, and record how many
    metres one tile covers so the room can repeat it at true scale."""
    import json, urllib.request
    os.makedirs(PHOTO_DIR, exist_ok=True)
    api = "https://api.polyhaven.com"

    def get(url):     # Poly Haven asks API users to identify themselves
        req = urllib.request.Request(url, headers={"User-Agent": "drone-midas-sim/1.0"})
        return urllib.request.urlopen(req, timeout=60).read()

    info = json.loads(get(f"{api}/assets?t=textures"))
    manifest = {}
    for pid in photo_ids():
        files = json.loads(get(f"{api}/files/{pid}"))
        # A few fabrics come in colour variants instead of one diffuse map.
        key = "Diffuse" if "Diffuse" in files else sorted(k for k in files if k.startswith("col"))[0]
        url = files[key]["1k"]["jpg"]["url"]
        raw = np.frombuffer(get(url), np.uint8)
        img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        cv2.imwrite(os.path.join(PHOTO_DIR, pid + ".png"), cv2.resize(img, (size, size),
                    interpolation=cv2.INTER_AREA))
        dims = info[pid].get("dimensions") or [2000, 2000]      # millimetres
        manifest[pid] = dict(tile_m=[round(dims[0] / 1000, 3), round(dims[1] / 1000, 3)], source=f"https://polyhaven.com/a/{pid}",
                             license="CC0")
        print(f"{pid:26s} tile {manifest[pid]['tile_m']} m", flush=True)
    json.dump(manifest, open(os.path.join(PHOTO_DIR, "manifest.json"), "w"), indent=1)


if __name__ == "__main__":
    import sys
    if "--photo" in sys.argv:
        fetch_photo()
    else:
        for k, v in generate().items():
            print(f"{k:9s} {v}")
