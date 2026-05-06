# Person 4 Day 5 Evaluation Report

## Model vs Baseline Comparison

| model           |   nmae_solar |   nmae_wind |   nrmse_solar |   nrmse_wind |    crps |   coverage_80 |   sharpness |
|:----------------|-------------:|------------:|--------------:|-------------:|--------:|--------------:|------------:|
| Persistence     |       0.9646 |      1.23   |        2.0644 |       1.7221 | 17.0423 |        0.4427 |      0.0625 |
| Climatological  |       1.2102 |      0.9972 |        1.9142 |       1.2825 | 11.4774 |        0.8188 |      0.403  |
| Raw NWP LR      |       0.0291 |      0.3554 |        0.0435 |       0.5677 |  3.3049 |        0.9055 |      0.1497 |
| LightGBM (ours) |       0.1624 |      0.0718 |        0.3617 |       0.1096 |  0.7648 |        0.7959 |      0.0253 |

## Calibration Chart

- Reliability diagram: `data/evaluation_plots/quantile_reliability.png`

## Interval Width Contrast

- Calm test mean interval width (MW): **2.369**
- Peak stress mean interval width (MW): **6.787**
- Widening factor (stress / calm): **2.86x**
- Contrast plot: `data/evaluation_plots/calm_vs_stress_interval_width.png`

## Season-Stratified Performance

| season       |   nmae |   nrmse |   crps |
|:-------------|-------:|--------:|-------:|
| Post-Monsoon | 0.0742 |  0.1342 | 0.8158 |
| Winter       | 0.1107 |  0.1933 | 0.7154 |

## Evaluator FAQ (One-line Answers)

- Why is monsoon accuracy lower? -> Fast cloud and wind transitions increase atmospheric uncertainty and reduce point predictability.
- How were baselines implemented? -> Persistence uses 24h lag, climatological uses train-only plant-hour-month means, raw NWP LR is per-plant linear regression on raw weather.
- What does CRPS mean? -> CRPS scores the full predictive distribution, jointly rewarding accurate medians and well-calibrated uncertainty intervals.
- Why rolling holdout instead of random split? -> Rolling temporal holdout prevents leakage from future into past and matches real forecasting deployment.

