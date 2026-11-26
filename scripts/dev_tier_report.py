"""Tier and Flat-Band numbers for the README, from the development years with the current pipeline.

    python scripts/dev_tier_report.py   -> results/tiers_dev.json

Both periods here (Apr-Oct 2025 and Nov 2025-Oct 2026) were looked at while building the model, so these
numbers are development numbers. The sealed tests are in results/v3_sealed.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from urja import config as C  # noqa: E402
from urja.eval import run as R  # noqa: E402

out = {"lead_mode": C.LEAD_MODE, "periods": {}}
for split, label in (("val", "Apr–Oct 2025"), ("test", "Nov 2025 – Oct 2026")):
    r = R.run(split)
    out["periods"][label] = {k: {"model": v["model"], "global_conformal": v["ablation"]["global_conformal"],
                                 "n_hours": v["n_hours"]} for k, v in r["kinds"].items()}
(C.RESULTS_DIR / "tiers_dev.json").write_text(json.dumps(out, indent=2, default=float))
print("wrote results/tiers_dev.json")
