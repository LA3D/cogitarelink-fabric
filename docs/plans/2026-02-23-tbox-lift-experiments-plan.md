# TBox Lift Experiments Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 6 TBox-lift tasks and two new experiment phases (phase2a-no-tbox-paths / phase2b-tbox-paths) to the fabric navigation experiment harness, then run both phases and collect results.

**Architecture:** New task file `tasks/phase2-tbox-lift.json` (6 tasks: 3 sharp discriminators requiring ontology graph SPARQL, 3 efficiency differentiators with richer instance data). Two new phases in `PHASE_FEATURES`; the only difference between them is whether the routing plan string passed to the RLM reveals `-> /ontology/{stem}` paths. A new helper `_strip_tbox_paths` removes those paths for phase2a. `_build_insert` is extended to handle optional SOSA properties (`usedProcedure`, `hasFeatureOfInterest`, `phenomenonTime`).

**Tech Stack:** Python 3.12, dspy 3.1 (rawwerks fork), httpx, Oxigraph SPARQL (Docker, `http://localhost:8080`). Run experiments with `~/uvws/.venv/bin/python`. Unit tests with `~/uvws/.venv/bin/pytest`.

**Design doc:** `docs/plans/2026-02-23-tbox-lift-experiments-design.md`

---

### Context

`run_experiment.py` is at `experiments/fabric_navigation/run_experiment.py`.
`PHASE_FEATURES` dict maps phase name → list of active feature strings.
`_build_insert(obs: dict) -> str` builds a SPARQL INSERT DATA statement from an observation dict.
`kwarg_builder(task)` returns `{'endpoint_sd': ..., 'query': ...}` for the RLM.
The routing plan (from `ep.routing_plan`) now contains lines like:
```
  sosa: <http://www.w3.org/ns/sosa/> -> /ontology/sosa
```
For phase2a we strip those `-> /ontology/sosa` suffixes; for phase2b we leave them.

Ontology data: the 7 ontologies are loaded into Oxigraph at container start. The agent can query them with the existing `sparql_query` tool using `GRAPH <http://localhost:8080/ontology/sosa> { ... }`. No new tools needed.

---

### Task 1: Create `tasks/phase2-tbox-lift.json`

**Files:**
- Create: `experiments/fabric_navigation/tasks/phase2-tbox-lift.json`

No unit test for this — it's data. Verify by loading it as JSON.

**Step 1: Write the task file**

Create `experiments/fabric_navigation/tasks/phase2-tbox-lift.json`:

```json
[
  {
    "id": "schema-property-type",
    "query": "Is sosa:hasSimpleResult a datatype property or an object property according to the SOSA ontology?",
    "context": "http://localhost:8080",
    "expected": ["DatatypeProperty"],
    "metadata": {
      "setup": {"type": "none"},
      "description": "Sharp discriminator: answer exists only in /ontology/sosa graph. Requires SPARQL against ontology named graph. Without tbox-graph-paths, agent has no signal that /ontology/sosa exists.",
      "task_type": "discriminator"
    }
  },
  {
    "id": "schema-used-procedure-range",
    "query": "What class does sosa:usedProcedure link an observation to, according to the SOSA ontology?",
    "context": "http://localhost:8080",
    "expected": ["Procedure"],
    "metadata": {
      "setup": {"type": "none"},
      "description": "Sharp discriminator: rdfs:range of sosa:usedProcedure is sosa:Procedure. Not in SHACL shape. Requires ontology graph query.",
      "task_type": "discriminator"
    }
  },
  {
    "id": "schema-phenomenon-time-exists",
    "query": "Does the SOSA ontology define a property for when the observed phenomenon actually occurred (distinct from when the result was recorded)?",
    "context": "http://localhost:8080",
    "expected": ["phenomenonTime"],
    "metadata": {
      "setup": {"type": "none"},
      "description": "Sharp discriminator: sosa:phenomenonTime exists in SOSA ontology but not in SHACL shape or SPARQL examples. Requires ontology graph query.",
      "task_type": "discriminator"
    }
  },
  {
    "id": "obs-used-procedure",
    "query": "What procedure was used to collect the observations?",
    "context": "http://localhost:8080",
    "expected": ["electrochemical-scan"],
    "metadata": {
      "setup": {
        "type": "sparql_insert",
        "graph": "http://localhost:8080/graph/observations",
        "data": [
          {
            "subject": "http://localhost:8080/entity/test-obs-tbox-4a",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
            "sosa:hasSimpleResult": "21.3",
            "sosa:resultTime": "2026-02-23T09:00:00Z",
            "sosa:usedProcedure": "http://localhost:8080/entity/procedure-electrochemical-scan"
          },
          {
            "subject": "http://localhost:8080/entity/test-obs-tbox-4b",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-2",
            "sosa:hasSimpleResult": "22.1",
            "sosa:resultTime": "2026-02-23T09:30:00Z",
            "sosa:usedProcedure": "http://localhost:8080/entity/procedure-electrochemical-scan"
          }
        ]
      },
      "description": "Efficiency differentiator: sosa:usedProcedure not in SHACL shape or SPARQL examples. Without tbox-graph-paths, agent must probe for the property name. With paths, can look it up in /ontology/sosa first.",
      "task_type": "efficiency"
    }
  },
  {
    "id": "obs-feature-of-interest",
    "query": "What feature of interest was being observed?",
    "context": "http://localhost:8080",
    "expected": ["sample-alpha"],
    "metadata": {
      "setup": {
        "type": "sparql_insert",
        "graph": "http://localhost:8080/graph/observations",
        "data": [
          {
            "subject": "http://localhost:8080/entity/test-obs-tbox-5a",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
            "sosa:hasSimpleResult": "19.8",
            "sosa:resultTime": "2026-02-23T10:00:00Z",
            "sosa:hasFeatureOfInterest": "http://localhost:8080/entity/feature-sample-alpha"
          }
        ]
      },
      "description": "Efficiency differentiator: sosa:hasFeatureOfInterest not in SHACL shape or examples. Agent must discover property name to answer.",
      "task_type": "efficiency"
    }
  },
  {
    "id": "obs-phenomenon-time",
    "query": "When did the observed phenomenon actually occur (not when the result was recorded)?",
    "context": "http://localhost:8080",
    "expected": ["11:30"],
    "metadata": {
      "setup": {
        "type": "sparql_insert",
        "graph": "http://localhost:8080/graph/observations",
        "data": [
          {
            "subject": "http://localhost:8080/entity/test-obs-tbox-6a",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
            "sosa:hasSimpleResult": "24.7",
            "sosa:resultTime": "2026-02-23T12:00:00Z",
            "sosa:phenomenonTime": "2026-02-23T11:30:00Z"
          }
        ]
      },
      "description": "Efficiency differentiator: sosa:phenomenonTime (phenomenon occurrence) vs sosa:resultTime (recording time). Agent must distinguish the two; without TBox may return resultTime (12:00) instead of phenomenonTime (11:30).",
      "task_type": "efficiency"
    }
  }
]
```

**Step 2: Verify it loads as valid JSON**

```bash
~/uvws/.venv/bin/python -c "
import json; tasks = json.loads(open('experiments/fabric_navigation/tasks/phase2-tbox-lift.json').read())
print(f'{len(tasks)} tasks loaded')
for t in tasks: print(f'  {t[\"id\"]} ({t[\"metadata\"][\"task_type\"]})')
"
```

Expected:
```
6 tasks loaded
  schema-property-type (discriminator)
  schema-used-procedure-range (discriminator)
  schema-phenomenon-time-exists (discriminator)
  obs-used-procedure (efficiency)
  obs-feature-of-interest (efficiency)
  obs-phenomenon-time (efficiency)
```

**Step 3: Commit**

```bash
git add experiments/fabric_navigation/tasks/phase2-tbox-lift.json
git commit -m "feat: add phase2 TBox lift task file (6 tasks: 3 discriminators + 3 efficiency)"
```

---

### Task 2: TDD `_strip_tbox_paths` helper

**Files:**
- Create: `tests/pytest/unit/test_tbox_lift_harness.py`
- Modify: `experiments/fabric_navigation/run_experiment.py` (add function, ~5 lines)

**Step 1: Write the failing test**

Create `tests/pytest/unit/test_tbox_lift_harness.py`:

```python
"""Unit tests for TBox lift experiment harness helpers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

from experiments.fabric_navigation.run_experiment import _strip_tbox_paths


ROUTING_PLAN_WITH_PATHS = """\
Endpoint: http://localhost:8080
SPARQL: http://localhost:8080/sparql
Profile: https://w3id.org/cogitarelink/fabric#CoreProfile

Local ontology cache (no external dereferencing needed):
  prov: <http://www.w3.org/ns/prov#> -> /ontology/prov
  sio: <http://semanticscience.org/resource/> -> /ontology/sio
  sosa: <http://www.w3.org/ns/sosa/> -> /ontology/sosa
  time: <http://www.w3.org/2006/time#> -> /ontology/time
  xsd: <http://www.w3.org/2001/XMLSchema#>
"""

def test_strip_removes_ontology_paths():
    result = _strip_tbox_paths(ROUTING_PLAN_WITH_PATHS)
    assert "-> /ontology/" not in result

def test_strip_preserves_namespace_iris():
    result = _strip_tbox_paths(ROUTING_PLAN_WITH_PATHS)
    assert "<http://www.w3.org/ns/sosa/>" in result
    assert "<http://www.w3.org/ns/prov#>" in result

def test_strip_idempotent_on_plan_without_paths():
    plan_no_paths = "  sosa: <http://www.w3.org/ns/sosa/>\n"
    assert _strip_tbox_paths(plan_no_paths) == plan_no_paths
```

**Step 2: Run to verify it fails**

```bash
~/uvws/.venv/bin/pytest tests/pytest/unit/test_tbox_lift_harness.py -v
```

Expected: `ImportError` or `cannot import name '_strip_tbox_paths'`

**Step 3: Implement `_strip_tbox_paths` in `run_experiment.py`**

Add after the existing imports (around line 14, after `import time`):

```python
import re
```

Add after `PHASE_FEATURES` dict (around line 75), before the `_build_insert` function:

```python
def _strip_tbox_paths(routing_plan: str) -> str:
    """Remove '-> /ontology/X' suffixes — produces phase2a control routing plan."""
    return re.sub(r' -> /ontology/\S+', '', routing_plan)
```

**Step 4: Run tests to verify they pass**

```bash
~/uvws/.venv/bin/pytest tests/pytest/unit/test_tbox_lift_harness.py -v
```

Expected: `3 passed`

**Step 5: Commit**

```bash
git add tests/pytest/unit/test_tbox_lift_harness.py experiments/fabric_navigation/run_experiment.py
git commit -m "feat: _strip_tbox_paths helper for phase2a routing plan control"
```

---

### Task 3: TDD extended `_build_insert`

**Files:**
- Modify: `tests/pytest/unit/test_tbox_lift_harness.py` (add tests)
- Modify: `experiments/fabric_navigation/run_experiment.py` (`_build_insert`)

**Step 1: Write failing tests — append to `test_tbox_lift_harness.py`**

```python
from experiments.fabric_navigation.run_experiment import _build_insert


def test_build_insert_baseline_unchanged():
    obs = {
        "subject": "http://localhost:8080/entity/obs-1",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "23.5",
        "sosa:resultTime": "2026-02-23T12:00:00Z",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sosa:madeBySensor" in q
    assert "23.5" in q
    assert "sosa:usedProcedure" not in q

def test_build_insert_includes_used_procedure():
    obs = {
        "subject": "http://localhost:8080/entity/obs-2",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "21.0",
        "sosa:resultTime": "2026-02-23T09:00:00Z",
        "sosa:usedProcedure": "http://localhost:8080/entity/procedure-cv-scan",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sosa:usedProcedure" in q
    assert "procedure-cv-scan" in q

def test_build_insert_includes_feature_of_interest():
    obs = {
        "subject": "http://localhost:8080/entity/obs-3",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "19.5",
        "sosa:resultTime": "2026-02-23T10:00:00Z",
        "sosa:hasFeatureOfInterest": "http://localhost:8080/entity/feature-sample-alpha",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sosa:hasFeatureOfInterest" in q
    assert "feature-sample-alpha" in q

def test_build_insert_includes_phenomenon_time():
    obs = {
        "subject": "http://localhost:8080/entity/obs-4",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "24.7",
        "sosa:resultTime": "2026-02-23T12:00:00Z",
        "sosa:phenomenonTime": "2026-02-23T11:30:00Z",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sosa:phenomenonTime" in q
    assert "11:30:00" in q
```

**Step 2: Run to verify they fail**

```bash
~/uvws/.venv/bin/pytest tests/pytest/unit/test_tbox_lift_harness.py::test_build_insert_includes_used_procedure -v
```

Expected: FAIL — `_build_insert` doesn't include `sosa:usedProcedure`

**Step 3: Rewrite `_build_insert` in `run_experiment.py`**

Replace the existing `_build_insert` function (lines ~79-90) with:

```python
def _build_insert(obs: dict) -> str:
    g = obs.get('graph', GATEWAY + '/graph/observations')
    subj = obs['subject']
    props = [f"  <{subj}> a sosa:Observation"]
    if 'sosa:madeBySensor' in obs:
        props.append(f"    sosa:madeBySensor <{obs['sosa:madeBySensor']}>")
    if 'sosa:hasSimpleResult' in obs:
        props.append(f"    sosa:hasSimpleResult \"{obs['sosa:hasSimpleResult']}\"^^xsd:double")
    if 'sosa:resultTime' in obs:
        props.append(f"    sosa:resultTime \"{obs['sosa:resultTime']}\"^^xsd:dateTime")
    if 'sosa:phenomenonTime' in obs:
        props.append(f"    sosa:phenomenonTime \"{obs['sosa:phenomenonTime']}\"^^xsd:dateTime")
    if 'sosa:usedProcedure' in obs:
        props.append(f"    sosa:usedProcedure <{obs['sosa:usedProcedure']}>")
    if 'sosa:hasFeatureOfInterest' in obs:
        props.append(f"    sosa:hasFeatureOfInterest <{obs['sosa:hasFeatureOfInterest']}>")
    body = " ;\n".join(props) + " ."
    return (
        "PREFIX sosa: <http://www.w3.org/ns/sosa/>\n"
        "PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>\n"
        f"INSERT DATA {{ GRAPH <{g}> {{\n{body}\n}} }}"
    )
```

**Step 4: Run all harness tests**

```bash
~/uvws/.venv/bin/pytest tests/pytest/unit/test_tbox_lift_harness.py -v
```

Expected: `7 passed`

**Step 5: Run full unit suite to confirm no regressions**

```bash
~/uvws/.venv/bin/pytest tests/pytest/unit/ -q
```

Expected: `44 passed` (existing) + `7 passed` = `51 passed`

Wait — the harness tests count as part of unit suite. Expected: **51 passed, 0 failed**.

**Step 6: Commit**

```bash
git add tests/pytest/unit/test_tbox_lift_harness.py experiments/fabric_navigation/run_experiment.py
git commit -m "feat: extend _build_insert for optional SOSA properties (usedProcedure, hasFeatureOfInterest, phenomenonTime)"
```

---

### Task 4: Add new phases and update `kwarg_builder`

**Files:**
- Modify: `experiments/fabric_navigation/run_experiment.py` (PHASE_FEATURES + kwarg_builder + setup_task_data guard)

No new tests needed — the unit tests cover the helpers; the phase wiring is integration-tested by running the experiment.

**Step 1: Add two new phases to `PHASE_FEATURES` in `run_experiment.py`**

After the existing `"phase1+validate"` entry (around line 74), add:

```python
    "phase2a-no-tbox-paths": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
    ],
    "phase2b-tbox-paths": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths",
    ],
```

**Step 2: Update `kwarg_builder` inside `main()` to strip paths for phase2a**

Find this block in `main()` (around line 144):

```python
    def kwarg_builder(task: EvalTask) -> dict:
        return {'endpoint_sd': ep.routing_plan, 'query': task.query}
```

Replace with:

```python
    def kwarg_builder(task: EvalTask) -> dict:
        sd = ep.routing_plan
        if "tbox-graph-paths" not in PHASE_FEATURES[args.phase]:
            sd = _strip_tbox_paths(sd)
        return {'endpoint_sd': sd, 'query': task.query}
```

**Step 3: Guard `setup_task_data` for `type: none` tasks**

The discriminator tasks have `"setup": {"type": "none"}`. The existing guard `if setup.get('type') != 'sparql_insert': return` already handles this correctly — no change needed. Verify by reading lines 93-96 of `run_experiment.py`.

**Step 4: Verify `--phase` choices automatically include new phases**

The `argparse` uses `choices=list(PHASE_FEATURES.keys())` so new phases appear automatically. Confirm with:

```bash
~/uvws/.venv/bin/python experiments/fabric_navigation/run_experiment.py --help 2>&1 | grep phase2
```

Expected: output contains `phase2a-no-tbox-paths` and `phase2b-tbox-paths`

**Step 5: Commit**

```bash
git add experiments/fabric_navigation/run_experiment.py
git commit -m "feat: add phase2a-no-tbox-paths and phase2b-tbox-paths experiment phases"
```

---

### Task 5: Run phase2a experiment (control — no ontology paths)

**Prerequisites:** Docker stack running (`docker compose up -d`), `ANTHROPIC_API_KEY` set.

**Step 1: Verify Docker is up**

```bash
curl -s http://localhost:8080/.well-known/void | head -5
```

Expected: Turtle VoID output starting with `@prefix`

**Step 2: Run phase2a**

```bash
~/uvws/.venv/bin/python experiments/fabric_navigation/run_experiment.py \
    --tasks experiments/fabric_navigation/tasks/phase2-tbox-lift.json \
    --phase phase2a-no-tbox-paths \
    --output experiments/fabric_navigation/results/ \
    --model anthropic/claude-sonnet-4-6 \
    --max-iterations 12 \
    --verbose
```

Expected console output:
```
Tasks: 6/6 completed
Mean score: ~0.5  (discriminators 0.0, efficiency tasks 1.0)
Mean iterations: ~6-8
```

The discriminators should score 0.0 — agent has no signal about ontology graph paths.

**Step 3: Note the result file path** (e.g. `results/phase2a-no-tbox-paths-20260223-XXXXXX.json`)

**Step 4: Quick sanity check**

```bash
~/uvws/.venv/bin/python -c "
import json
r = json.loads(open('experiments/fabric_navigation/results/$(ls -t experiments/fabric_navigation/results/phase2a* | head -1 | xargs basename)').read())
for t in r['results']:
    print(f'{t[\"taskId\"]}: score={t[\"score\"]} iter={t[\"iterations\"]}')
print('mean score:', r['aggregate']['meanScore'])
"
```

---

### Task 6: Run phase2b experiment (treatment — ontology paths revealed)

**Step 1: Run phase2b**

```bash
~/uvws/.venv/bin/python experiments/fabric_navigation/run_experiment.py \
    --tasks experiments/fabric_navigation/tasks/phase2-tbox-lift.json \
    --phase phase2b-tbox-paths \
    --output experiments/fabric_navigation/results/ \
    --model anthropic/claude-sonnet-4-6 \
    --max-iterations 12 \
    --verbose
```

Expected console output:
```
Tasks: 6/6 completed
Mean score: ~1.0  (all tasks succeed)
Mean iterations: ~4-5
```

**Step 2: Compare the two runs**

```bash
~/uvws/.venv/bin/python -c "
import json, glob

phase2a = sorted(glob.glob('experiments/fabric_navigation/results/phase2a-*.json'))[-1]
phase2b = sorted(glob.glob('experiments/fabric_navigation/results/phase2b-*.json'))[-1]

a = json.loads(open(phase2a).read())
b = json.loads(open(phase2b).read())

print('Task-level comparison:')
print(f'{\"Task\":<35} {\"phase2a score\":>13} {\"phase2b score\":>13} {\"Δ iter\":>8}')
a_by_id = {r[\"taskId\"]: r for r in a[\"results\"]}
b_by_id = {r[\"taskId\"]: r for r in b[\"results\"]}
for tid in a_by_id:
    ra, rb = a_by_id[tid], b_by_id[tid]
    delta = ra[\"iterations\"] - rb[\"iterations\"]
    print(f'{tid:<35} {ra[\"score\"]:>13.1f} {rb[\"score\"]:>13.1f} {delta:>+8}')

print()
print(f'Mean score  — phase2a: {a[\"aggregate\"][\"meanScore\"]:.3f}  phase2b: {b[\"aggregate\"][\"meanScore\"]:.3f}')
print(f'Mean iter   — phase2a: {a[\"aggregate\"][\"meanIterations\"]:.1f}  phase2b: {b[\"aggregate\"][\"meanIterations\"]:.1f}')
"
```

**Expected output shape:**
```
Task                                  phase2a score  phase2b score    Δ iter
schema-property-type                            0.0            1.0        +N
schema-used-procedure-range                     0.0            1.0        +N
schema-phenomenon-time-exists                   0.0            1.0        +N
obs-used-procedure                              1.0            1.0        +2
obs-feature-of-interest                         1.0            1.0        +2
obs-phenomenon-time                             1.0            1.0        +1
```

**Step 3: Commit results**

```bash
git add experiments/fabric_navigation/results/phase2a-*.json \
        experiments/fabric_navigation/results/phase2b-*.json \
        experiments/fabric_navigation/trajectories/phase2a-*.jsonl \
        experiments/fabric_navigation/trajectories/phase2b-*.jsonl
git commit -m "experiment: phase2a/phase2b TBox lift results"
```

---

## Full Verification

```bash
# Unit tests (no Docker needed)
~/uvws/.venv/bin/pytest tests/pytest/unit/ -v

# Integration tests (needs Docker stack)
~/uvws/.venv/bin/pytest tests/pytest/integration/ -v
```

Expected: all existing tests pass + 7 new unit tests pass.

## Success Criteria

- All 51 unit tests pass (44 existing + 7 new)
- phase2a: discriminators score 0.0, efficiency tasks score 1.0
- phase2b: all 6 tasks score 1.0
- Δiterations ≥ 1.5 (mean efficiency task iterations: phase2a − phase2b)
- Trajectories saved for both phases
