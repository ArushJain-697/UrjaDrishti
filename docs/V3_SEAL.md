# v3 held-out seal (written before any v3 code)

Date sealed: 2026-11-26, on branch `v3/tier1`, before any v3 modelling.

| Slice | What | Rule |
|---|---|---|
| Spatial | 4 sites in `config.HELDOUT_SITES` (Raichur, Kalaburagi solar; Bagalkot, Davanagere wind), Apr 2024 – Oct 2026 | Their truth data is not fetched until `urja.eval.v3 --final`. Scored once. |
| Temporal | All hours from 2026-11-01 at every site | Not fetched. Scored when at least 6 months exist (≈ May 2027). |
| Dev | The 4 original sites, Apr 2024 – Oct 2026, including v2's test year | v2's test year has been looked at, so for v3 it is development data. |

Anything decided after looking at a sealed slice gets a BUILD_LOG entry, and that slice is relabelled dev.
