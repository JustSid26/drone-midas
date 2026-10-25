"""Reactive obstacle-avoidance policy driven by a depth map.

Steers toward the direction of maximum free depth, biased toward the current
station, with a hard safety-stop layer underneath that contains no learned
component.

The depth map is an argument, not something this module produces. Feed it
MuJoCo ground truth today and a MiDaS estimate later; the ablation is the
difference between those two runs on the same seeds.

Depth is planar, measured along the camera axis, which is what MuJoCo returns.
"""
import numpy as np


class ReactivePolicy:
    def __init__(self, fovy_deg, width, height,
                 max_range=8.0,        # beyond this a direction counts as fully open
                 stop_threshold=1.2,   # FR-3 safety trip point, metres
                 release_margin=0.0,   # hysteresis on the stop layer. Tested at 0.25,
                                       # 0.45 and 0.70 m and all were worse, so it is off
                 clear_distance=3.5,   # full speed once this much room is ahead
                 goal_weight=1.8,      # pull toward the station
                 half_span=0.55,       # wingspan/2 plus margin, metres
                 z_band=0.35,          # only obstacles within this of flight level count
                 min_throttle=0.30,    # never creep asymptotically to a halt
                 commit=0.25,          # penalty for abandoning the gap already chosen
                 escape_after=1.0,     # seconds blocked before backing out
                 desperate_after=3.0,  # seconds blocked before ignoring the station
                 flip_cooldown=0.0,    # seconds before the wing guard may switch sides again
                 escape_speed=0.35,    # reverse speed while escaping, m/s (blind, so slow)
                 smoothing=0.25,       # EMA time constant on the chosen heading
                 memory_bins=72,       # short-term all-round obstacle memory
                 forget=0.15,          # metres/second the memory relaxes to open
                 max_speed=2.0, max_yaw=1.8, max_climb=1.0):
        self.max_range = max_range
        self.stop_threshold = stop_threshold
        self.release_margin = release_margin
        self.clear_distance = clear_distance
        self.goal_weight = goal_weight
        self.half_span = half_span
        self.z_band = z_band
        self.min_throttle = min_throttle
        self.commit = commit
        self.escape_after = escape_after
        self.desperate_after = desperate_after
        self.flip_cooldown = flip_cooldown
        self.escape_speed = escape_speed
        self.smoothing = smoothing
        self.max_speed, self.max_yaw, self.max_climb = max_speed, max_yaw, max_climb
        self.width = width

        vfov = np.radians(fovy_deg)
        hfov = 2 * np.arctan(np.tan(vfov / 2) * width / height)
        self.hfov = hfov
        # Image column to yaw offset. The camera is mounted with image-right
        # along body -y, so a column right of centre is a right turn.
        ndc_x = (np.arange(width) + 0.5) / width * 2 - 1
        self.yaw_offset = -np.arctan(ndc_x * np.tan(hfov / 2))
        # Row to height offset, used to throw away floor and ceiling pixels.
        ndc_y = 1 - 2 * (np.arange(height) + 0.5) / height
        self.row_gain = (ndc_y * np.tan(vfov / 2))[:, None]
        self._heading = 0.0
        self._blocked_for = 0.0
        self._turn_dir = 0.0
        self._since_flip = 1e9
        self._was_blocked = False

        # The camera sees a wedge, but the wing sweeps all the way round. Keep a
        # coarse all-round memory so obstacles that leave the frame are not
        # forgotten the instant they stop being visible. This is not a map: it is
        # ego-motion compensated, it decays, and nothing is ever localised.
        self.n_bins = memory_bins
        self.forget = forget
        self.bin_ang = (np.arange(memory_bins) + 0.5) / memory_bins * 2 * np.pi - np.pi
        self.bins = np.full(memory_bins, max_range)
        self._last_v = 0.0
        self._last_w = 0.0

    def reset(self):
        self._heading = 0.0
        self._blocked_for = 0.0
        self._turn_dir = 0.0
        self.bins = np.full(self.n_bins, self.max_range)
        self._since_flip = 1e9
        self._was_blocked = False
        self._last_v = self._last_w = 0.0

    def _update_memory(self, raw, dt):
        """Carry the memory through last step's motion, let it decay, then
        overwrite whatever the camera can currently see."""
        v, w = self._last_v, self._last_w
        x = self.bins * np.cos(self.bin_ang) - v * dt
        y = self.bins * np.sin(self.bin_ang)
        ca, sa = np.cos(-w * dt), np.sin(-w * dt)
        xr, yr = ca * x - sa * y, sa * x + ca * y
        moved = np.full(self.n_bins, self.max_range)
        idx = ((np.arctan2(yr, xr) + np.pi) / (2 * np.pi) * self.n_bins).astype(int) % self.n_bins
        np.minimum.at(moved, idx, np.hypot(xr, yr))
        moved = np.minimum(self.max_range, moved + self.forget * dt)

        fresh = np.full(self.n_bins, np.inf)
        seen = ((self.yaw_offset + np.pi) / (2 * np.pi) * self.n_bins).astype(int) % self.n_bins
        np.minimum.at(fresh, seen, raw)
        visible = np.isfinite(fresh)
        moved[visible] = fresh[visible]
        self.bins = moved

    def _free_per_column(self, depth):
        """Nearest obstacle per column, counting only what sits at flight level,
        then widened so each obstacle casts a shadow as broad as the wing needs
        to clear it at that obstacle's own range."""
        height = depth * self.row_gain               # metres above the camera
        at_level = np.abs(height) < self.z_band
        masked = np.where(at_level, depth, np.inf)
        nearest = masked.min(axis=0)
        raw = np.where(np.isfinite(nearest), nearest, self.max_range)
        raw = np.clip(raw, 0.0, self.max_range)

        # Obstacle at range d blocks every heading within atan(half_span / d).
        k = np.arctan(self.half_span / np.maximum(raw, 0.35))
        sep = np.abs(self.yaw_offset[:, None] - self.yaw_offset[None, :])
        shadowed = sep < k[None, :]
        free = np.where(shadowed, raw[None, :], self.max_range).min(axis=1)
        return free, raw

    def __call__(self, depth, bearing, alt_error, dt):
        """bearing: station direction in the body frame, radians, positive left.
        Returns (forward, strafe, climb, yaw_rate, info)."""
        free, raw = self._free_per_column(depth)
        self._update_memory(raw, dt)

        centre = np.abs(self.yaw_offset) < np.radians(12.0)
        min_front = float(free[centre].min())

        align = np.cos(np.clip(self.yaw_offset - bearing, -np.pi, np.pi))
        # After a long block, ignore the station and simply leave the pocket.
        # Steering toward a station that is behind an obstacle is what keeps the
        # aircraft pinned against it.
        desperate = self._blocked_for > self.desperate_after
        gw = 0.0 if desperate else self.goal_weight
        # The commit term stops the aircraft dithering between two gaps of
        # near-equal value, which otherwise averages its heading to zero.
        stay = np.abs(self.yaw_offset - self._heading) / self.hfov
        score = free / self.max_range + gw * align - self.commit * stay
        best = float(self.yaw_offset[int(np.argmax(score))])

        a = np.exp(-dt / max(self.smoothing, 1e-3)) if self.smoothing > 0 else 0.0
        self._heading = a * self._heading + (1 - a) * best

        # Hysteresis. A single threshold makes the layer chatter on and off at
        # loop rate whenever the aircraft sits near it, which the telemetry trace
        # shows as a sawtooth. Engage low, release higher.
        if self._was_blocked:
            blocked = min_front < self.stop_threshold + self.release_margin
        else:
            blocked = min_front < self.stop_threshold
        self._was_blocked = blocked
        self._blocked_for = self._blocked_for + dt if blocked else 0.0
        escaping = False

        # How much room the wingtip has on each side, from the all round memory.
        reach = self.half_span + 0.25
        left_side = (self.bin_ang > 0.30) & (self.bin_ang < 2.4)
        right_side = (self.bin_ang < -0.30) & (self.bin_ang > -2.4)
        left_clear = float(self.bins[left_side].min())
        right_clear = float(self.bins[right_side].min())

        if blocked:
            # Latch one turn direction and hold it. Choosing again every frame
            # makes the aircraft alternate at loop rate and stay where it is.
            if self._turn_dir == 0.0:
                lf = float(free[self.yaw_offset > 0].mean())
                rf = float(free[self.yaw_offset < 0].mean())
                # A side the wing cannot sweep through is not a candidate at all.
                if left_clear < reach:
                    lf -= 100.0
                if right_clear < reach:
                    rf -= 100.0
                self._turn_dir = 1.0 if lf >= rf else -1.0
            yaw_rate = self._turn_dir * self.max_yaw * 0.85
            # Rotating alone cannot help once the wing is already boxed in.
            escaping = self._blocked_for > self.escape_after
            forward = -self.escape_speed if escaping else 0.0
        else:
            self._turn_dir = 0.0
            span = max(self.clear_distance - self.stop_threshold, 1e-3)
            throttle = np.clip((min_front - self.stop_threshold) / span, 0.0, 1.0)
            throttle = max(throttle, self.min_throttle)   # commit, or declare blocked
            forward = (self.max_speed * throttle
                       * float(np.clip(np.cos(self._heading), 0.25, 1.0))
                       * float(np.clip(np.cos(bearing), 0.20, 1.0)))
            yaw_rate = float(np.clip(2.2 * self._heading, -self.max_yaw, self.max_yaw))

        # Wing guard. Slow a rotation that would sweep the wing into something the
        # memory still holds. It only damps: reversing the latch here is what
        # produced the left and right chatter it was meant to prevent.
        wing_risk = left_clear if yaw_rate > 0 else right_clear
        other_side = right_clear if yaw_rate > 0 else left_clear
        self._since_flip += dt
        if wing_risk < reach:
            if (self.flip_cooldown > 0 and other_side > reach
                    and self._since_flip > self.flip_cooldown):
                # Switch sides, but on a cooldown. Switching every frame is what
                # made the aircraft alternate at loop rate and go nowhere.
                yaw_rate = -yaw_rate
                self._turn_dir = -self._turn_dir
                self._since_flip = 0.0
            else:
                yaw_rate *= 0.15

        climb = float(np.clip(1.5 * alt_error, -self.max_climb, self.max_climb))
        self._last_v, self._last_w = forward, yaw_rate
        info = dict(min_front=min_front, blocked=blocked, escaping=escaping,
                    desperate=desperate,
                    blocked_for=self._blocked_for, heading=float(self._heading),
                    wing_risk=wing_risk, bins=self.bins,
                    free=free, raw=raw, score=score, best=best)
        return float(forward), 0.0, climb, yaw_rate, info
