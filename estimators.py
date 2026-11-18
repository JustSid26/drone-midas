"""Monocular depth networks behind one interface, for the real data comparison.

Every estimator returns inverse depth at the input resolution. For the relative
models that is only correct up to an unknown scale and offset, which the
alignment in eval_real.py recovers. The metric model's inverse depth is already
in 1/metres, so it can also be scored with no alignment at all.
"""
import time
import numpy as np
import torch

from midas_depth import MidasDepth


def _device():
    return ("mps" if torch.backends.mps.is_available()
            else "cuda" if torch.cuda.is_available() else "cpu")


class Midas:
    metric = False

    def __init__(self, model_type="MiDaS_small", device=None):
        self.name = {"MiDaS_small": "MiDaS small (deployed)",
                     "DPT_Hybrid": "MiDaS DPT-Hybrid"}.get(model_type, model_type)
        self.m = MidasDepth(device=device or _device(), model_type=model_type)

    def inverse_depth(self, rgb):
        return self.m.inverse_depth(rgb)


class DepthAnything:
    """Depth Anything V2 through transformers. The relative variant outputs
    disparity like MiDaS; the metric indoor variant outputs metres."""

    def __init__(self, metric=False, device=None):
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation
        hid = ("depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf" if metric
               else "depth-anything/Depth-Anything-V2-Small-hf")
        self.metric = metric
        self.name = "Depth Anything V2 small, metric indoor" if metric else "Depth Anything V2 small"
        self.device = torch.device(device or _device())
        self.proc = AutoImageProcessor.from_pretrained(hid)
        self.model = AutoModelForDepthEstimation.from_pretrained(hid).to(self.device).eval()

    @torch.no_grad()
    def inverse_depth(self, rgb):
        h, w = rgb.shape[:2]
        x = self.proc(images=rgb, return_tensors="pt")["pixel_values"].to(self.device)
        y = self.model(pixel_values=x).predicted_depth
        y = torch.nn.functional.interpolate(y.unsqueeze(1), size=(h, w),
                                            mode="bicubic", align_corners=False)
        y = y.squeeze().float().cpu().numpy()
        if self.metric:
            return 1.0 / np.maximum(y, 1e-3)
        return y


def load(key, device=None):
    return {"midas_small": lambda: Midas("MiDaS_small", device),
            "midas_hybrid": lambda: Midas("DPT_Hybrid", device),
            "da2_small": lambda: DepthAnything(False, device),
            "da2_metric": lambda: DepthAnything(True, device)}[key]()


def speed(est, rgb, n=30):
    """Milliseconds per frame, after a warm up."""
    for _ in range(3):
        est.inverse_depth(rgb)
    t0 = time.perf_counter()
    for _ in range(n):
        est.inverse_depth(rgb)
    if torch.backends.mps.is_available():
        torch.mps.synchronize()
    return 1000 * (time.perf_counter() - t0) / n
