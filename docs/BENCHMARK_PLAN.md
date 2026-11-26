# CPU benchmark and optimisation plan

Written before any measurement. Every number this produces lands in `results/bench_trees.json` / `results/bench_nets.json` and the README
table is generated from it.

## Why these tests

A forecaster that runs next to a plant (a substation box, a small single-board computer) has to be small,
fast and predictable, and every saving has to be paid for in accuracy, not hidden. So the question this answers is:
**how small and fast can the forecaster get on a CPU, and what does each step cost in accuracy?**

## Hardware

Apple M4 laptop (CPU features: FEAT_DotProd, FEAT_I8MM, FEAT_BF16, FEAT_SME, FEAT_SME2), macOS. Same code
runs on a Raspberry Pi 5 via `scripts/bench_pi.sh`.

## Accuracy (validation split, Apr–Oct 2025, filed-deadline lead; never the sealed slices)

| Metric | Why |
|---|---|
| CRPS (9 quantiles) | The model's real job is a distribution |
| nMAE of the median | Point accuracy, comparable with earlier tables |
| Max |Δ quantile| vs the fp32 model | Shows exactly what quantisation/compilation changed |

## Performance (one thread unless stated)

| Test | Detail |
|---|---|
| Latency per plant-day | batch of 24 rows: p50, p95, p99 over ≥ 500 runs after warm-up |
| Latency per row | batch 1 |
| Throughput | rows/s at batch 1, 24, 1 000, 10 000 |
| Thread scaling | 1, 2, 4 threads at batch 10 000 |
| Cold start | process-free: load model file + first inference |
| Model size | bytes on disk; parameter count |
| Compute | multiply-accumulates (MACs) per row for the MLPs; nodes evaluated per row for the trees |

Energy is not measured: macOS `powermetrics` needs root. Stated as a limit.

## Optimisations, each measured against its parent

**Trees (LightGBM, 9 quantile boosters × 400 trees)**
1. Fewer, smaller trees (trees × leaves sweep), chosen on the train-year out-of-fold loss only.
2. Compile to native code: treelite (C) and lleaves (LLVM). Predictions must match LightGBM.

**Neural net (quantile MLP)**
3. Knowledge distillation: train the MLP on the LightGBM teacher's 9 quantiles + the truth.
4. Width sweep (16 → 256 hidden units): accuracy vs MACs vs latency (Pareto front).
5. Structured pruning of hidden units, then fine-tune.
6. Post-training quantisation in ONNX Runtime: dynamic int8, static int8 (QDQ, per-channel, calibrated on
   train rows), fp16 weights.
7. ExecuTorch export with XNNPACK (fp32 and int8 via the XNNPACK quantiser): an on-device deployment stack.
8. Where int8 starts to pay off: int8 vs fp32 latency as width grows (the v2 finding was "int8 is slower at 64").

## Rules

- Accuracy and speed are always reported together; no speed number without its accuracy cost.
- Warm-up runs are discarded; timing uses `time.perf_counter_ns`; percentiles, not means alone.
- LightGBM and PyTorch never share a process (OpenMP clash on macOS, BUILD_LOG #8).
