"""MiDaS-small as a depth source for the avoidance policy.

The network returns inverse depth with an unknown scale and an unknown offset,
so it cannot be handed to the policy directly. Both terms are recovered by a
least squares fit. Median scaling corrects only the scale and would leave a
systematic error behind.
"""
import os
import numpy as np
import torch

os.environ.setdefault("TORCH_HOME", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".torch"))


def fit_scale_shift(pred, target, mask=None):
    """Least squares s and t minimising sum (s*pred + t - target)^2.

    Both arrays are inverse depth. Closed form two by two solve, which is the
    alignment the MiDaS authors evaluate with.
    """
    p = pred.reshape(-1).astype(np.float64)
    q = target.reshape(-1).astype(np.float64)
    if mask is not None:
        m = mask.reshape(-1)
        p, q = p[m], q[m]
    if p.size < 16:
        return 1.0, 0.0
    a00 = float(np.dot(p, p)); a01 = float(p.sum())
    a11 = float(p.size)
    b0 = float(np.dot(p, q)); b1 = float(q.sum())
    det = a00 * a11 - a01 * a01
    if abs(det) < 1e-12:
        return 1.0, 0.0
    s = (a11 * b0 - a01 * b1) / det
    t = (-a01 * b0 + a00 * b1) / det
    return s, t


class MidasDepth:
    def __init__(self, device=None, model_type="MiDaS_small"):
        if device is None:
            device = ("mps" if torch.backends.mps.is_available()
                      else "cuda" if torch.cuda.is_available() else "cpu")
        self.device = torch.device(device)
        self.model = torch.hub.load("intel-isl/MiDaS", model_type, trust_repo=True)
        self.model.to(self.device).eval()
        tfs = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
        self.transform = (tfs.small_transform if model_type == "MiDaS_small"
                          else tfs.dpt_transform)
        self.scale, self.shift = None, None      # frozen calibration, if any

    @torch.no_grad()
    def inverse_depth(self, rgb):
        """One colour image in, raw inverse depth out at the input resolution."""
        h, w = rgb.shape[:2]
        # The hub transform divides by 255 itself, so hand it a 0 to 255 image.
        # Scaling here as well leaves the network looking at a near black frame,
        # which makes it emit a generic ground plane ramp regardless of content.
        img = rgb.astype(np.float32)
        x = self.transform(img).to(self.device)
        y = self.model(x)
        y = torch.nn.functional.interpolate(y.unsqueeze(1), size=(h, w),
                                            mode="bicubic", align_corners=False)
        return y.squeeze().float().cpu().numpy()

    def calibrate(self, rgb_frames, true_depths, max_range=10.0):
        """Freeze one scale and offset across a set of frames. This stands in for
        the calibration a real aircraft would do against a known height."""
        preds, targets = [], []
        for rgb, d in zip(rgb_frames, true_depths):
            inv = self.inverse_depth(rgb)
            m = np.isfinite(d) & (d > 0.2) & (d < max_range)
            preds.append(inv[m]); targets.append(1.0 / d[m])
        p = np.concatenate(preds); q = np.concatenate(targets)
        self.scale, self.shift = fit_scale_shift(p, q)
        return self.scale, self.shift

    def metric_depth(self, rgb, true_depth=None, mode="frozen",
                     max_range=10.0, far=1000.0):
        """Depth in metres. mode 'oracle' refits per frame against the true depth
        and is an upper bound rather than something an aircraft could do. Mode
        'frozen' uses the calibration and is the honest arm."""
        inv = self.inverse_depth(rgb)
        if mode == "oracle":
            if true_depth is None:
                raise ValueError("oracle alignment needs the true depth")
            m = np.isfinite(true_depth) & (true_depth > 0.2) & (true_depth < max_range)
            s, t = fit_scale_shift(inv, 1.0 / np.where(m, true_depth, 1.0), m)
        else:
            if self.scale is None:
                raise RuntimeError("call calibrate() before using frozen mode")
            s, t = self.scale, self.shift
        aligned = s * inv + t
        depth = np.where(aligned > 1e-3, 1.0 / np.maximum(aligned, 1e-3), far)
        return np.clip(depth, 0.0, far).astype(np.float32)


def depth_metrics(pred, true, lo=0.2, hi=10.0):
    """AbsRel and the delta thresholds the literature reports."""
    m = np.isfinite(true) & (true > lo) & (true < hi) & np.isfinite(pred)
    p, q = pred[m], true[m]
    if p.size == 0:
        return {}
    ratio = np.maximum(p / q, q / p)
    return dict(absrel=float(np.mean(np.abs(p - q) / q)),
                rmse=float(np.sqrt(np.mean((p - q) ** 2))),
                d1=float(np.mean(ratio < 1.25)),
                d2=float(np.mean(ratio < 1.25 ** 2)),
                n=int(p.size))
