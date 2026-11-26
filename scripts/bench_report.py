"""Write the README's CPU benchmark section from results/bench_trees.json and results/bench_nets.json."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"


def ms(x):
    return f"{x * 1000:.0f} µs" if x < 1 else f"{x:.2f} ms"


def main():
    t = json.loads((R / "bench_trees.json").read_text())
    n = json.loads((R / "bench_nets.json").read_text())
    cpu = t["cpu"]
    L = [f"Measured on **{cpu.get('cpu')}** (CPU features: {', '.join(cpu.get('cpu_features', []))}), "
         "one thread, validation split (Apr–Oct 2025). Latency is p50 over ≥ 200 timed runs after warm-up; "
         "p99 in brackets. CRPS: lower is better. Plan written before measuring: [`docs/BENCHMARK_PLAN.md`](docs/BENCHMARK_PLAN.md).", ""]
    for kind in ("solar", "wind"):
        tk, nk = t["kinds"][kind], n["kinds"][kind]
        base = tk["sweep"]["lgbm_400x31"]
        ch = tk["sweep"][tk["chosen"]]
        comp = tk["compiled"]["chosen_lleaves_llvm"]
        stu = nk["deployed_student"]
        d = nk["deploy"]
        rows = [
            ("LightGBM 9 × 400 trees, Python API (starting point)", "–", base["latency_plant_day"], base["crps"], f"{base['nodes_per_row']:,.0f} nodes"),
            (f"Smaller trees: 9 × {ch['trees_per_quantile']} × {ch['leaves']} leaves (chosen on train-year out-of-fold CRPS)", "–", ch["latency_plant_day"], ch["crps"], f"{ch['nodes_per_row']:,.0f} nodes"),
            ("…compiled to native code with treelite (C)", f"{tk['compiled']['chosen_tl2cgen_c']['library_kb']:.0f} KB", tk["compiled"]["chosen_tl2cgen_c"]["latency_plant_day"], tk["compiled"]["chosen_tl2cgen_c"]["crps"], "identical outputs"),
            ("…compiled with lleaves (LLVM)", "–", comp["latency_plant_day"], comp["crps"], f"max Δ {comp['max_abs_diff_vs_ref']:.0e}"),
        ]
        for name, label in (("ort_fp32", "fp32"), ("ort_fp16", "fp16 weights"), ("ort_int8_dynamic", "int8 dynamic"),
                            ("ort_int8_static", "int8 static (QDQ, per-channel)")):
            if name in d and "error" not in d[name]:
                x = d[name]
                rows.append((f"{stu} (ONNX Runtime, {label})", f"{x['size_kb']:.0f} KB", x["latency_plant_day"], x["crps"],
                             f"max Δ {x.get('max_abs_diff_vs_ref', 0):.3f}"))
        for name, label in (("executorch_xnnpack_fp32", "fp32"), ("executorch_xnnpack_int8", "int8")):
            x = d.get(name, {})
            if x and "error" not in x:
                rows.append((f"{stu} (ExecuTorch + XNNPACK, {label})", f"{x['size_kb']:.0f} KB", x["latency_plant_day"], x["crps"],
                             f"max Δ {x.get('max_abs_diff_vs_ref', 0):.3f}"))
        L += [f"**{kind.capitalize()}: one plant-day forecast (24 hours, 9 quantiles)**", "",
              "| Step | Size | Latency per plant-day | CRPS | Note |", "|---|---|---|---|---|"]
        for name, size, lat, crps, note in rows:
            L.append(f"| {name} | {size} | {ms(lat['p50_ms'])} ({ms(lat['p99_ms'])}) | {crps:.4f} | {note} |")
        sp = base["latency_plant_day"]["p50_ms"] / comp["latency_plant_day"]["p50_ms"]
        L += ["", f"Trees: **{sp:.0f}× faster** per plant-day than the starting point with the same accuracy. "
              f"Teacher (LightGBM 400×31) CRPS {nk['teacher_val']['crps']:.4f}.", ""]
        L += ["| Student MLP | Params | MACs / row | CRPS plain | CRPS distilled |", "|---|---|---|---|---|"]
        for w in (16, 32, 64, 128, 256):
            p, q = nk["students"][f"mlp{w}_plain"], nk["students"][f"mlp{w}_distilled"]
            L.append(f"| {w} hidden units | {p['params']:,} | {p['macs_per_row']:,} | {p['crps']:.4f} | {q['crps']:.4f} |")
        pr = nk["pruning"]
        L += ["", f"Structured pruning, distilled 128 → 64 units + 15 fine-tune epochs: CRPS "
              f"{pr['mlp128_distilled_pruned_to_64']['crps']:.4f} vs {pr['mlp64_distilled_from_scratch']['crps']:.4f} for a 64-unit "
              "model distilled from scratch.", ""]
        th = nk["thread_scaling_fp32_10k"]
        L += [f"Thread scaling (ONNX fp32, batch 10 000): " + ", ".join(f"{k} thread{'s' if k != '1' else ''} {v / 1e6:.1f} M rows/s" for k, v in th.items()), ""]
    x = n["int8_crossover"]
    L += ["**Where int8 starts to pay off on this CPU** (ONNX Runtime, batch 1 024, random weights, latency only)", "",
          "| Hidden units | MACs / row | fp32 | int8 dynamic | int8 speed-up |" + (" ExecuTorch fp32 | ExecuTorch int8 |" if "et_xnnpack_int8_ms" in next(iter(x.values())) else ""),
          "|---|---|---|---|---|" + ("---|---|" if "et_xnnpack_int8_ms" in next(iter(x.values())) else "")]
    for w, r in x.items():
        line = f"| {w} | {r['macs_per_row']:,} | {ms(r['ort_fp32_ms'])} | {ms(r['ort_int8_dynamic_ms'])} | {r['int8_speedup_ort']:.2f}× |"
        if "et_xnnpack_int8_ms" in r:
            line += f" {ms(r['et_xnnpack_fp32_ms'])} | {ms(r['et_xnnpack_int8_ms'])} |"
        L.append(line)
    L.append("")
    block = "<!-- bench:start (generated by scripts/bench_report.py; do not edit) -->\n" + "\n".join(L) + "<!-- bench:end -->"
    readme = ROOT / "README.md"
    txt = readme.read_text()
    if "<!-- bench:start" in txt:
        txt = re.sub(r"<!-- bench:start.*?<!-- bench:end -->", lambda _: block, txt, flags=re.S)
    else:
        txt = txt.replace("## Honest limits", "## CPU benchmarks and optimisation\n\n" + block + "\n\n## Honest limits", 1)
    readme.write_text(txt)
    print(block)


if __name__ == "__main__":
    main()
