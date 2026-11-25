"""Edge benchmark: can tomorrow's forecast for a plant be produced on a small Arm board?

    python -m urja.edge.bench          # writes results/edge_<machine>.json

Measures, on the CPU it runs on:
  * accuracy (val split) of LightGBM vs the quantile MLP in fp32 ONNX vs int8 ONNX
  * file size, and latency for one plant-day (24 rows) and a 10k-row batch
  * the Arm CPU features the int8 kernels can use (dot-product / i8mm)
Run the same command on a Raspberry Pi 5 (scripts/bench_pi.sh) to get Cortex-A76 numbers.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import time

import sys

import numpy as np

from urja import config as C
from urja.eval import metrics as M
from urja.features.build import build_table, feature_columns
from urja.models.common import LEVELS, gate


def cpu_info() -> dict:
    info = {"machine": platform.machine(), "system": platform.system(), "processor": platform.processor()}
    if platform.system() == "Darwin":
        def sysctl(k):
            try:
                return subprocess.check_output(["sysctl", "-n", k], text=True).strip()
            except Exception:
                return None
        info["cpu"] = sysctl("machdep.cpu.brand_string")
        info["arm_features"] = {f: sysctl(f"hw.optional.arm.{f}") == "1" for f in ("FEAT_DotProd", "FEAT_I8MM", "FEAT_BF16")}
    elif os.path.exists("/proc/cpuinfo"):
        txt = open("/proc/cpuinfo").read()
        flags = next((l.split(":", 1)[1].split() for l in txt.splitlines() if l.startswith("Features")), [])
        model = next((l.split(":", 1)[1].strip() for l in txt.splitlines() if l.startswith("Model")), None)
        info["cpu"] = model
        info["arm_features"] = {f: f in flags for f in ("asimddp", "i8mm", "bf16", "sve")}
    info["threads"] = os.cpu_count()
    return info


def _lat(fn, n=200) -> float:
    fn()
    t = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t) / n * 1e3


def _val(df, kind):
    d = df[(df["kind"] == kind) & (df["split"] == "val")]
    return d[d["daylight"]] if kind == "solar" else d


def bench_lightgbm(kind: str, df, cols) -> dict:
    from urja.models.quantile import QuantileForecaster   # LightGBM only ever loads in this process
    d = _val(df, kind)
    y = d["y"].to_numpy()
    gbm = QuantileForecaster(kind, cols).fit(df)
    q = gbm.raw(d)
    day = d.iloc[:24]
    return {"crps": M.crps_from_quantiles(y, q, LEVELS), "nmae": M.nmae(y, q[:, 4]),
            "ms_per_plant_day": _lat(lambda: gbm.raw(day), 50)}


def bench_mlp(kind: str, df, cols) -> dict:
    """Runs in a child process that never imports LightGBM (OpenMP clash on macOS)."""
    import onnxruntime as ort
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic

    from urja.models import mlp

    d = _val(df, kind)
    y = d["y"].to_numpy()
    net = mlp.train(df, kind, cols)
    C.ART_DIR.mkdir(parents=True, exist_ok=True)
    fp32 = C.ART_DIR / f"mlp_{kind}_fp32.onnx"
    int8 = C.ART_DIR / f"mlp_{kind}_int8.onnx"
    torch.onnx.export(net, torch.zeros(1, len(cols)), fp32, input_names=["x"], output_names=["q"],
                      dynamic_axes={"x": {0: "n"}, "q": {0: "n"}}, opset_version=17, dynamo=False)
    quantize_dynamic(str(fp32), str(int8), weight_type=QuantType.QInt8)
    X = d[cols].to_numpy(np.float32)
    X = np.where(np.isnan(X), 0, X).astype(np.float32)
    Xday, Xbig = X[:24], np.resize(X, (10_000, X.shape[1]))
    daylight = d["daylight"].to_numpy() if kind == "solar" else None
    out = {"onnxruntime": ort.__version__}
    for name, path in (("mlp_fp32", fp32), ("mlp_int8", int8)):
        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        s = ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])
        qq = gate(s.run(None, {"x": X})[0], daylight)
        out[name] = {"crps": M.crps_from_quantiles(y, qq, LEVELS), "nmae": M.nmae(y, qq[:, 4]),
                     "size_kb": path.stat().st_size / 1024,
                     "ms_per_plant_day": _lat(lambda: s.run(None, {"x": Xday})),
                     "ms_per_10k_rows": _lat(lambda: s.run(None, {"x": Xbig}), 20)}
    out["int8_crps_change"] = out["mlp_int8"]["crps"] / out["mlp_fp32"]["crps"] - 1
    return out


def main() -> None:
    df = build_table()
    cols = feature_columns(df)
    if len(sys.argv) > 2 and sys.argv[1] == "--mlp-child":
        print(json.dumps(bench_mlp(sys.argv[2], df, cols), default=float))
        return
    res = {"cpu": cpu_info(), "threads_used": 1, "kinds": {}}
    for k in ("solar", "wind"):
        child = subprocess.run([sys.executable, "-m", "urja.edge.bench", "--mlp-child", k],
                               capture_output=True, text=True, check=True)
        res["kinds"][k] = {"lightgbm": bench_lightgbm(k, df, cols), **json.loads(child.stdout.strip().splitlines()[-1])}
    tag = (res["cpu"].get("cpu") or res["cpu"]["machine"]).lower().replace(" ", "_").replace("(", "").replace(")", "")
    out = C.RESULTS_DIR / f"edge_{tag}.json"
    out.write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps(res, indent=1, default=lambda x: round(float(x), 4)))
    print("wrote", out)


if __name__ == "__main__":
    main()
