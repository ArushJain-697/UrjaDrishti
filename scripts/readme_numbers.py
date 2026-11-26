"""Regenerate the numbers block in README.md from results/*.json. Never type a number by hand."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
pct = lambda v, d=1: f"{v * 100:.{d}f}%"


def split_table(m: dict, title: str) -> list[str]:
    out = [f"**{title}** ({m['period'][0]} to {m['period'][1]}, n = "
           + ", ".join(f"{k['n_hours']:,} {kind} hours" for kind, k in m["kinds"].items()) + ")", "",
           "| | Model nMAE | Best baseline (nMAE) | NWP ensemble nMAE | CRPS model / NWP ens. | P10-P90 coverage (target 80%) | Energy outside ±10% band vs best baseline |",
           "|---|---|---|---|---|---|---|"]
    for kind, k in m["kinds"].items():
        bb = k["baselines"][k["best_baseline"]]
        out.append(f"| {kind} | **{pct(k['model']['nmae'], 2)}** | {k['best_baseline']} ({pct(bb['nmae'], 2)}) | "
                   f"{pct(k['baselines']['nwp_ensemble']['nmae'], 2)} | {k['model']['crps']:.4f} / {k['baselines']['nwp_ensemble']['crps']:.4f} | "
                   f"{pct(k['model']['coverage_80'])} | **−{pct(k['vs_best_baseline']['dsm_excess_reduction'], 0)}** |")
    out += ["", "| Tier (per-tier calibration) | " + " | ".join(f"{kind}: share of hours · coverage · share of out-of-band energy" for kind in m["kinds"]) + " |",
            "|---|" + "---|" * len(m["kinds"])]
    for t in ("GREEN", "AMBER", "RED"):
        cells = []
        for kind, k in m["kinds"].items():
            x = k["model"]["tiers"].get(t)
            cells.append(f"{pct(x['share_hours'], 0)} · {pct(x['coverage_80'])} · {pct(x['share_dsm_excess'], 0)}" if x else "–")
        out.append(f"| {t} | " + " | ".join(cells) + " |")
    out += ["", "| Ablation (coverage in RED hours / nMAE) | " + " | ".join(m["kinds"]) + " |", "|---|" + "---|" * len(m["kinds"])]
    names = {"model": "full model, per-tier calibration", "global_conformal": "one calibration for all hours (the trap)",
             "no_disagreement": "without NWP-disagreement features", "single_nwp_icon": "ICON only (1 weather model, not 3)",
             "no_physics_prior": "without the physics prior"}
    for key, label in names.items():
        cells = []
        for kind, k in m["kinds"].items():
            r = k["model"] if key == "model" else k["ablation"][key]
            cells.append(f"{pct(r['tiers']['RED']['coverage_80'])} / {pct(r['nmae'], 2)}")
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    return out + [""]


def edge_table() -> list[str]:
    out = []
    for f in sorted(R.glob("edge_*.json")):
        e = json.loads(f.read_text())
        feats = ", ".join(k for k, v in e["cpu"].get("cpu_features", {}).items() if v)
        out += [f"**Edge benchmark: {e['cpu'].get('cpu') or e['cpu']['machine']}** (CPU features: {feats or 'n/a'}; 1 thread)", "",
                "| | Model | Size | Latency per plant-day (24 h) | 10k rows | CRPS (val) |", "|---|---|---|---|---|---|"]
        for kind, k in e["kinds"].items():
            out.append(f"| {kind} | LightGBM, 9 quantiles (Python API) | – | {k['lightgbm']['ms_per_plant_day']:.2f} ms | – | {k['lightgbm']['crps']:.4f} |")
            for n in ("mlp_fp32", "mlp_int8"):
                x = k[n]
                out.append(f"| {kind} | quantile MLP, ONNX {n[4:]} | {x['size_kb']:.0f} KB | {x['ms_per_plant_day'] * 1000:.0f} µs | {x['ms_per_10k_rows']:.2f} ms | {x['crps']:.4f} |")
        out.append("")
    return out


NAMES = {"RCR_S1": "Raichur solar", "KLB_S1": "Kalaburagi solar", "BGK_W1": "Bagalkot wind",
         "DVG_W1": "Davanagere wind", "BE_LIM_S": "Limburg solar (measured)", "BE_OFF_W": "Belgian offshore wind (measured)"}


def v3_block() -> list[str]:
    sealed, dev = json.loads((R / "v3_sealed.json").read_text()), json.loads((R / "v3_dev.json").read_text())
    out = ["**v3 sealed slices, scored once** (forecasts as available at the real filing deadline, 24–48 h lead)", "",
           "*Unseen sites: 4 Karnataka locations no model or design choice had seen, Apr 2025 – Oct 2026.*", "",
           "| Site | Model nMAE | Best baseline (nMAE) | vs best | P10–P90 coverage | RED-hour coverage | RED share of hours |",
           "|---|---|---|---|---|---|---|"]
    for sid, v in sealed["spatial"].items():
        base = {k: v[k]["nmae"] for k in ("nwp_ensemble", "linear_mos", "nwp_ecmwf", "nwp_gfs", "nwp_icon")}
        bn = min(base, key=base.get)
        m = v["model"]
        out.append(f"| {NAMES[sid]} | **{pct(m['nmae'], 2)}** | {bn} ({pct(base[bn], 2)}) | **−{pct(1 - m['nmae'] / base[bn])}** | "
                   f"{pct(m['coverage_80'])} | {pct(m['red_coverage'])} | {pct(m['red_share_hours'], 0)} |")
    out += ["", "*Measured output (Elia, Belgium), Nov 2025 – Oct 2026, against Elia's own day-ahead forecast issued 11:00 the day before.*", "",
            "| Series | Model nMAE | Elia nMAE | Linear MOS nMAE | Quantile score model / Elia | Coverage model / Elia (target 80%) |",
            "|---|---|---|---|---|---|"]
    for sid, v in sealed["elia_test"].items():
        m, e = v["model"], v["elia_dayahead"]
        out.append(f"| {NAMES[sid]} | {pct(m['nmae'], 2)} | **{pct(e['nmae'], 2)}** | {pct(v['linear_mos']['nmae'], 2)} | "
                   f"{m['qs3']:.4f} / {e['qs3']:.4f} | {pct(m['coverage_80'])} / {pct(e['coverage_80'])} |")
    out += ["", "**v3 dev checks** (development data; looked at while building v3)", "",
            "| Check | Solar | Wind |", "|---|---|---|"]
    ld = dev["lead"]
    cells = [f"{pct(ld['day1']['test'][k]['nmae'], 2)} → {pct(ld['filed']['test'][k]['nmae'], 2)}" for k in ("solar", "wind")]
    out.append(f"| Real filing deadline vs v2's ~24 h lead (nMAE, Nov 2025 – Oct 2026) | {cells[0]} | {cells[1]} |")
    for sid, v in dev["second_truth"].items():
        out.append(f"| {sid}: model vs NWP ensemble, scored on ERA5 / on NASA POWER satellite | "
                   f"{pct(v['era5']['model_p50'], 2)} vs {pct(v['era5']['nwp_ensemble'], 2)} / {pct(v['nasa']['model_p50'], 2)} vs {pct(v['nasa']['nwp_ensemble'], 2)} | – |")
    st = list(dev["second_truth"].values())
    out.append(f"| How far the two truths disagree with each other (nMAE) | {pct(min(x['truths_agree_nmae'] for x in st), 1)}–{pct(max(x['truths_agree_nmae'] for x in st), 1)} | – |")
    return out + [""]


def main():
    lines = v3_block() if (R / "v3_sealed.json").exists() else []
    lines += ["<details><summary>v2 results (superseded: ~24 h lead and a 30-minute timestamp shift, see BUILD_LOG #12–13)</summary>", ""]
    if (R / "metrics_test.json").exists():
        lines += split_table(json.loads((R / "metrics_test.json").read_text()), "Sealed test year, scored once")
    lines += split_table(json.loads((R / "metrics_val.json").read_text()), "Validation (design choices were made looking at this)")
    lines += edge_table()
    lines += ["</details>", ""]
    block = "<!-- numbers:start (generated by scripts/readme_numbers.py; do not edit) -->\n" + "\n".join(lines) + "<!-- numbers:end -->"
    readme = ROOT / "README.md"
    txt = readme.read_text()
    txt = re.sub(r"<!-- numbers:start.*?<!-- numbers:end -->", lambda _: block, txt, flags=re.S)
    readme.write_text(txt)
    print(block)


if __name__ == "__main__":
    main()
