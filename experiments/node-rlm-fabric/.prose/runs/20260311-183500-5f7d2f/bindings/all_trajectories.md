# all_trajectories

kind: let

source:
```prose
let all_trajectories = session: navigator_analyst
  prompt: "Load all trajectory JSON files..."
```

---

## Overview

All trajectory and fabric-result JSON files from `experiments/node-rlm-fabric/results/`.
13 trajectory files + 13 fabric aggregate files across three conditions.
Model: `claude-sonnet-4-6` throughout.
Endpoint: `https://bootstrap.cogitarelink.ai`

### File Inventory

| Condition | Runs | Task Set(s) |
|-----------|------|-------------|
| js-baseline | 5 | phase1 SIO/obs tasks (×3), vocab tasks (×2) |
| js-jsonld | 4 | vocab tasks (×2), phase1 SIO/obs tasks (×2) |
| js-combined | 4 | vocab tasks (×2), phase1 SIO/obs tasks (×2) |

---

## Condition Summary Statistics

| Condition | Runs | Tasks | Mean Score | Mean Iter | Mean comunica/task | Mean fetchJsonLd/task | Mean jsonld.*/task | Mean Tokens/task | Mean Wall/task |
|-----------|------|-------|-----------|-----------|--------------------|-----------------------|-------------------|-----------------|----------------|
| js-baseline | 5 | 26 | 0.885 | 6.5 | 4.15 | 0.00 | 0.00 | 35,542 | 22.6s |
| js-jsonld | 4 | 20 | 0.900 | 6.7 | 2.90 | 1.10 | 0.40 | 42,396 | 28.0s |
| js-combined | 4 | 20 | 0.850 | 6.7 | 3.30 | 0.60 | 0.35 | 42,869 | 26.3s |

Key observations:
- js-jsonld achieves the highest mean score (0.900) with the lowest comunica call rate (2.90/task)
- fetchJsonLd is used exclusively for schema tasks, never for data (obs-*) tasks
- jsonld.* methods (expand, frame) appear only in runs with schema/vocab tasks
- Token cost is 19-20% higher in jsonld and combined vs baseline

---

## Per-Task Score Breakdown (Mean Across Runs)

Scores are mean across all runs of that condition. `n` = number of task runs.

| Task | js-baseline | js-jsonld | js-combined |
|------|-------------|-----------|-------------|
| `obs-sio-chemical-entity` | 1.00 (n=3) | 1.00 (n=2) | 1.00 (n=2) |
| `obs-sio-measured-value` | 1.00 (n=3) | 1.00 (n=2) | 1.00 (n=2) |
| `obs-sio-unit` | 1.00 (n=3) | 1.00 (n=2) | 1.00 (n=2) |
| `sio-attribute-inverse` | 0.67 (n=3) | 1.00 (n=2) | 1.00 (n=2) |
| `sio-has-value-type` | 1.00 (n=3) | 1.00 (n=2) | 1.00 (n=2) |
| `sio-measured-value-range` | 0.67 (n=3) | 0.50 (n=2) | 0.50 (n=2) |
| `vocab-obs-to-sensor-properties` | 1.00 (n=2) | 1.00 (n=2) | 1.00 (n=2) |
| `vocab-observation-subclasses` | 1.00 (n=2) | 1.00 (n=2) | 1.00 (n=2) |
| `vocab-sio-datatype-property` | 1.00 (n=1) | 1.00 (n=1) | 1.00 (n=1) |
| `vocab-sio-float-range-properties` | 1.00 (n=1) | 1.00 (n=1) | 0.00 (n=1) |
| `vocab-sio-inverse-chain` | 0.50 (n=2) | 0.50 (n=2) | 0.50 (n=2) |

Notable patterns:
- `vocab-sio-inverse-chain` fails at 50% across all conditions — the hardest task
- `sio-measured-value-range` is the second hardest (0.67/0.50/0.50) — schema property range reasoning
- `sio-attribute-inverse` improves with JSON-LD access: 0.67 → 1.00 (both jsonld and combined)
- All three obs-* data tasks score 1.00 across all conditions — SPARQL exploration sufficient

---

## Run-Level Detail

### js-baseline (5 runs)

#### Run `2026-03-06T17-50-41-018Z`

- File: `trajectory-js-baseline_claude-sonnet-4-6_2026-03-06T17-50-41-018Z.json`
- Tasks: 6
- Mean score: 1.000
- Cost (USD): $0.4934 ($0.0822/task)
- Total wall time: 93.9s
- Total prompt tokens: 138,866
- Total completion tokens: 5,117

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `sio-has-value-type` | 1 | 5 | 3 | 0 | 0 | 16,122 | 15.2 | i0:cq \| i1:cq \| i2:fv \| i3:cq \| i4:(none) |
| `sio-attribute-inverse` | 1 | 3 | 1 | 0 | 0 | 11,319 | 7.9 | i0:fv \| i1:cq \| i2:(none) |
| `sio-measured-value-range` | 1 | 4 | 2 | 0 | 0 | 13,687 | 12.4 | i0:fv \| i1:cq \| i2:cq \| i3:(none) |
| `obs-sio-measured-value` | 1 | 8 | 5 | 0 | 0 | 39,718 | 20.5 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:fetchEntity \| i5:cq,cq \| i6:(none) \| i7:(none) |
| `obs-sio-unit` | 1 | 7 | 3 | 0 | 0 | 34,834 | 20.5 | i0:fv \| i1:cq \| i2:cq \| i3:fetchEntity \| i4:cq \| i5:(none) \| i6:(none) |
| `obs-sio-chemical-entity` | 1 | 6 | 3 | 0 | 0 | 28,303 | 16.4 | i0:fv \| i1:cq \| i2:cq \| i3:fetchEntity \| i4:cq \| i5:(none) |

#### Run `2026-03-11T15-58-31-918Z`

- File: `trajectory-js-baseline_claude-sonnet-4-6_2026-03-11T15-58-31-918Z.json`
- Tasks: 4
- Mean score: 1.000
- Cost (USD): $0.7103 ($0.1776/task)
- Total wall time: 131.9s
- Total prompt tokens: 198,363
- Total completion tokens: 7,679

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `vocab-obs-to-sensor-properties` | 1 | 7 | 5 | 0 | 0 | 52,002 | 31.7 | i0:fs,fv \| i1:cq \| i2:cq \| i3:cq \| i4:cq \| i5:cq \| i6:(none) |
| `vocab-sio-float-range-properties` | 1 | 13 | 10 | 0 | 0 | 89,421 | 51.4 | i0:cq \| i1:fv \| i2:cq \| i3:cq \| i4:cq \| i5:cq \| i6:cq \| i7:cq \| i8:fs \| i9:cq \| i10:cq,cq \| i11:(none) \| i12:(none) |
| `vocab-sio-inverse-chain` | 1 | 5 | 3 | 0 | 0 | 20,699 | 22.4 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:(none) |
| `vocab-observation-subclasses` | 1 | 8 | 6 | 0 | 0 | 43,920 | 25.3 | i0:cq \| i1:cq \| i2:fv \| i3:cq \| i4:cq \| i5:cq \| i6:cq \| i7:(none) |

#### Run `2026-03-11T16-12-53-597Z`

- File: `trajectory-js-baseline_claude-sonnet-4-6_2026-03-11T16-12-53-597Z.json`
- Tasks: 6
- Mean score: 1.000
- Cost (USD): $0.4999 ($0.0833/task)
- Total wall time: 97.8s
- Total prompt tokens: 141,564
- Total completion tokens: 5,013

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `sio-has-value-type` | 1 | 4 | 2 | 0 | 0 | 13,616 | 13.1 | i0:fv \| i1:cq \| i2:cq \| i3:(none) |
| `sio-attribute-inverse` | 1 | 4 | 2 | 0 | 0 | 13,886 | 11.3 | i0:fv \| i1:cq \| i2:cq \| i3:(none) |
| `sio-measured-value-range` | 1 | 4 | 2 | 0 | 0 | 16,496 | 12.4 | i0:fv \| i1:cq \| i2:cq \| i3:(none) |
| `obs-sio-measured-value` | 1 | 6 | 2 | 0 | 0 | 27,995 | 16.8 | i0:fv \| i1:cq \| i2:fetchEntity \| i3:fetchEntity \| i4:cq \| i5:(none) |
| `obs-sio-unit` | 1 | 7 | 3 | 0 | 0 | 33,509 | 18.0 | i0:fv \| i1:cq \| i2:cq \| i3:fetchEntity \| i4:cq \| i5:(none) \| i6:(none) |
| `obs-sio-chemical-entity` | 1 | 8 | 4 | 0 | 0 | 41,075 | 25.3 | i0:fv \| i1:cq \| i2:cq \| i3:fetchEntity \| i4:cq \| i5:cq \| i6:(none) \| i7:(none) |

#### Run `2026-03-11T18-34-35-421Z`

- File: `trajectory-js-baseline_claude-sonnet-4-6_2026-03-11T18-34-35-421Z.json`
- Tasks: 4
- Mean score: 0.750
- Cost (USD): $0.5642 ($0.1411/task)
- Total wall time: 108.7s
- Total prompt tokens: 154,800
- Total completion tokens: 6,654

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `vocab-obs-to-sensor-properties` | 1 | 7 | 5 | 0 | 0 | 46,456 | 32.7 | i0:fs,fv \| i1:cq \| i2:cq \| i3:cq \| i4:cq \| i5:cq \| i6:(none) |
| `vocab-sio-datatype-property` | 1 | 3 | 1 | 0 | 0 | 9,256 | 7.5 | i0:fv \| i1:cq \| i2:(none) |
| `vocab-sio-inverse-chain` | 0 | 9 | 11 | 0 | 0 | 74,072 | 42.5 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:cq \| i5:cq,cq \| i6:cq,cq,cq \| i7:cq,cq \| i8:(none) |
| `vocab-observation-subclasses` | 1 | 8 | 8 | 0 | 0 | 31,670 | 24.9 | i0:cq \| i1:cq \| i2:cq \| i3:cq \| i4:fv \| i5:cq,cq \| i6:cq \| i7:cq |

#### Run `2026-03-11T18-51-09-275Z`

- File: `trajectory-js-baseline_claude-sonnet-4-6_2026-03-11T18-51-09-275Z.json`
- Tasks: 6
- Mean score: 0.667
- Cost (USD): $0.8999 ($0.1500/task)
- Total wall time: 161.3s
- Total prompt tokens: 257,551
- Total completion tokens: 8,485

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `sio-has-value-type` | 1 | 9 | 8 | 0 | 0 | 42,751 | 33.7 | i0:cq \| i1:fv \| i2:cq \| i3:cq \| i4:cq \| i5:cq \| i6:cq \| i7:cq \| i8:cq |
| `sio-attribute-inverse` | 0 | 8 | 6 | 0 | 0 | 56,071 | 31.4 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:cq \| i5:cq \| i6:cq \| i7:(none) |
| `sio-measured-value-range` | 0 | 7 | 5 | 0 | 0 | 48,517 | 25.9 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:cq \| i5:cq \| i6:(none) |
| `obs-sio-measured-value` | 1 | 7 | 4 | 0 | 0 | 47,088 | 29.1 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:cq \| i5:(none) \| i6:(none) |
| `obs-sio-unit` | 1 | 5 | 2 | 0 | 0 | 28,658 | 16.1 | i0:fv \| i1:cq \| i2:cq \| i3:fetchEntity \| i4:(none) |
| `obs-sio-chemical-entity` | 1 | 7 | 2 | 0 | 0 | 42,951 | 23.8 | i0:fv \| i1:cq \| i2:fetchEntity \| i3:fetchEntity \| i4:cq \| i5:(none) \| i6:(none) |

---

### js-jsonld (4 runs)

#### Run `2026-03-11T16-01-32-644Z`

- File: `trajectory-js-jsonld_claude-sonnet-4-6_2026-03-11T16-01-32-644Z.json`
- Tasks: 4
- Mean score: 1.000
- Cost (USD): $0.7603 ($0.1901/task)
- Total wall time: 159.9s
- Total prompt tokens: 209,217
- Total completion tokens: 8,840

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `vocab-obs-to-sensor-properties` | 1 | 4 | 0 | 1 | 1 | 22,428 | 19.0 | i0:fv \| i1:fjl,jsonld.expand \| i2:(none) \| i3:(none) |
| `vocab-sio-float-range-properties` | 1 | 14 | 3 | 7 | 2 | 108,044 | 70.1 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:fjl \| i5:jsonld.expand \| i6:jsonld.expand \| i7:fjl \| i8:fjl \| i9:fjl \| i10:fjl \| i11:fjl \| i12:fjl \| i13:(none) |
| `vocab-sio-inverse-chain` | 1 | 8 | 5 | 1 | 0 | 48,628 | 35.2 | i0:fv \| i1:fjl \| i2:cq \| i3:cq \| i4:cq \| i5:cq,cq \| i6:(none) \| i7:(none) |
| `vocab-observation-subclasses` | 1 | 8 | 2 | 2 | 0 | 38,957 | 30.5 | i0:fjl \| i1:fv \| i2:cq \| i3:fjl \| i4:(none) \| i5:(none) \| i6:cq \| i7:(none) |

#### Run `2026-03-11T16-08-35-772Z`

- File: `trajectory-js-jsonld_claude-sonnet-4-6_2026-03-11T16-08-35-772Z.json`
- Tasks: 6
- Mean score: 1.000
- Cost (USD): $0.5313 ($0.0886/task)
- Total wall time: 113.8s
- Total prompt tokens: 149,355
- Total completion tokens: 5,550

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `sio-has-value-type` | 1 | 5 | 2 | 1 | 1 | 18,659 | 19.6 | i0:fjl,jsonld.expand \| i1:fv \| i2:cq \| i3:cq \| i4:(none) |
| `sio-attribute-inverse` | 1 | 3 | 0 | 1 | 1 | 12,806 | 13.0 | i0:fv \| i1:fjl,jsonld.expand \| i2:(none) |
| `sio-measured-value-range` | 1 | 5 | 2 | 1 | 0 | 27,093 | 16.9 | i0:fv \| i1:fjl \| i2:cq \| i3:cq \| i4:(none) |
| `obs-sio-measured-value` | 1 | 8 | 3 | 0 | 0 | 43,359 | 22.6 | i0:fv \| i1:cq \| i2:fetchEntity \| i3:fetchEntity \| i4:cq \| i5:cq \| i6:(none) \| i7:(none) |
| `obs-sio-unit` | 1 | 6 | 2 | 0 | 0 | 29,732 | 19.4 | i0:fv \| i1:cq \| i2:fetchEntity \| i3:cq \| i4:fetchEntity \| i5:(none) |
| `obs-sio-chemical-entity` | 1 | 5 | 1 | 0 | 0 | 23,256 | 21.4 | i0:fv \| i1:cq \| i2:fetchEntity \| i3:fetchEntity \| i4:(none) |

#### Run `2026-03-11T18-45-54-138Z`

- File: `trajectory-js-jsonld_claude-sonnet-4-6_2026-03-11T18-45-54-138Z.json`
- Tasks: 4
- Mean score: 0.750
- Cost (USD): $0.7403 ($0.1851/task)
- Total wall time: 150.1s
- Total prompt tokens: 201,641
- Total completion tokens: 9,025

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `vocab-obs-to-sensor-properties` | 1 | 7 | 3 | 1 | 1 | 49,984 | 31.5 | i0:fv \| i1:cq \| i2:fjl,jsonld.frame \| i3:cq \| i4:cq \| i5:(none) \| i6:(none) |
| `vocab-sio-datatype-property` | 1 | 4 | 2 | 0 | 0 | 22,393 | 15.0 | i0:fv \| i1:cq \| i2:cq \| i3:(none) |
| `vocab-sio-inverse-chain` | 0 | 8 | 7 | 0 | 0 | 65,242 | 55.7 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:cq,cq \| i5:cq,cq \| i6:(none) \| i7:(none) |
| `vocab-observation-subclasses` | 1 | 9 | 5 | 4 | 2 | 73,047 | 46.9 | i0:fv \| i1:cq \| i2:fjl \| i3:fjl,fjl,jsonld.expand,jsonld.expand \| i4:cq \| i5:cq \| i6:fjl \| i7:cq \| i8:cq |

#### Run `2026-03-11T18-53-46-003Z`

- File: `trajectory-js-jsonld_claude-sonnet-4-6_2026-03-11T18-53-46-003Z.json`
- Tasks: 6
- Mean score: 0.833
- Cost (USD): $0.8809 ($0.1468/task)
- Total wall time: 144.9s
- Total prompt tokens: 256,973
- Total completion tokens: 7,329

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `sio-has-value-type` | 1 | 6 | 3 | 1 | 0 | 39,783 | 23.2 | i0:fv \| i1:cq \| i2:cq \| i3:fjl \| i4:cq \| i5:(none) |
| `sio-attribute-inverse` | 1 | 5 | 2 | 1 | 0 | 31,874 | 17.0 | i0:fv \| i1:cq \| i2:fjl \| i3:cq \| i4:(none) |
| `sio-measured-value-range` | 0 | 6 | 3 | 1 | 0 | 41,031 | 23.4 | i0:fv \| i1:cq \| i2:fjl \| i3:cq \| i4:cq \| i5:(none) |
| `obs-sio-measured-value` | 1 | 7 | 6 | 0 | 0 | 49,103 | 25.6 | i0:fv \| i1:cq \| i2:cq \| i3:cq,cq \| i4:cq,cq \| i5:(none) \| i6:(none) |
| `obs-sio-unit` | 1 | 8 | 4 | 0 | 0 | 55,993 | 29.7 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:fetchEntity \| i5:cq \| i6:(none) \| i7:(none) |
| `obs-sio-chemical-entity` | 1 | 7 | 3 | 0 | 0 | 46,518 | 24.7 | i0:fv \| i1:cq \| i2:cq \| i3:fetchEntity \| i4:cq \| i5:(none) \| i6:(none) |

---

### js-combined (4 runs)

#### Run `2026-03-11T16-06-07-967Z`

- File: `trajectory-js-combined_claude-sonnet-4-6_2026-03-11T16-06-07-967Z.json`
- Tasks: 4
- Mean score: 0.750
- Cost (USD): $0.7070 ($0.1768/task)
- Total wall time: 146.1s
- Total prompt tokens: 196,753
- Total completion tokens: 7,784

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `vocab-obs-to-sensor-properties` | 1 | 6 | 3 | 1 | 1 | 35,522 | 26.6 | i0:fv \| i1:fjl,jsonld.expand \| i2:cq \| i3:cq \| i4:cq \| i5:(none) |
| `vocab-sio-float-range-properties` | 0 | 12 | 8 | 2 | 0 | 83,478 | 58.2 | i0:fv \| i1:cq \| i2:fjl \| i3:(none) \| i4:(none) \| i5:cq \| i6:cq \| i7:fjl \| i8:cq,cq \| i9:cq \| i10:cq,cq \| i11:(none) |
| `vocab-sio-inverse-chain` | 1 | 7 | 0 | 1 | 1 | 43,158 | 29.5 | i0:fv \| i1:fjl \| i2:jsonld.expand \| i3:(none) \| i4:(none) \| i5:(none) \| i6:(none) |
| `vocab-observation-subclasses` | 1 | 8 | 5 | 1 | 0 | 42,379 | 30.4 | i0:fjl \| i1:fv \| i2:cq \| i3:cq \| i4:cq \| i5:cq \| i6:cq \| i7:(none) |

#### Run `2026-03-11T16-10-46-303Z`

- File: `trajectory-js-combined_claude-sonnet-4-6_2026-03-11T16-10-46-303Z.json`
- Tasks: 6
- Mean score: 1.000
- Cost (USD): $0.6251 ($0.1042/task)
- Total wall time: 122.0s
- Total prompt tokens: 178,206
- Total completion tokens: 6,030

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `sio-has-value-type` | 1 | 4 | 1 | 1 | 1 | 13,952 | 14.1 | i0:fjl,jsonld.expand \| i1:fv \| i2:cq \| i3:(none) |
| `sio-attribute-inverse` | 1 | 5 | 3 | 0 | 0 | 24,102 | 16.9 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:(none) |
| `sio-measured-value-range` | 1 | 3 | 0 | 1 | 1 | 12,468 | 10.7 | i0:fv \| i1:fjl,jsonld.expand \| i2:(none) |
| `obs-sio-measured-value` | 1 | 7 | 2 | 0 | 0 | 36,123 | 24.0 | i0:fv \| i1:cq \| i2:fetchEntity \| i3:fetchEntity \| i4:cq \| i5:(none) \| i6:(none) |
| `obs-sio-unit` | 1 | 8 | 5 | 0 | 0 | 54,980 | 26.1 | i0:fv \| i1:cq \| i2:fs \| i3:cq \| i4:cq \| i5:cq \| i6:cq \| i7:(none) |
| `obs-sio-chemical-entity` | 1 | 8 | 4 | 0 | 0 | 42,611 | 29.4 | i0:fv \| i1:cq \| i2:fetchEntity \| i3:fetchEntity \| i4:cq \| i5:cq,cq \| i6:(none) \| i7:(none) |

#### Run `2026-03-11T18-48-13-053Z`

- File: `trajectory-js-combined_claude-sonnet-4-6_2026-03-11T18-48-13-053Z.json`
- Tasks: 4
- Mean score: 0.750
- Cost (USD): $0.7103 ($0.1776/task)
- Total wall time: 128.9s
- Total prompt tokens: 200,153
- Total completion tokens: 7,323

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `vocab-obs-to-sensor-properties` | 1 | 7 | 2 | 1 | 1 | 53,540 | 39.9 | i0:fv \| i1:cq \| i2:fjl \| i3:jsonld.expand \| i4:cq \| i5:(none) \| i6:(none) |
| `vocab-sio-datatype-property` | 1 | 4 | 2 | 0 | 0 | 22,482 | 11.4 | i0:fv \| i1:cq \| i2:cq \| i3:(none) |
| `vocab-sio-inverse-chain` | 0 | 9 | 6 | 2 | 1 | 71,378 | 44.0 | i0:fv \| i1:cq \| i2:cq \| i3:fjl \| i4:fjl,jsonld.frame \| i5:cq \| i6:cq,cq \| i7:cq \| i8:(none) |
| `vocab-observation-subclasses` | 1 | 8 | 5 | 1 | 1 | 60,076 | 32.7 | i0:fv \| i1:cq \| i2:fjl \| i3:jsonld.expand \| i4:cq \| i5:cq \| i6:cq \| i7:cq |

#### Run `2026-03-11T19-09-48-125Z`

- File: `trajectory-js-combined_claude-sonnet-4-6_2026-03-11T19-09-48-125Z.json`
- Tasks: 6
- Mean score: 0.833
- Cost (USD): $0.8743 ($0.1457/task)
- Total wall time: 133.1s
- Total prompt tokens: 253,564
- Total completion tokens: 7,576

**Task breakdown:**

| Task | Score | Iter | comunica | fetchJsonLd | jsonld.* | Tokens | Wall (s) | Tool sequence per iteration |
|------|-------|------|----------|-------------|----------|--------|----------|-----------------------------|
| `sio-has-value-type` | 1 | 6 | 4 | 0 | 0 | 38,626 | 24.5 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:cq \| i5:(none) |
| `sio-attribute-inverse` | 1 | 3 | 1 | 0 | 0 | 15,809 | 9.8 | i0:fv \| i1:cq \| i2:(none) |
| `sio-measured-value-range` | 0 | 7 | 4 | 1 | 0 | 52,602 | 29.9 | i0:fv \| i1:cq \| i2:fjl \| i3:cq \| i4:cq \| i5:cq \| i6:(none) |
| `obs-sio-measured-value` | 1 | 9 | 5 | 0 | 0 | 64,858 | 28.4 | i0:fv \| i1:cq \| i2:fetchEntity \| i3:fetchEntity \| i4:cq \| i5:cq \| i6:cq,cq \| i7:(none) \| i8:(none) |
| `obs-sio-unit` | 1 | 7 | 4 | 0 | 0 | 48,224 | 21.4 | i0:fv \| i1:cq \| i2:cq \| i3:cq \| i4:cq \| i5:(none) \| i6:(none) |
| `obs-sio-chemical-entity` | 1 | 6 | 2 | 0 | 0 | 41,021 | 18.2 | i0:fv \| i1:cq \| i2:fetchEntity \| i3:fetchEntity \| i4:cq \| i5:(none) |

---

## Failure Analysis

Tasks that scored 0 in any run:

| Run | Condition | Task | Score | Iterations | comunica |
|-----|-----------|------|-------|------------|----------|
| 2026-03-11T18-34-35-421Z | js-baseline | `vocab-sio-inverse-chain` | 0 | 9 | 11 |
| 2026-03-11T18-51-09-275Z | js-baseline | `sio-attribute-inverse` | 0 | 8 | 6 |
| 2026-03-11T18-51-09-275Z | js-baseline | `sio-measured-value-range` | 0 | 7 | 5 |
| 2026-03-11T18-45-54-138Z | js-jsonld | `vocab-sio-inverse-chain` | 0 | 8 | 7 |
| 2026-03-11T18-53-46-003Z | js-jsonld | `sio-measured-value-range` | 0 | 6 | 3 |
| 2026-03-11T16-06-07-967Z | js-combined | `vocab-sio-float-range-properties` | 0 | 12 | 8 |
| 2026-03-11T18-48-13-053Z | js-combined | `vocab-sio-inverse-chain` | 0 | 9 | 6 |
| 2026-03-11T19-09-48-125Z | js-combined | `sio-measured-value-range` | 0 | 7 | 4 |

Two persistent failure modes:
1. `vocab-sio-inverse-chain` — fails at 50% in all conditions; high comunica iteration count (6-11) suggests the agent is querying correctly but the answer extraction is failing
2. `sio-measured-value-range` — also fails at 50% in jsonld and combined; fetchJsonLd does not help (it's called in the failing runs)

---

## Tool Usage Patterns

### fetchJsonLd and jsonld.* adoption by task (js-jsonld condition)

| Task | Runs | fetchJsonLd used | jsonld.* used | Mean fetchJsonLd/run | Mean jsonld.*/run |
|------|------|-----------------|---------------|---------------------|------------------|
| `obs-sio-chemical-entity` | 2 | 0/2 | 0/2 | 0.0 | 0.0 |
| `obs-sio-measured-value` | 2 | 0/2 | 0/2 | 0.0 | 0.0 |
| `obs-sio-unit` | 2 | 0/2 | 0/2 | 0.0 | 0.0 |
| `sio-attribute-inverse` | 2 | 2/2 | 1/2 | 1.0 | 0.5 |
| `sio-has-value-type` | 2 | 2/2 | 1/2 | 1.0 | 0.5 |
| `sio-measured-value-range` | 2 | 2/2 | 0/2 | 1.0 | 0.0 |
| `vocab-obs-to-sensor-properties` | 2 | 2/2 | 2/2 | 1.0 | 1.0 |
| `vocab-observation-subclasses` | 2 | 2/2 | 1/2 | 3.0 | 1.0 |
| `vocab-sio-datatype-property` | 1 | 0/1 | 0/1 | 0.0 | 0.0 |
| `vocab-sio-float-range-properties` | 1 | 1/1 | 1/1 | 7.0 | 2.0 |
| `vocab-sio-inverse-chain` | 2 | 1/2 | 0/2 | 0.5 | 0.0 |

### fetchJsonLd and jsonld.* adoption by task (js-combined condition)

| Task | Runs | fetchJsonLd used | jsonld.* used | Mean fetchJsonLd/run | Mean jsonld.*/run |
|------|------|-----------------|---------------|---------------------|------------------|
| `obs-sio-chemical-entity` | 2 | 0/2 | 0/2 | 0.0 | 0.0 |
| `obs-sio-measured-value` | 2 | 0/2 | 0/2 | 0.0 | 0.0 |
| `obs-sio-unit` | 2 | 0/2 | 0/2 | 0.0 | 0.0 |
| `sio-attribute-inverse` | 2 | 0/2 | 0/2 | 0.0 | 0.0 |
| `sio-has-value-type` | 2 | 1/2 | 1/2 | 0.5 | 0.5 |
| `sio-measured-value-range` | 2 | 2/2 | 1/2 | 1.0 | 0.5 |
| `vocab-obs-to-sensor-properties` | 2 | 2/2 | 2/2 | 1.0 | 1.0 |
| `vocab-observation-subclasses` | 2 | 2/2 | 1/2 | 1.0 | 0.5 |
| `vocab-sio-datatype-property` | 1 | 0/1 | 0/1 | 0.0 | 0.0 |
| `vocab-sio-float-range-properties` | 1 | 1/1 | 0/1 | 2.0 | 0.0 |
| `vocab-sio-inverse-chain` | 2 | 2/2 | 2/2 | 1.5 | 1.0 |

### comunica_query calls vs fetchJsonLd calls (schema vs data tasks)

Schema tasks: `sio-attribute-inverse`, `sio-has-value-type`, `sio-measured-value-range`, `vocab-*`
Data tasks: `obs-sio-chemical-entity`, `obs-sio-measured-value`, `obs-sio-unit`

**js-baseline** schema tasks (n=17): mean comunica=4.71, mean fetchJsonLd=0.00
**js-baseline** data tasks (n=9): mean comunica=3.11, mean fetchJsonLd=0.00

**js-jsonld** schema tasks (n=14): mean comunica=2.79, mean fetchJsonLd=1.57
**js-jsonld** data tasks (n=6): mean comunica=3.17, mean fetchJsonLd=0.00

**js-combined** schema tasks (n=14): mean comunica=3.14, mean fetchJsonLd=0.86
**js-combined** data tasks (n=6): mean comunica=3.67, mean fetchJsonLd=0.00

Key finding: fetchJsonLd is used exclusively for schema introspection tasks — identical selectivity pattern to the Python `analyze_rdfs_routes` tool found in phases 4-6. The agent never uses JSON-LD access for data retrieval tasks.

---

## Cost and Token Efficiency

| Condition | Runs | Total Cost (USD) | Mean Cost/Task | Mean Tokens/Task |
|-----------|------|-----------------|---------------|-----------------|
| js-baseline | 5 | $3.1677 | $0.1218 | 35,542 |
| js-jsonld | 4 | $2.9127 | $0.1456 | 42,396 |
| js-combined | 4 | $2.9167 | $0.1458 | 42,869 |

The 19-20% token overhead in jsonld/combined is driven primarily by the large JSON-LD ontology payloads returned by `fetchJsonLd` on schema tasks (e.g. `vocab-sio-float-range-properties` run: 108,044 tokens for a single 14-iteration task with 7 fetchJsonLd calls).

---

## Abbreviations Used in Tool Sequence Column

| Abbreviation | Full name |
|---|---|
| `cq` | `comunica_query` |
| `fjl` | `fetchJsonLd` |
| `fv` | `fetchVoID` |
| `fs` | `fetchShapes` |
| `fe` | `fetchExamples` |
| `jsonld.expand` | `jsonld.expand()` |
| `jsonld.frame` | `jsonld.frame()` |
| `fetchEntity` | `fetchEntity` |
| `(none)` | no tool calls (reasoning-only or return iteration) |
