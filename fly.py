"""Fly the VTOL through a seeded indoor course, by hand or on autopilot.

Click stations on the map panel and press N. The aircraft flies the route on
its own, steering by depth and stopping when the safety layer fires.

Motion is kinematic with collision rejection: a move that would intersect
geometry is refused and counted, which is the collision metric the graded
project reports. Real dynamics arrive later with PX4 SITL.

    .venv/bin/python fly.py --seed 0
"""
import argparse, os, time
from collections import deque
import numpy as np
import mujoco
import cv2
import room as roommod
from policy import ReactivePolicy

CAM_W, CAM_H = 320, 240          # what the depth model will eventually see
CHASE_W, CHASE_H = 640, 480
MAP = 480
MAP_X0 = CHASE_W + CAM_W
PANEL_H = 230            # telemetry strip along the bottom

FOVY = 100                       # wide lens; a narrow one cannot protect the wing
SPEED, CLIMB, YAW_RATE = 2.0, 1.2, 1.6
DECAY = 0.35                     # seconds a keypress keeps acting
STOP_THRESHOLD = 1.2             # FR-3 trip point, metres
ARRIVE_RADIUS = 0.7              # station counts as reached inside this
CRUISE_ALT = 1.2

UP    = {63232, 65362, ord('w')}
DOWN  = {63233, 65364, ord('s')}
LEFT  = {63234, 65361}
RIGHT = {63235, 65363}


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class Telemetry:
    """Bottom strip. Live control bars, rolling traces of what the policy is
    commanding, and a log of the events worth noticing."""

    BG = (24, 24, 28)
    GRID = (46, 46, 54)
    LABEL = (150, 150, 162)
    TEXT = (228, 228, 234)
    C_FWD = (120, 220, 255)
    C_YAW = (140, 255, 170)
    C_DEPTH = (255, 185, 110)

    def __init__(self, span=20.0):
        self.span = span
        self.hist = deque(maxlen=1200)
        self.log = deque(maxlen=8)
        self.state = {}

    def sample(self, t, cmd, info):
        self.hist.append((t, float(cmd[0]), float(cmd[3]), float(cmd[2]),
                          float(info.get("min_front", np.nan))))

    def event(self, t, text):
        self.log.append((t, text))

    def latch(self, t, key, value, message):
        """Log only when a condition changes, not every frame it holds."""
        if self.state.get(key) != value:
            self.state[key] = value
            if message:
                self.event(t, message)

    def _bar(self, img, x, y, w, h, value, lo, hi, label, colour):
        cv2.rectangle(img, (x, y), (x + w, y + h), self.GRID, -1)
        zero = x + int(round(w * (0.0 - lo) / (hi - lo)))
        v = x + int(round(w * (float(np.clip(value, lo, hi)) - lo) / (hi - lo)))
        a, b = (zero, v) if v >= zero else (v, zero)
        cv2.rectangle(img, (a, y), (max(b, a + 1), y + h), colour, -1)
        cv2.line(img, (zero, y - 3), (zero, y + h + 3), (130, 130, 142), 1)
        cv2.putText(img, label, (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.40,
                    self.LABEL, 1, cv2.LINE_AA)
        cv2.putText(img, f"{value:+5.2f}", (x + w + 10, y + h - 1),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, self.TEXT, 1, cv2.LINE_AA)

    def _trace(self, img, x, y, w, h, idx, lo, hi, colour, label):
        cv2.rectangle(img, (x, y), (x + w, y + h), self.GRID, 1)
        zero = y + h - int(round(h * (0.0 - lo) / (hi - lo)))
        if y < zero < y + h:
            cv2.line(img, (x, zero), (x + w, zero), self.GRID, 1)
        if len(self.hist) > 1:
            now = self.hist[-1][0]
            pts = []
            for row in self.hist:
                age = now - row[0]
                if age > self.span:
                    continue
                val = row[idx]
                if not np.isfinite(val):
                    continue
                px = x + int(round(w * (1.0 - age / self.span)))
                py = y + h - int(round(h * (float(np.clip(val, lo, hi)) - lo) / (hi - lo)))
                pts.append((px, py))
            if len(pts) > 1:
                cv2.polylines(img, [np.array(pts, np.int32)], False, colour, 1,
                              cv2.LINE_AA)
        cv2.putText(img, label, (x + 5, y + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    colour, 1, cv2.LINE_AA)

    def draw(self, w, h, cmd, info, sim_t):
        img = np.full((h, w, 3), self.BG, np.uint8)
        cv2.line(img, (0, 0), (w, 0), (60, 60, 70), 1)
        c1, c2 = 470, 950
        cv2.line(img, (c1, 10), (c1, h - 10), self.GRID, 1)
        cv2.line(img, (c2, 10), (c2, h - 10), self.GRID, 1)

        cv2.putText(img, "CONTROL OUTPUT", (18, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    self.LABEL, 1, cv2.LINE_AA)
        self._bar(img, 18, 52, 330, 13, cmd[0], -1.0, 2.2, "forward  m/s", self.C_FWD)
        self._bar(img, 18, 96, 330, 13, cmd[3], -2.0, 2.0, "yaw rate  rad/s", self.C_YAW)
        self._bar(img, 18, 140, 330, 13, cmd[2], -1.2, 1.2, "climb  m/s", (200, 180, 120))
        self._bar(img, 18, 184, 330, 13, cmd[1], -2.2, 2.2, "strafe  m/s", (170, 170, 180))

        if info:
            mf = info.get("min_front", float("nan"))
            wr = info.get("wing_risk", float("nan"))
            blocked = info.get("blocked", False)
            state = ("SAFETY STOP" if blocked else "clear")
            col = (90, 90, 255) if blocked else (150, 220, 150)
            cv2.putText(img, "front", (18, 218), cv2.FONT_HERSHEY_SIMPLEX, 0.40,
                        self.LABEL, 1, cv2.LINE_AA)
            cv2.putText(img, f"{mf:4.2f} m", (68, 218), cv2.FONT_HERSHEY_SIMPLEX, 0.44,
                        self.TEXT, 1, cv2.LINE_AA)
            cv2.putText(img, "wing", (150, 218), cv2.FONT_HERSHEY_SIMPLEX, 0.40,
                        self.LABEL, 1, cv2.LINE_AA)
            cv2.putText(img, f"{wr:4.2f} m", (196, 218), cv2.FONT_HERSHEY_SIMPLEX, 0.44,
                        self.TEXT, 1, cv2.LINE_AA)
            cv2.putText(img, state, (285, 218), cv2.FONT_HERSHEY_SIMPLEX, 0.44,
                        col, 1, cv2.LINE_AA)

        cv2.putText(img, f"LAST {self.span:.0f} SECONDS", (c1 + 18, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, self.LABEL, 1, cv2.LINE_AA)
        self._trace(img, c1 + 18, 34, 444, 56, 1, -1.0, 2.2, self.C_FWD, "forward")
        self._trace(img, c1 + 18, 100, 444, 56, 2, -2.0, 2.0, self.C_YAW, "yaw rate")
        self._trace(img, c1 + 18, 166, 444, 56, 4, 0.0, 6.0, self.C_DEPTH,
                    "min frontal depth")
        stop = float(info.get("stop", STOP_THRESHOLD)) if info else STOP_THRESHOLD
        ly = 166 + 56 - int(round(56 * stop / 6.0))
        cv2.line(img, (c1 + 18, ly), (c1 + 462, ly), (70, 70, 130), 1)

        cv2.putText(img, "EVENT LOG", (c2 + 18, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    self.LABEL, 1, cv2.LINE_AA)
        for i, (t, text) in enumerate(self.log):
            yy = 46 + i * 22
            cv2.putText(img, f"{t:6.1f}s", (c2 + 18, yy), cv2.FONT_HERSHEY_SIMPLEX,
                        0.42, self.LABEL, 1, cv2.LINE_AA)
            cv2.putText(img, text, (c2 + 84, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                        self.TEXT, 1, cv2.LINE_AA)
        return img


class Map:
    """Top-down panel. Converts between world metres and panel pixels."""

    def __init__(self, meta):
        self.m = meta
        self.half = meta["room"] / 2.0
        self.s = MAP / meta["room"]

    def to_px(self, wx, wy):
        return (int((wx + self.half) * self.s),
                int(MAP - (wy + self.half) * self.s))

    def to_world(self, px, py):
        return (px / self.s - self.half, (MAP - py) / self.s - self.half)

    def inside_obstacle(self, wx, wy, margin=0.6):
        for o in self.m["obstacles"]:
            if np.hypot(wx - o["x"], wy - o["y"]) < o["r"] + margin:
                return True
        return abs(wx) > self.half - 0.8 or abs(wy) > self.half - 0.8

    def draw(self, pos, yaw, stations, idx, trail, auto, hfov):
        img = np.full((MAP, MAP, 3), 26, np.uint8)
        cv2.rectangle(img, (0, 0), (MAP - 1, MAP - 1), (70, 70, 78), 2)
        for gx in range(1, int(self.m["room"])):
            p = int(gx * self.s)
            cv2.line(img, (p, 0), (p, MAP), (38, 38, 44), 1)
            cv2.line(img, (0, p), (MAP, p), (38, 38, 44), 1)

        for o in self.m["obstacles"]:
            c = self.to_px(o["x"], o["y"])
            r = max(3, int(o["r"] * self.s))
            col = (int(90 + 120 * o["c"]), int(190 - 70 * o["c"]), int(110 + 90 * o["c"]))
            if o["kind"] == "cylinder":
                cv2.circle(img, c, r, col, -1)
            else:
                cv2.rectangle(img, (c[0] - r, c[1] - r), (c[0] + r, c[1] + r), col, -1)

        if len(trail) > 1:
            pts = np.array([self.to_px(p[0], p[1]) for p in trail], np.int32)
            cv2.polylines(img, [pts], False, (90, 90, 110), 1)

        # Route, then the stations on top of it.
        chain = [self.to_px(pos[0], pos[1])] + [self.to_px(s[0], s[1]) for s in stations[idx:]]
        for a, b in zip(chain, chain[1:]):
            cv2.line(img, a, b, (70, 160, 90), 1, cv2.LINE_AA)
        for i, s in enumerate(stations):
            c = self.to_px(s[0], s[1])
            done = i < idx
            col = (80, 80, 88) if done else ((90, 230, 120) if i == idx else (90, 190, 220))
            cv2.circle(img, c, 9, col, -1)
            cv2.circle(img, c, 9, (20, 20, 20), 1)
            cv2.putText(img, str(i + 1), (c[0] - 4, c[1] + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (15, 15, 15), 1, cv2.LINE_AA)
            if i == idx and not done:
                cv2.circle(img, c, int(ARRIVE_RADIUS * self.s), (90, 230, 120), 1)

        # Aircraft: camera wedge, then a triangle pointing along the heading.
        c = self.to_px(pos[0], pos[1])
        reach = 3.0 * self.s
        wedge = [c]
        for a in np.linspace(-hfov / 2, hfov / 2, 12):
            wedge.append((int(c[0] + reach * np.cos(yaw + a)),
                          int(c[1] - reach * np.sin(yaw + a))))
        overlay = img.copy()
        cv2.fillPoly(overlay, [np.array(wedge, np.int32)], (60, 100, 150))
        img = cv2.addWeighted(overlay, 0.22, img, 0.78, 0)

        span = roommod.DRONE_SPAN / 2 * self.s
        nose = roommod.DRONE_LEN / 2 * self.s
        tri = np.array([
            (c[0] + nose * np.cos(yaw), c[1] - nose * np.sin(yaw)),
            (c[0] + span * np.cos(yaw + 2.4), c[1] - span * np.sin(yaw + 2.4)),
            (c[0] + span * np.cos(yaw - 2.4), c[1] - span * np.sin(yaw - 2.4)),
        ], np.int32)
        cv2.fillPoly(img, [tri], (120, 200, 255) if auto else (200, 200, 210))
        cv2.polylines(img, [tri], True, (30, 30, 30), 1)

        cv2.putText(img, "MAP  click to add a station", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (170, 170, 180), 1, cv2.LINE_AA)
        return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--room", type=float, default=10.0)
    ap.add_argument("--obstacles", type=int, default=9)
    ap.add_argument("--show-hull", action="store_true")
    ap.add_argument("--snapshot", metavar="PATH",
                    help="fly a route headlessly and save one composite frame, then exit")
    ap.add_argument("--snapshot-steps", type=int, default=400)
    ap.add_argument("--midas", action="store_true",
                    help="fly on depth estimated by MiDaS instead of simulator truth")
    ap.add_argument("--align", choices=["frozen", "oracle"], default="frozen",
                    help="frozen fits scale and offset once, oracle refits per frame")
    ap.add_argument("--flat", action="store_true", help="untextured world")
    args = ap.parse_args()

    xml, meta = roommod.build(seed=args.seed, room=args.room,
                              n_obstacles=args.obstacles, show_hull=args.show_hull,
                              fovy=FOVY, textured=not args.flat,
                              cam_w=max(CAM_W, CHASE_W), cam_h=max(CAM_H, CHASE_H))
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    fpv = mujoco.Renderer(model, CAM_H, CAM_W)
    chase = mujoco.Renderer(model, CHASE_H, CHASE_W)
    pol = ReactivePolicy(FOVY, CAM_W, CAM_H, stop_threshold=STOP_THRESHOLD, max_speed=SPEED)
    mp = Map(meta)
    tel = Telemetry()

    md = None
    if args.midas:
        import json
        from midas_depth import MidasDepth, depth_metrics
        print("loading MiDaS ...", flush=True)
        md = MidasDepth()
        cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".midas_calib.json")
        key = f"tex{int(not args.flat)}_fovy{FOVY}"
        cal = json.load(open(cache)) if os.path.exists(cache) else {}
        if key in cal:
            md.scale, md.shift = cal[key]
            print(f"calibration from cache  scale {md.scale:.6f}  shift {md.shift:.6f}")
        else:
            from bench_midas import sample_frames
            print("calibrating scale and offset, one time only ...", flush=True)
            cr, cd = sample_frames(range(200, 206), per_seed=5, rng_seed=1)
            md.calibrate(cr, cd)
            cal[key] = [md.scale, md.shift]
            json.dump(cal, open(cache, "w"))
            print(f"calibration  scale {md.scale:.6f}  shift {md.shift:.6f}")
        print(f"depth source: MiDaS-small on {md.device}, {args.align} alignment")

    print(f"course seed {args.seed} | room {args.room:.0f}m | {args.obstacles} obstacles | "
          f"narrowest gap {meta['min_gap']:.2f}m vs {roommod.DRONE_SPAN:.2f}m wingspan")
    print("airframe: " + ("meshes/vtol_shell.stl" if meta["mesh"] else "box placeholder"))

    start = meta["start"]
    st = dict(pos=start.copy(), yaw=0.0, idx=0, auto=False, collisions=0,
              trail=deque(maxlen=600), recover=0.0, done=False, touching=False, t=0.0)
    stations = []
    cmd = np.zeros(4)
    cmd_age = np.full(4, 1e9)
    note = ["click the map to add stations, then press N"]

    def write_pose(p, y):
        data.qpos[0:3] = p
        data.qpos[3:7] = [np.cos(y / 2), 0, 0, np.sin(y / 2)]
        data.qvel[:] = 0
        mujoco.mj_forward(model, data)

    def on_mouse(event, x, y, flags, _):
        if x < MAP_X0 or y >= MAP:
            return
        wx, wy = mp.to_world(x - MAP_X0, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            if mp.inside_obstacle(wx, wy):
                note[0] = "station rejected: too close to an obstacle or wall"
                return
            stations.append(np.array([wx, wy, CRUISE_ALT]))
            st["done"] = False
            note[0] = f"station {len(stations)} at {wx:+.1f}, {wy:+.1f}"
        elif event == cv2.EVENT_RBUTTONDOWN and stations:
            k = int(np.argmin([np.hypot(s[0] - wx, s[1] - wy) for s in stations]))
            stations.pop(k)
            st["idx"] = min(st["idx"], len(stations))
            note[0] = f"removed station {k + 1}"

    write_pose(st["pos"], st["yaw"])
    headless = bool(args.snapshot)
    if headless:
        rng = np.random.default_rng(args.seed + 9973)
        half = args.room / 2
        placed = 0
        while placed < 5:
            p = rng.uniform(-half + 1.4, half - 1.4, 2)
            if not mp.inside_obstacle(p[0], p[1], margin=0.9):
                stations.append(np.array([p[0], p[1], CRUISE_ALT]))
                placed += 1
        st["auto"] = True
        note[0] = "AUTO engaged"
    else:
        cv2.namedWindow("VTOL course", cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback("VTOL course", on_mouse)
    steps = 0
    last = time.time()

    while True:
        now = time.time()
        dt = 0.05 if headless else min(now - last, 0.05)
        last = now
        steps += 1
        st["t"] += dt

        # 1. See. Render before deciding, so the command follows the image.
        fpv.disable_depth_rendering()
        fpv.update_scene(data, camera="fpv"); rgb = fpv.render()
        fpv.enable_depth_rendering()
        fpv.update_scene(data, camera="fpv"); true_depth = fpv.render()
        if md is not None:
            depth = md.metric_depth(rgb, true_depth, mode=args.align)
            if steps % 10 == 0:
                st["derr"] = depth_metrics(depth, true_depth)
        else:
            depth = true_depth

        key = -1 if headless else cv2.waitKeyEx(1)
        if key != -1:
            if key in (27, ord('q')):
                break
            elif key in (ord('n'), ord('N')):
                st["auto"] = not st["auto"]
                pol.reset(); cmd[:] = 0
                note[0] = "AUTO engaged" if st["auto"] else "manual control"
                tel.event(st["t"], note[0])
            elif key in (ord('c'), ord('C')):
                stations.clear(); st["idx"] = 0; st["done"] = False
                note[0] = "stations cleared"
                tel.event(st["t"], note[0])
            elif key == ord(' '):
                st.update(pos=start.copy(), yaw=0.0, idx=0, collisions=0,
                          recover=0.0, done=False, touching=False, t=0.0)
                st["trail"].clear(); pol.reset(); cmd[:] = 0
                write_pose(st["pos"], st["yaw"]); note[0] = "reset"
                tel.log.clear(); tel.hist.clear(); tel.state.clear()
                tel.event(0.0, "reset to start")
                continue
            elif not st["auto"]:
                if key in UP:      cmd[0], cmd_age[0] =  SPEED, 0.0
                elif key in DOWN:  cmd[0], cmd_age[0] = -SPEED, 0.0
                elif key == ord('a'): cmd[1], cmd_age[1] =  SPEED, 0.0
                elif key == ord('d'): cmd[1], cmd_age[1] = -SPEED, 0.0
                elif key == ord('r'): cmd[2], cmd_age[2] =  CLIMB, 0.0
                elif key == ord('f'): cmd[2], cmd_age[2] = -CLIMB, 0.0
                elif key in LEFT:  cmd[3], cmd_age[3] =  YAW_RATE, 0.0
                elif key in RIGHT: cmd[3], cmd_age[3] = -YAW_RATE, 0.0

        # 2. Decide.
        info, bearing, dist = {}, 0.0, 0.0
        if st["auto"] and stations and not st["done"]:
            wp = stations[st["idx"]]
            to = wp[:2] - st["pos"][:2]
            dist = float(np.linalg.norm(to))
            if dist < ARRIVE_RADIUS:
                tel.event(st["t"], f"station {st['idx']+1} reached")
                st["idx"] += 1
                if st["idx"] >= len(stations):
                    st["done"] = True; st["auto"] = False; cmd[:] = 0
                    note[0] = f"route complete in {st['t']:.1f}s"
                    tel.event(st["t"], note[0])
                continue
            bearing = wrap(np.arctan2(to[1], to[0]) - st["yaw"])
            f, s, c, y, info = pol(depth, bearing, wp[2] - st["pos"][2], dt)
            tel.latch(st["t"], "blocked", info["blocked"],
                      "safety stop engaged" if info["blocked"] else "safety stop cleared")
            tel.latch(st["t"], "escaping", info["escaping"],
                      "backing out of a pocket" if info["escaping"] else None)
            tel.latch(st["t"], "wing", info["wing_risk"] < 0.8,
                      "wing clearance tight" if info["wing_risk"] < 0.8 else None)
            if st["recover"] > 0:            # turn away after a contact
                st["recover"] -= dt
                f, y = -0.5, (np.sign(info["heading"]) or 1.0) * YAW_RATE
            cmd[:] = [f, s, c, y]
        elif not st["auto"]:
            cmd_age += dt
            cmd[cmd_age > DECAY] = 0.0

        # 3. Move, refusing anything that would intersect the world.
        cy, sy = np.cos(st["yaw"]), np.sin(st["yaw"])
        step = np.array([cy * cmd[0] - sy * cmd[1],
                         sy * cmd[0] + cy * cmd[1], cmd[2]]) * dt
        new_pos, new_yaw = st["pos"] + step, st["yaw"] + cmd[3] * dt

        def clear(p, a):
            write_pose(p, a)
            return data.ncon == 0

        if clear(new_pos, new_yaw):
            st["touching"] = False
            st["pos"], st["yaw"] = new_pos, new_yaw
        else:
            # Refusing the whole move leaves a wedged aircraft unable even to
            # turn away, and since the view never changes it reissues the same
            # command forever. Fall back to rotating alone, then translating alone.
            if not st["touching"]:      # count contact events, not frames in contact
                st["collisions"] += 1
                tel.event(st["t"], f"contact {st['collisions']}")
            st["touching"] = True
            if clear(st["pos"], new_yaw):
                st["yaw"] = new_yaw          # rotating free is safe
            elif clear(new_pos, st["yaw"]):
                st["pos"] = new_pos          # matches run_route fallback='both'
            else:
                write_pose(st["pos"], st["yaw"])
            if st["auto"]:
                st["recover"] = 0.6
            else:
                cmd[:] = 0
        st["trail"].append(st["pos"].copy())

        # 4. Draw.
        chase.disable_depth_rendering()
        chase.update_scene(data, camera="chase"); over = chase.render()
        def dviz(d, h):
            v = np.clip((d - 0.4) / 7.6, 0, 1)
            im = cv2.applyColorMap((255 * (1 - v)).astype(np.uint8), cv2.COLORMAP_TURBO)
            return cv2.resize(im, (CAM_W, h))

        if md is not None:
            ch = 160
            mid = np.vstack([cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (CAM_W, ch)),
                             dviz(depth, ch), dviz(true_depth, ch)])
            labels = [("camera", 0), ("MiDaS depth  (flying on this)", ch),
                      ("ground truth  (reference only)", 2 * ch)]
        else:
            mid = np.vstack([cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), dviz(depth, CAM_H)])
            labels = [("camera", 0), ("ground-truth depth", CAM_H)]
        panel = mp.draw(st["pos"], st["yaw"], stations, st["idx"],
                        st["trail"], st["auto"], pol.hfov)
        top = np.hstack([cv2.cvtColor(over, cv2.COLOR_RGB2BGR), mid, panel])
        tel.sample(st["t"], cmd, info)
        frame = np.vstack([top, tel.draw(top.shape[1], PANEL_H, cmd, info, st["t"])])

        # Build the heads-up lines first, then lay a translucent panel behind them.
        # Never outline text by drawing it twice at two thicknesses: OpenCV widens
        # character advance with stroke weight, so the passes drift apart and the
        # end of every line renders doubled.
        mode = "AUTO" if st["auto"] else ("DONE" if st["done"] else "MANUAL")
        lines = [(f"{mode}   seed {args.seed}   t {st['t']:5.1f}s",
                  (120, 220, 255) if st["auto"] else (240, 240, 240)),
                 (f"pos {st['pos'][0]:+5.2f} {st['pos'][1]:+5.2f} {st['pos'][2]:4.2f}"
                  f"   yaw {np.degrees(st['yaw']):+6.1f}", (235, 235, 235))]
        if stations:
            lines.append((f"station {min(st['idx']+1, len(stations))}/{len(stations)}"
                          f"   {dist:4.2f} m   bearing {np.degrees(bearing):+5.1f}",
                          (235, 235, 235)))
        lines.append((f"collisions {st['collisions']}",
                      (120, 120, 255) if st["collisions"] else (235, 235, 235)))
        if info:
            lines.append((f"min frontal depth {info['min_front']:4.2f} m",
                          (90, 90, 255) if info["blocked"] else (235, 235, 235)))
            if info["blocked"]:
                lines.append(("SAFETY STOP ACTIVE"
                              + ("  (backing out)" if info["escaping"] else ""), (70, 70, 255)))
            if info["wing_risk"] < 0.8:
                lines.append((f"wing clearance {info['wing_risk']:4.2f} m", (90, 170, 255)))
        if md is not None:
            e = st.get("derr") or {}
            lines.append((f"depth  MiDaS {args.align}"
                          + (f"   AbsRel {e['absrel']:.2f}   within 1.25  {e['d1']:.2f}"
                             if e else ""), (140, 200, 255)))
        else:
            lines.append(("depth  simulator ground truth", (170, 210, 170)))
        if note[0]:
            lines.append((note[0], (150, 215, 245)))

        FONT, SC, TH = cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1
        pad, step, x0, y0 = 9, 20, 14, 26
        wide = max(cv2.getTextSize(t, FONT, SC, TH)[0][0] for t, _ in lines)
        h = y0 + step * (len(lines) - 1) + pad
        box = frame[0:h + 4, 0:x0 + wide + pad * 2]
        frame[0:h + 4, 0:x0 + wide + pad * 2] = cv2.addWeighted(
            box, 0.35, np.zeros_like(box), 0.65, 0)
        for i, (txt, col) in enumerate(lines):
            cv2.putText(frame, txt, (x0, y0 + i * step), FONT, SC, col, TH, cv2.LINE_AA)

        for text, yoff in labels:
            cv2.putText(frame, text, (CHASE_W + 10, yoff + 18), FONT, 0.42,
                        (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, text, (CHASE_W + 10, yoff + 18), FONT, 0.42,
                        (255, 255, 255), 1, cv2.LINE_AA)

        help_txt = ("click map = station    right-click = remove    N auto    C clear"
                    "    arrows and a d r f manual    space reset    q quit")
        hw = cv2.getTextSize(help_txt, FONT, 0.44, 1)[0][0]
        hy = CHASE_H - 24
        strip = frame[hy:CHASE_H, 0:hw + 24]
        frame[hy:CHASE_H, 0:hw + 24] = cv2.addWeighted(
            strip, 0.3, np.zeros_like(strip), 0.7, 0)
        cv2.putText(frame, help_txt, (12, CHASE_H - 8), FONT, 0.44,
                    (185, 185, 195), 1, cv2.LINE_AA)

        if headless:
            if steps >= args.snapshot_steps or st["done"]:
                cv2.imwrite(args.snapshot, frame)
                print(f"wrote {args.snapshot} after {steps} steps")
                break
            continue
        cv2.imshow("VTOL course", frame)

    if not headless:
        cv2.destroyAllWindows()
    print(f"collisions {st['collisions']} | stations reached {st['idx']}/{len(stations)}")


if __name__ == "__main__":
    main()
