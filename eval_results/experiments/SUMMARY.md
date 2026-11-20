# Experiment summary

| Experiment | Model | Input | Perturbation | Docs all-correct | Mean field acc. | Line items | Total | Review flag | Avg cost/doc | Avg latency | Failed calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ablation-blur-no-second-read | gemini-3.5-flash-lite | hybrid | blur (no second read) | 9/10 | 96.2% | 9/10 | 9/10 | 1/1 caught, 9 false | $0.0023 | 2.7s | 0 |
| ablation-blur-same-model-second-read | gemini-3.5-flash-lite | hybrid | blur | 9/10 | 96.2% | 9/10 | 9/10 | 0/1 caught, 0 false | $0.0047 | 5.0s | 0 |
| ablation-fax-no-second-read | gemini-3.5-flash-lite | hybrid | fax (no second read) | 9/10 | 98.8% | 10/10 | 10/10 | 1/1 caught, 1 false | $0.0023 | 5.0s | 0 |
| ablation-fax-same-model-second-read | gemini-3.5-flash-lite | hybrid | fax | 9/10 | 98.8% | 10/10 | 10/10 | 0/1 caught, 0 false | $0.0029 | 5.5s | 0 |
| ablation-lowres-no-second-read | gemini-3.5-flash-lite | hybrid | lowres (no second read) | 3/10 | 87.5% | 6/10 | 9/10 | 6/7 caught, 2 false | $0.0032 | 3.3s | 0 |
| ablation-lowres-same-model-second-read | gemini-3.5-flash-lite | hybrid | lowres | 3/10 | 85.0% | 6/10 | 8/10 | 6/7 caught, 0 false | $0.0047 | 6.6s | 0 |
| ablation-photo-no-second-read | gemini-3.5-flash-lite | hybrid | photo (no second read) | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0024 | 3.5s | 0 |
| ablation-rotate90-nofix | gemini-3.5-flash-lite | hybrid | rotate90 (no orientation fix) | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 10 false | $0.0024 | 2.9s | 0 |
| main | gemini-3.5-flash-lite | hybrid | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0025 | 2.8s | 0 |
| mode-images | gemini-3.5-flash-lite | images | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0024 | 3.2s | 0 |
| mode-pdf | gemini-3.5-flash-lite | pdf | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0023 | 2.4s | 0 |
| model-3.1-flash-lite | gemini-3.1-flash-lite | hybrid | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0024 | 7.6s | 0 |
| repeat-2 | gemini-3.5-flash-lite | hybrid | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0025 | 3.2s | 0 |
| repeat-3 | gemini-3.5-flash-lite | hybrid | - | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0025 | 4.0s | 0 |
| stress-blur | gemini-3.5-flash-lite | hybrid | blur | 9/10 | 96.2% | 9/10 | 9/10 | 1/1 caught, 0 false | $0.0040 | 7.3s | 0 |
| stress-fax | gemini-3.5-flash-lite | hybrid | fax | 9/10 | 98.8% | 10/10 | 10/10 | 1/1 caught, 0 false | $0.0027 | 5.9s | 0 |
| stress-lowres | gemini-3.5-flash-lite | hybrid | lowres | 3/10 | 85.0% | 6/10 | 8/10 | 6/7 caught, 0 false | $0.0043 | 6.5s | 0 |
| stress-photo | gemini-3.5-flash-lite | hybrid | photo | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0024 | 3.5s | 0 |
| stress-rotate180 | gemini-3.5-flash-lite | hybrid | rotate180 | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0025 | 3.6s | 0 |
| stress-rotate270 | gemini-3.5-flash-lite | hybrid | rotate270 | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0031 | 7.5s | 0 |
| stress-rotate90 | gemini-3.5-flash-lite | hybrid | rotate90 | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0031 | 6.7s | 0 |
| stress-skew7 | gemini-3.5-flash-lite | hybrid | skew7 | 10/10 | 100.0% | 10/10 | 10/10 | 0/0 caught, 0 false | $0.0024 | 3.0s | 0 |
