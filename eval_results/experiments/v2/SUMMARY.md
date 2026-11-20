# Experiment summary

| Experiment | Model | Input | Perturbation | Docs all-correct | Mean field acc. | Line items | Total | Review flag | Avg cost/doc | Avg latency | Failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| main | gemini-3.5-flash-lite | hybrid | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0024 | 4.4s | 0 |
| mode-images | gemini-3.5-flash-lite | images | - | 9/10 | 90.0% | 9/10 | 9/10 | 1/1 caught, 0 false | $0.0023 | 3.2s | 1 |
| mode-pdf | gemini-3.5-flash-lite | pdf | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0023 | 4.9s | 0 |
| model-3.1-flash-lite | gemini-3.1-flash-lite | hybrid | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0022 | 5.1s | 0 |
| model-3.6-flash | gemini-3.6-flash | hybrid | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0037 | 19.1s | 0 |
| repeat-2 | gemini-3.5-flash-lite | hybrid | - | 8/10 | 80.0% | 8/10 | 8/10 | 2/2 caught, 0 false | $0.0021 | 6.2s | 2 |
| repeat-3 | gemini-3.5-flash-lite | hybrid | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0024 | 3.9s | 0 |
| stress-blur | gemini-3.5-flash-lite | hybrid | blur | 9/10 | 96.2% | 9/10 | 9/10 | 1/1 caught, 9 false | $0.0023 | 4.7s | 0 |
| stress-lowres | gemini-3.5-flash-lite | hybrid | lowres | 4/10 | 71.2% | 6/10 | 7/10 | 5/6 caught, 1 false | $0.0030 | 7.3s | 2 |
| stress-rotate180 | gemini-3.5-flash-lite | hybrid | rotate180 | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0023 | 5.2s | 0 |
| stress-rotate270 | gemini-3.5-flash-lite | hybrid | rotate270 | 6/10 | 60.0% | 6/10 | 6/10 | 4/4 caught, 1 false | $0.0028 | 13.0s | 4 |
| stress-rotate90-nofix | gemini-3.5-flash-lite | hybrid | rotate90 (no fix) | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 10 false | $0.0023 | 3.9s | 0 |
| stress-rotate90 | gemini-3.5-flash-lite | hybrid | rotate90 | 8/10 | 80.0% | 8/10 | 8/10 | 2/2 caught, 3 false | $0.0024 | 13.2s | 2 |
| stress-skew7 | gemini-3.5-flash-lite | hybrid | skew7 | 9/10 | 98.8% | 9/10 | 10/10 | 0/1 caught, 0 false | $0.0023 | 6.2s | 0 |
