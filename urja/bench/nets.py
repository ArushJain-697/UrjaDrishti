"""Neural-net benchmarks (this process loads PyTorch, never LightGBM).

    python -m urja.bench.nets      -> results/bench_nets.json   (needs artifacts/bench/teacher_*.npz)

Students: quantile MLPs, trained plain or distilled from the LightGBM teacher's out-of-fold quantiles.
Deployment variants: ONNX Runtime fp32 / fp16 / dynamic int8 / static int8 (QDQ, per-channel),
ExecuTorch + XNNPACK fp32 / int8. Plus an int8-vs-fp32 latency crossover sweep over network width.
"""
from __future__ import annotations

import copy
import json
import time
import warnings

import numpy as np
import onnxruntime as ort
import torch
from torch import nn

from urja import config as C
from urja.bench.common import SEED, X, accuracy, cpu_info, data, peak_rss_mb, timeit
from urja.models.common import LEVELS
from urja.models.mlp import QuantileMLP

warnings.filterwarnings("ignore")
OUT = C.ART_DIR / "bench"
WIDTHS = (16, 32, 64, 128, 256)
LV = torch.tensor(LEVELS, dtype=torch.float32)[None, :]


def pinball(q, y):
    d = y - q
    return torch.maximum(LV * d, (LV - 1) * d).mean()


def train(x, y, width, teacher=None, lam=1.0, epochs=60, model=None, lr=2e-3):
    torch.manual_seed(SEED)
    m = model or QuantileMLP(x.shape[1], hidden=width)
    if model is None:
        m.mu.data = torch.tensor(x.mean(0))
        m.sd.data = torch.tensor(np.maximum(x.std(0), 1e-2))
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=lr, weight_decay=1e-4)
    xt, yt = torch.tensor(x), torch.tensor(y, dtype=torch.float32)[:, None]
    tt = torch.tensor(teacher, dtype=torch.float32) if teacher is not None else None
    for _ in range(epochs):
        perm = torch.randperm(len(xt))
        for i in range(0, len(xt), 256):
            b = perm[i:i + 256]
            q = m(xt[b])
            loss = pinball(q, yt[b])
            if tt is not None:
                loss = loss + lam * (q - tt[b]).abs().mean()     # match the teacher's quantiles
            opt.zero_grad(); loss.backward(); opt.step()
    return m.eval()


def params_and_macs(m: QuantileMLP) -> tuple[int, int]:
    lin = [l for l in m.net if isinstance(l, nn.Linear)]
    return sum(l.weight.numel() + l.bias.numel() for l in lin), sum(l.in_features * l.out_features for l in lin)


def prune(m: QuantileMLP, keep: float) -> QuantileMLP:
    """Structured pruning: keep the hidden units with the largest L1 norm of outgoing weights."""
    l1, _, l2, _, l3 = m.net
    k = max(1, int(round(l1.out_features * keep)))
    keep1 = torch.argsort(l2.weight.abs().sum(0), descending=True)[:k]
    keep2 = torch.argsort(l3.weight.abs().sum(0), descending=True)[:k]
    p = QuantileMLP(l1.in_features, hidden=k)
    p.mu.data, p.sd.data = m.mu.data.clone(), m.sd.data.clone()
    a, _, b, _, c = p.net
    with torch.no_grad():
        a.weight.copy_(l1.weight[keep1]); a.bias.copy_(l1.bias[keep1])
        b.weight.copy_(l2.weight[keep2][:, keep1]); b.bias.copy_(l2.bias[keep2])
        c.weight.copy_(l3.weight[:, keep2]); c.bias.copy_(l3.bias)
    return p


def torch_pred(m, x):
    with torch.no_grad():
        return m(torch.tensor(x)).numpy()


# ------------------------------------------------------------------ ONNX Runtime variants
def onnx_export(m, n_in, path):
    torch.onnx.export(m, torch.zeros(1, n_in), path, input_names=["x"], output_names=["q"],
                      dynamic_axes={"x": {0: "n"}, "q": {0: "n"}}, opset_version=17, dynamo=False)


def ort_session(path, threads=1):
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])


def ort_variants(m, x_cal, n_in, tag) -> dict:
    from onnxruntime.quantization import (CalibrationDataReader, QuantFormat, QuantType, quantize_dynamic,
                                          quantize_static)
    OUT.mkdir(parents=True, exist_ok=True)
    fp32 = OUT / f"{tag}_fp32.onnx"
    onnx_export(m, n_in, fp32)
    paths = {"ort_fp32": fp32}
    dyn = OUT / f"{tag}_int8_dynamic.onnx"
    quantize_dynamic(str(fp32), str(dyn), weight_type=QuantType.QInt8, per_channel=True)
    paths["ort_int8_dynamic"] = dyn

    class Reader(CalibrationDataReader):
        def __init__(self):
            self.it = iter([{"x": x_cal[i:i + 64]} for i in range(0, len(x_cal), 64)])
        def get_next(self):
            return next(self.it, None)

    st = OUT / f"{tag}_int8_static.onnx"
    quantize_static(str(fp32), str(st), Reader(), quant_format=QuantFormat.QDQ, per_channel=True,
                    activation_type=QuantType.QInt8, weight_type=QuantType.QInt8)
    paths["ort_int8_static"] = st
    try:
        import onnx
        from onnxconverter_common import float16
        h = OUT / f"{tag}_fp16.onnx"
        onnx.save(float16.convert_float_to_float16(onnx.load(str(fp32)), keep_io_types=True), str(h))
        paths["ort_fp16"] = h
    except Exception as e:  # converter not installed
        print("fp16 skipped:", e)
    return paths


# ------------------------------------------------------------------ ExecuTorch + XNNPACK
def et_export(m, n_in, path, x_cal=None, batch=24):
    from executorch.backends.xnnpack.partition.xnnpack_partitioner import XnnpackPartitioner
    from executorch.exir import to_edge_transform_and_lower
    ex = (torch.zeros(batch, n_in),)
    model = m
    if x_cal is not None:
        from executorch.backends.xnnpack.quantizer.xnnpack_quantizer import (XNNPACKQuantizer,
                                                                              get_symmetric_quantization_config)
        from torchao.quantization.pt2e.quantize_pt2e import convert_pt2e, prepare_pt2e
        q = XNNPACKQuantizer()
        q.set_global(get_symmetric_quantization_config(is_per_channel=True))
        g = prepare_pt2e(torch.export.export(copy.deepcopy(m), ex).module(), q)
        with torch.no_grad():
            for i in range(0, len(x_cal) - batch + 1, batch):
                g(torch.tensor(x_cal[i:i + batch]))
        model = convert_pt2e(g)
    prog = to_edge_transform_and_lower(torch.export.export(model, ex), partitioner=[XnnpackPartitioner()]).to_executorch()
    path.write_bytes(prog.buffer)
    return path


def et_runner(path, batch=24):
    from executorch.runtime import Runtime
    method = Runtime.get().load_program(str(path)).load_method("forward")

    def run(x):
        out = []
        for i in range(0, len(x), batch):
            chunk = x[i:i + batch]
            pad = batch - len(chunk)
            if pad:
                chunk = np.vstack([chunk, np.zeros((pad, x.shape[1]), np.float32)])
            out.append(method.execute([torch.tensor(chunk)])[0].numpy()[:batch - pad if pad else batch])
        return np.vstack(out)
    return run


# ------------------------------------------------------------------ per technology
def bench_kind(kind: str) -> dict:
    tr, va, cols = data(kind)
    xtr, ytr, xva, yva = X(tr, cols), tr["y"].to_numpy(np.float32), X(va, cols), va["y"].to_numpy()
    day = va["daylight"].to_numpy() if kind == "solar" else None
    t = np.load(OUT / f"teacher_{kind}.npz")
    n_in = len(cols)
    res = {"teacher_val": accuracy(yva, t["val"], day), "students": {}, "pruning": {}, "deploy": {}}

    models = {}
    for w in WIDTHS:
        for distil in (False, True):
            m = train(xtr, ytr, w, t["train"] if distil else None)
            p, macs = params_and_macs(m)
            name = f"mlp{w}_{'distilled' if distil else 'plain'}"
            models[name] = m
            res["students"][name] = {"width": w, "distilled": distil, "params": p, "macs_per_row": macs,
                                     **accuracy(yva, torch_pred(m, xva), day)}
    # Structured pruning: distilled 128 -> 64 units (+ 15 fine-tune epochs) vs a 64 trained from scratch.
    p64 = train(xtr, ytr, 64, t["train"], model=prune(models["mlp128_distilled"], 0.5), epochs=15, lr=1e-3)
    res["pruning"]["mlp128_distilled_pruned_to_64"] = {"params": params_and_macs(p64)[0], **accuracy(yva, torch_pred(p64, xva), day)}
    res["pruning"]["mlp64_distilled_from_scratch"] = {k: res["students"]["mlp64_distilled"][k] for k in ("params", "crps", "nmae")}

    # Deployment: best student (plain or distilled) by val CRPS among widths <= 128, all runtimes.
    # Chosen on the validation split, so its accuracy here is optimistic by a little (stated in README).
    cands = {k: v for k, v in res["students"].items() if v["width"] <= 128}
    best = min(cands, key=lambda k: cands[k]["crps"])
    res["deployed_student"] = best
    m = models[best]
    ref = torch_pred(m, xva)
    paths = ort_variants(m, xtr[np.random.default_rng(0).choice(len(xtr), 1024, replace=False)], n_in, f"{kind}_{best}")
    big = np.resize(xva, (10_000, n_in)).astype(np.float32)
    for name, path in paths.items():
        s = ort_session(path)
        t0 = time.perf_counter(); s2 = ort_session(path); s2.run(None, {"x": xva[:24]}); cold = (time.perf_counter() - t0) * 1e3
        r = {"size_kb": path.stat().st_size / 1024, "cold_start_ms": cold,
             **accuracy(yva, s.run(None, {"x": xva})[0], day, ref=ref),
             "latency_plant_day": timeit(lambda: s.run(None, {"x": xva[:24]})),
             "latency_row": timeit(lambda: s.run(None, {"x": xva[:1]})),
             "rows_per_s": {}}
        for b in (1, 24, 1000, 10_000):
            xb = big[:b]
            r["rows_per_s"][str(b)] = b / (timeit(lambda: s.run(None, {"x": xb}), 100 if b < 1000 else 20, 5)["p50_ms"] / 1e3)
        res["deploy"][name] = r
    # Thread scaling on the fp32 model at a 10k batch.
    res["thread_scaling_fp32_10k"] = {}
    for th in (1, 2, 4):
        s = ort_session(paths["ort_fp32"], th)
        res["thread_scaling_fp32_10k"][str(th)] = 10_000 / (timeit(lambda: s.run(None, {"x": big}), 20, 3)["p50_ms"] / 1e3)
    # ExecuTorch + XNNPACK (fixed batch of 24 = one plant-day).
    for name, cal in (("executorch_xnnpack_fp32", None), ("executorch_xnnpack_int8", xtr[:2400])):
        try:
            path = et_export(m, n_in, OUT / f"{kind}_{best}_{name}.pte", cal)
            run = et_runner(path)
            t0 = time.perf_counter(); run2 = et_runner(path); run2(xva[:24]); cold = (time.perf_counter() - t0) * 1e3
            res["deploy"][name] = {"size_kb": path.stat().st_size / 1024, "cold_start_ms": cold,
                                   **accuracy(yva, run(xva), day, ref=ref),
                                   "latency_plant_day": timeit(lambda: run(xva[:24]))}
        except Exception as e:
            res["deploy"][name] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
    return res


def crossover() -> dict:
    """int8 vs fp32 latency as the network grows (random weights; latency only). Batch 1024, 1 thread."""
    from onnxruntime.quantization import QuantType, quantize_dynamic
    out = {}
    x = np.random.default_rng(0).normal(size=(1024, 34)).astype(np.float32)
    for w in (64, 256, 1024, 2048):
        m = QuantileMLP(34, hidden=w).eval()
        fp32 = OUT / f"xover_{w}_fp32.onnx"
        onnx_export(m, 34, fp32)
        dyn = OUT / f"xover_{w}_int8.onnx"
        quantize_dynamic(str(fp32), str(dyn), weight_type=QuantType.QInt8, per_channel=True)
        r = {"macs_per_row": params_and_macs(m)[1]}
        for tag, p in (("ort_fp32", fp32), ("ort_int8_dynamic", dyn)):
            s = ort_session(p)
            r[tag + "_ms"] = timeit(lambda: s.run(None, {"x": x}), 50, 5)["p50_ms"]
        try:
            for tag, cal in (("et_xnnpack_fp32", None), ("et_xnnpack_int8", x)):
                run = et_runner(et_export(m, 34, OUT / f"xover_{w}_{tag}.pte", cal, batch=1024), batch=1024)
                r[tag + "_ms"] = timeit(lambda: run(x), 50, 5)["p50_ms"]
        except Exception as e:
            r["executorch_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        r["int8_speedup_ort"] = r["ort_fp32_ms"] / r["ort_int8_dynamic_ms"]
        if "et_xnnpack_int8_ms" in r:
            r["int8_speedup_executorch"] = r["et_xnnpack_fp32_ms"] / r["et_xnnpack_int8_ms"]
        out[str(w)] = r
    return out


def main() -> None:
    torch.set_num_threads(1)
    res = {"cpu": cpu_info(), "torch": torch.__version__, "onnxruntime": ort.__version__, "threads": 1,
           "kinds": {k: bench_kind(k) for k in ("solar", "wind")}, "int8_crossover": crossover()}
    res["peak_rss_mb"] = peak_rss_mb()
    out = C.RESULTS_DIR / "bench_nets.json"
    out.write_text(json.dumps(res, indent=2, default=float))
    print(json.dumps(res, indent=1, default=lambda v: round(float(v), 4))[:9000])
    print("wrote", out)


if __name__ == "__main__":
    main()
