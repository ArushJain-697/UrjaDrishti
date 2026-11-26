"""Tree-model benchmarks (this process loads LightGBM, never PyTorch).

    python -m urja.bench.trees      -> results/bench_trees.json, artifacts/bench/teacher_<kind>.npz

1. Size sweep: trees x leaves, chosen by out-of-fold CRPS on the training year (month-blocked folds).
2. Compile the chosen and the baseline model to native code with lleaves (LLVM) and check the outputs match.
3. Write out-of-fold teacher quantiles on the train rows, and teacher quantiles on val, for distillation.
"""
from __future__ import annotations

import json
import time

import lightgbm as lgb
import numpy as np

from urja import config as C
from urja.bench.common import SEED, X, accuracy, cpu_info, data, peak_rss_mb, timeit
from urja.eval import metrics as M
from urja.models.common import LEVELS, gate

OUT = C.ART_DIR / "bench"
CONFIGS = [(400, 31), (200, 31), (100, 31), (200, 15), (100, 15), (50, 15), (50, 7)]   # (trees, leaves)
BASE = (400, 31)


def params(n, leaves):
    return dict(objective="quantile", learning_rate=0.05 * 400 / n if n < 400 else 0.05, num_leaves=leaves,
                min_child_samples=40, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                n_estimators=n, verbose=-1, random_state=SEED, n_jobs=1)


def fit9(x, y, n, leaves):
    return [lgb.LGBMRegressor(alpha=a, **params(n, leaves)).fit(x, y) for a in LEVELS]


def predict9(models, x):
    return np.column_stack([m.predict(x) for m in models])


def oof(tr, cols, n, leaves, folds=4):
    fold = tr["time"].dt.month.to_numpy() % folds
    x, y = X(tr, cols), tr["y"].to_numpy()
    q = np.zeros((len(tr), len(LEVELS)))
    for k in range(folds):
        ms = fit9(x[fold != k], y[fold != k], n, leaves)
        q[fold == k] = predict9(ms, x[fold == k])
    return q


def nodes_per_row(models, x) -> float:
    """Average decision nodes evaluated per row, summed over all 9 boosters (a compute proxy)."""
    total = 0
    for m in models:
        leaf = m.booster_.predict(x[:2000], pred_leaf=True)        # (rows, trees)
        dump = m.booster_.dump_model()["tree_info"]
        depth = []
        for t, info in enumerate(dump):
            d = {}
            def walk(node, lvl):
                if "leaf_index" in node:
                    d[node["leaf_index"]] = lvl
                else:
                    walk(node["left_child"], lvl + 1); walk(node["right_child"], lvl + 1)
            walk(info["tree_structure"], 0)
            depth.append(d)
        total += np.mean([sum(depth[t][leaf[r, t]] for t in range(leaf.shape[1])) for r in range(len(leaf))])
    return float(total)


def tl2cgen_variant(models, kind, tag, xva, yva, day, ref) -> dict:
    """treelite -> C source -> clang -O2 shared library (one per quantile booster)."""
    import tl2cgen
    import treelite
    libs, size = [], 0
    t0 = time.perf_counter()
    for i, m in enumerate(models):
        lib = OUT / f"tl2c_{kind}_{tag}_{i}.dylib"
        tl2cgen.export_lib(treelite.frontend.from_lightgbm(m.booster_), toolchain="clang", libpath=str(lib),
                           params={"parallel_comp": 8})
        size += lib.stat().st_size
        libs.append(tl2cgen.Predictor(str(lib), nthread=1))
    compile_s = time.perf_counter() - t0
    pred = lambda x: np.column_stack([p.predict(tl2cgen.DMatrix(x)).ravel() for p in libs])
    return {"library_kb": size / 1024, "compile_s": compile_s, **accuracy(yva, pred(xva), day, ref=ref),
            "latency_plant_day": timeit(lambda: pred(xva[:24])), "latency_row": timeit(lambda: pred(xva[:1])),
            "rows_per_s_10k": 10_000 / (timeit(lambda: pred(np.resize(xva, (10_000, xva.shape[1]))), 30, 3)["p50_ms"] / 1e3)}


def bench_kind(kind: str) -> dict:
    tr, va, cols = data(kind)
    xtr, ytr, xva, yva = X(tr, cols), tr["y"].to_numpy(), X(va, cols), va["y"].to_numpy()
    day = va["daylight"].to_numpy() if kind == "solar" else None
    res = {"n_train": int(len(tr)), "n_val": int(len(va)), "n_features": len(cols), "sweep": {}}

    for n, leaves in CONFIGS:
        q_oof = oof(tr, cols, n, leaves)
        ms = fit9(xtr, ytr, n, leaves)
        q = predict9(ms, xva)
        name = f"lgbm_{n}x{leaves}"
        res["sweep"][name] = {"trees_per_quantile": n, "leaves": leaves,
                              "oof_crps_train": M.crps_from_quantiles(ytr, np.sort(q_oof, 1), LEVELS),
                              **accuracy(yva, q, day),
                              "nodes_per_row": nodes_per_row(ms, xva),
                              "latency_plant_day": timeit(lambda: predict9(ms, xva[:24]), 200, 20),
                              "latency_row": timeit(lambda: predict9(ms, xva[:1]), 200, 20)}
        if (n, leaves) == BASE:
            base_models, base_q, base_oof = ms, q, q_oof
    # Selection uses the training year only: smallest config within 1% of the best out-of-fold CRPS.
    best = min(v["oof_crps_train"] for v in res["sweep"].values())
    ok = [k for k, v in res["sweep"].items() if v["oof_crps_train"] <= best * 1.01]
    chosen = min(ok, key=lambda k: res["sweep"][k]["nodes_per_row"])
    res["chosen"] = chosen
    n, leaves = res["sweep"][chosen]["trees_per_quantile"], res["sweep"][chosen]["leaves"]
    chosen_models = fit9(xtr, ytr, n, leaves)

    # Native compilation with lleaves (LLVM). One compiled library per quantile booster.
    import lleaves
    OUT.mkdir(parents=True, exist_ok=True)
    res["compiled"] = {}
    for tag, models in (("baseline", base_models), ("chosen", chosen_models)):
        comp, size = [], 0
        t0 = time.perf_counter()
        for i, m in enumerate(models):
            path = OUT / f"lgbm_{kind}_{tag}_{i}.txt"
            m.booster_.save_model(str(path))
            size += path.stat().st_size
            lm = lleaves.Model(model_file=str(path))
            lm.compile()
            comp.append(lm)
        compile_s = time.perf_counter() - t0
        pred = lambda x: np.column_stack([c.predict(x, n_jobs=1) for c in comp])
        ref = predict9(models, xva)
        res["compiled"][tag + "_tl2cgen_c"] = tl2cgen_variant(models, kind, tag, xva, yva, day, ref)
        res["compiled"][tag + "_lleaves_llvm"] = {"model_text_kb": size / 1024, "compile_s": compile_s,
                                **accuracy(yva, pred(xva), day, ref=ref),
                                "latency_plant_day": timeit(lambda: pred(xva[:24])),
                                "latency_row": timeit(lambda: pred(xva[:1])),
                                "rows_per_s_10k": 10_000 / (timeit(lambda: pred(np.resize(xva, (10_000, xva.shape[1]))), 30, 3)["p50_ms"] / 1e3)}

    # Teacher for distillation: out-of-fold on train (so the student never sees in-sample fits), fitted on val.
    np.savez(OUT / f"teacher_{kind}.npz", train=np.sort(base_oof, 1), val=np.sort(base_q, 1))
    res["peak_rss_mb"] = peak_rss_mb()
    return res


def main() -> None:
    res = {"cpu": cpu_info(), "lightgbm": lgb.__version__, "threads": 1,
           "kinds": {k: bench_kind(k) for k in ("solar", "wind")}}
    out = C.RESULTS_DIR / "bench_trees.json"
    out.write_text(json.dumps(res, indent=2, default=float))
    for k, v in res["kinds"].items():
        print(k, "chosen", v["chosen"])
        for n, s in v["sweep"].items():
            print(f"  {n:12s} oofCRPS {s['oof_crps_train']:.4f} valCRPS {s['crps']:.4f} nodes/row {s['nodes_per_row']:7.0f} plant-day {s['latency_plant_day']['p50_ms']:.2f} ms")
        for t, c in v["compiled"].items():
            print(f"  {t}: CRPS {c['crps']:.4f} maxdiff {c['max_abs_diff_vs_ref']:.2e} plant-day {c['latency_plant_day']['p50_ms']:.3f} ms row {c['latency_row']['p50_ms']:.3f} ms {c['rows_per_s_10k']:.0f} rows/s")
        b = v["sweep"]["lgbm_400x31"]
        print(f"  lightgbm python baseline: plant-day {b['latency_plant_day']['p50_ms']:.3f} ms row {b['latency_row']['p50_ms']:.3f} ms")
    print("wrote", out)


if __name__ == "__main__":
    main()
