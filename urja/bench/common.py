"""Shared benchmark helpers. Imports neither LightGBM nor PyTorch (they clash on macOS, BUILD_LOG #8)."""
from __future__ import annotations

import os
import platform
import resource
import subprocess
import time

import numpy as np
import pandas as pd

from urja.eval import metrics as M
from urja.features.build import build_table, feature_columns
from urja.models.common import LEVELS, gate

SEED = 42


def cpu_info() -> dict:
    info = {"machine": platform.machine(), "system": platform.system(), "python": platform.python_version()}
    if platform.system() == "Darwin":
        sc = lambda k: subprocess.run(["sysctl", "-n", k], capture_output=True, text=True).stdout.strip()
        info["cpu"] = sc("machdep.cpu.brand_string")
        info["cpu_features"] = [f for f in ("FEAT_DotProd", "FEAT_I8MM", "FEAT_BF16", "FEAT_SME", "FEAT_SME2")
                                if sc(f"hw.optional.arm.{f}") == "1"]
        info["perf_cores"] = sc("hw.perflevel0.physicalcpu")
    elif os.path.exists("/proc/cpuinfo"):
        txt = open("/proc/cpuinfo").read()
        flags = next((l.split(":", 1)[1].split() for l in txt.splitlines() if l.startswith("Features")), [])
        info["cpu"] = next((l.split(":", 1)[1].strip() for l in txt.splitlines() if l.startswith("Model")), None)
        info["cpu_features"] = [f for f in ("asimddp", "i8mm", "bf16", "sve", "sme") if f in flags]
    return info


def timeit(fn, runs: int = 500, warm: int = 50) -> dict:
    for _ in range(warm):
        fn()
    t = np.empty(runs)
    for i in range(runs):
        a = time.perf_counter_ns()
        fn()
        t[i] = time.perf_counter_ns() - a
    t /= 1e6
    return {"p50_ms": float(np.percentile(t, 50)), "p95_ms": float(np.percentile(t, 95)),
            "p99_ms": float(np.percentile(t, 99)), "mean_ms": float(t.mean())}


def peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024) if platform.system() == "Darwin" else r / 1024


def data(kind: str):
    """Train and validation rows for one technology (filed-deadline lead). Never the sealed slices."""
    df = build_table()
    cols = feature_columns(df)
    d = df[df["kind"] == kind]
    d = d[d["daylight"]] if kind == "solar" else d
    tr, va = d[d["split"] == "train"], d[d["split"] == "val"]
    return tr, va, cols


def X(d: pd.DataFrame, cols) -> np.ndarray:
    x = d[cols].to_numpy(np.float32)
    return np.where(np.isnan(x), 0.0, x).astype(np.float32)


def accuracy(y, q, daylight=None, ref=None) -> dict:
    q = gate(np.asarray(q, float), daylight)
    out = {"crps": M.crps_from_quantiles(y, q, LEVELS), "nmae": M.nmae(y, q[:, 4])}
    if ref is not None:
        out["max_abs_diff_vs_ref"] = float(np.max(np.abs(q - gate(np.asarray(ref, float), daylight))))
    return out
