# v3 held-out seal (written before any v3 code)

Date sealed: 2026-11-26, on branch `v3/tier1`, before any v3 modelling.

| Slice | What | Rule |
|---|---|---|
| Spatial | 4 sites in `config.HELDOUT_SITES` (Raichur, Kalaburagi solar; Bagalkot, Davanagere wind), Apr 2024 – Oct 2026 | Their truth data is not fetched until `urja.eval.v3 --final`. Scored once. |
| Temporal | All hours from 2026-11-01 at every site | Not fetched. Scored when at least 6 months exist (≈ May 2027). |
| Dev | The 4 original sites, Apr 2024 – Oct 2026, including v2's test year | v2's test year has been looked at, so for v3 it is development data. |

Anything decided after looking at a sealed slice gets a BUILD_LOG entry, and that slice is relabelled dev.

## Measured-generation check (Elia, Belgium), sealed 2026-11-26 before fetching

| Slice | What | Rule |
|---|---|---|
| Dev | 2024-04-01 – 2025-10-31 | Used to build and check the Belgian pipeline |
| Sealed test | 2025-11-01 – 2026-10-31 | Scored once, together with the spatial slice |

Series: Limburg province solar (`ods032`, region Limburg) and Belgian offshore wind (`ods031`, Federal).
Elia's solar "measured" is an upscaled estimate from sampled installations; offshore wind is metered at
the Elia connection. Elia's own `dayahead11h` forecast (issued 11:00 the day before) and its P10/P90 are the
professional baseline. Only two records (15 Jun 2025, inside dev) were seen while probing the API.
