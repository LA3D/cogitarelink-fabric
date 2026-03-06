# Phase 3: SIO TBox Lift Experiments — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 6 SIO+SOSA experiment tasks and extend the harness to insert SIO measurement data, then run phase3a/phase3b experiments to measure TBox routing lift on a vocabulary outside LLM pretraining.

**Architecture:** Reuse the Phase 2 A/B experiment infrastructure. Extend `_build_insert()` to handle SIO triples (multi-hop measurement pattern with explicit MeasuredValue IRIs). Add `phase3a`/`phase3b` to `PHASE_FEATURES` with identical feature lists to Phase 2. New task JSON file with 3 SIO discriminators + 3 SIO efficiency differentiators.

**Tech Stack:** Python 3.12, pytest, httpx, dspy 3.1 (rawwerks fork), Oxigraph SPARQL endpoint (Docker)

**Design doc:** `~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/2026-02-23-sio-tbox-experiments-design.md`

---

### Task 1: Create SIO task file

**Files:**
- Create: `experiments/fabric_navigation/tasks/phase3-sio-tbox.json`

**Step 1: Create the task file with 6 tasks**

```json
[
  {
    "id": "sio-has-value-type",
    "query": "Is sio:has-value a datatype property or an object property according to the SIO ontology?",
    "context": "http://localhost:8080",
    "expected": ["DatatypeProperty"],
    "metadata": {
      "setup": { "type": "none" },
      "description": "Sharp discriminator: owl:DatatypeProperty declaration in /ontology/sio. SIO property typing unlikely in LLM pretraining.",
      "task_type": "discriminator"
    }
  },
  {
    "id": "sio-attribute-inverse",
    "query": "What is the inverse property of sio:has-attribute according to the SIO ontology?",
    "context": "http://localhost:8080",
    "expected": ["is-attribute-of"],
    "metadata": {
      "setup": { "type": "none" },
      "description": "Sharp discriminator: owl:inverseOf declaration in /ontology/sio. Hyphenated SIO property names not guessable from pretraining.",
      "task_type": "discriminator"
    }
  },
  {
    "id": "sio-measured-value-range",
    "query": "What class does sio:has-measurement-value link to according to the SIO ontology?",
    "context": "http://localhost:8080",
    "expected": ["MeasuredValue"],
    "metadata": {
      "setup": { "type": "none" },
      "description": "Sharp discriminator: rdfs:range axiom in /ontology/sio. SIO class hierarchy not in pretraining.",
      "task_type": "discriminator"
    }
  },
  {
    "id": "obs-sio-measured-value",
    "query": "What is the measured value of the observation?",
    "context": "http://localhost:8080",
    "expected": ["21.3"],
    "metadata": {
      "setup": {
        "type": "sparql_insert",
        "graph": "http://localhost:8080/graph/observations",
        "data": [
          {
            "subject": "http://localhost:8080/entity/test-obs-sio-1a",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
            "sosa:resultTime": "2026-02-23T09:00:00Z",
            "sio:has-attribute": "http://localhost:8080/entity/mv-1a",
            "sio:mv-type": "http://semanticscience.org/resource/MeasuredValue",
            "sio:has-value": "21.3"
          }
        ]
      },
      "description": "Efficiency differentiator: measurement encoded via SIO has-attribute → MeasuredValue → has-value chain. No sosa:hasSimpleResult present. Agent must discover SIO measurement pattern.",
      "task_type": "efficiency"
    }
  },
  {
    "id": "obs-sio-unit",
    "query": "What unit was the measurement recorded in?",
    "context": "http://localhost:8080",
    "expected": ["MilliMOL"],
    "metadata": {
      "setup": {
        "type": "sparql_insert",
        "graph": "http://localhost:8080/graph/observations",
        "data": [
          {
            "subject": "http://localhost:8080/entity/test-obs-sio-2a",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
            "sosa:resultTime": "2026-02-23T10:00:00Z",
            "sio:has-attribute": "http://localhost:8080/entity/mv-2a",
            "sio:mv-type": "http://semanticscience.org/resource/MeasuredValue",
            "sio:has-value": "42.7",
            "sio:has-unit": "http://localhost:8080/entity/unit-millimol",
            "sio:unit-label": "MilliMOL"
          }
        ]
      },
      "description": "Efficiency differentiator: SIO measurement chain plus sio:has-unit with rdfs:label. Agent must traverse has-attribute → MeasuredValue → has-unit → label.",
      "task_type": "efficiency"
    }
  },
  {
    "id": "obs-sio-chemical-entity",
    "query": "What chemical entity is the observation about?",
    "context": "http://localhost:8080",
    "expected": ["potassium chloride"],
    "metadata": {
      "setup": {
        "type": "sparql_insert",
        "graph": "http://localhost:8080/graph/observations",
        "data": [
          {
            "subject": "http://localhost:8080/entity/test-obs-sio-3a",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
            "sosa:hasSimpleResult": "18.9",
            "sosa:resultTime": "2026-02-23T11:00:00Z",
            "sio:is-about": "http://localhost:8080/entity/chem-kcl",
            "sio:chem-type": "http://semanticscience.org/resource/ChemicalEntity",
            "sio:chem-label": "potassium chloride"
          }
        ]
      },
      "description": "Efficiency differentiator: sio:is-about linking observation to sio:ChemicalEntity with rdfs:label. Agent must discover is-about property and traverse to label.",
      "task_type": "efficiency"
    }
  }
]
```

**Step 2: Verify JSON is valid**

Run: `python -c "import json; json.load(open('experiments/fabric_navigation/tasks/phase3-sio-tbox.json'))"`
Expected: No error

**Step 3: Commit**

```bash
git add experiments/fabric_navigation/tasks/phase3-sio-tbox.json
git commit -m "feat: add Phase 3 SIO TBox lift experiment tasks (6 tasks)"
```

---

### Task 2: Extend `_build_insert()` to handle SIO triples

The SIO efficiency tasks encode measurements as multi-hop patterns. The existing `_build_insert()` only handles flat SOSA properties. We need to extend it to emit SIO triples: the observation gets `sio:has-attribute <mv-iri>`, the MeasuredValue node gets `a sio:MeasuredValue`, `sio:has-value`, and optionally `sio:has-unit`. Similarly for `sio:is-about` linking to a ChemicalEntity with `rdfs:label`.

The task JSON uses these keys in the `data` objects:
- `sio:has-attribute` — IRI of the MeasuredValue node
- `sio:mv-type` — type IRI for the MeasuredValue node (e.g., `sio:MeasuredValue`)
- `sio:has-value` — literal value on the MeasuredValue node
- `sio:has-unit` — IRI of the unit node
- `sio:unit-label` — rdfs:label on the unit node
- `sio:is-about` — IRI of the entity the observation is about
- `sio:chem-type` — type IRI for the chemical entity
- `sio:chem-label` — rdfs:label on the chemical entity

**Files:**
- Modify: `experiments/fabric_navigation/run_experiment.py:96-117` (`_build_insert` function)
- Test: `tests/pytest/unit/test_tbox_lift_harness.py`

**Step 1: Write failing tests for SIO insert generation**

Add to `tests/pytest/unit/test_tbox_lift_harness.py`:

```python
def test_build_insert_sio_measurement_chain():
    """SIO has-attribute → MeasuredValue → has-value chain."""
    obs = {
        "subject": "http://localhost:8080/entity/obs-sio-1",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:resultTime": "2026-02-23T09:00:00Z",
        "sio:has-attribute": "http://localhost:8080/entity/mv-1",
        "sio:mv-type": "http://semanticscience.org/resource/MeasuredValue",
        "sio:has-value": "21.3",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sio:has-attribute" in q
    assert "<http://localhost:8080/entity/mv-1>" in q
    assert "sio:MeasuredValue" in q
    assert 'sio:has-value "21.3"' in q


def test_build_insert_sio_unit():
    """SIO measurement with has-unit and rdfs:label on unit node."""
    obs = {
        "subject": "http://localhost:8080/entity/obs-sio-2",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:resultTime": "2026-02-23T10:00:00Z",
        "sio:has-attribute": "http://localhost:8080/entity/mv-2",
        "sio:mv-type": "http://semanticscience.org/resource/MeasuredValue",
        "sio:has-value": "42.7",
        "sio:has-unit": "http://localhost:8080/entity/unit-millimol",
        "sio:unit-label": "MilliMOL",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sio:has-unit" in q
    assert "unit-millimol" in q
    assert 'rdfs:label "MilliMOL"' in q


def test_build_insert_sio_is_about():
    """SIO is-about linking to ChemicalEntity with rdfs:label."""
    obs = {
        "subject": "http://localhost:8080/entity/obs-sio-3",
        "sosa:madeBySensor": "http://localhost:8080/entity/sensor-1",
        "sosa:hasSimpleResult": "18.9",
        "sosa:resultTime": "2026-02-23T11:00:00Z",
        "sio:is-about": "http://localhost:8080/entity/chem-kcl",
        "sio:chem-type": "http://semanticscience.org/resource/ChemicalEntity",
        "sio:chem-label": "potassium chloride",
        "graph": "http://localhost:8080/graph/observations",
    }
    q = _build_insert(obs)
    assert "sio:is-about" in q
    assert "chem-kcl" in q
    assert "sio:ChemicalEntity" in q
    assert 'rdfs:label "potassium chloride"' in q
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && pytest tests/pytest/unit/test_tbox_lift_harness.py -v -k "sio"`
Expected: 3 FAILED (assertions about SIO properties not found in output)

**Step 3: Extend `_build_insert()` with SIO support**

In `experiments/fabric_navigation/run_experiment.py`, replace the `_build_insert` function (lines 96-117) with:

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
    # SIO: has-attribute → MeasuredValue node
    if 'sio:has-attribute' in obs:
        mv_iri = obs['sio:has-attribute']
        props.append(f"    sio:has-attribute <{mv_iri}>")
    # SIO: is-about → entity node
    if 'sio:is-about' in obs:
        props.append(f"    sio:is-about <{obs['sio:is-about']}>")

    body = " ;\n".join(props) + " ."

    # SIO secondary nodes (MeasuredValue, unit, ChemicalEntity)
    extra_triples = []
    if 'sio:has-attribute' in obs:
        mv_iri = obs['sio:has-attribute']
        mv_type = obs.get('sio:mv-type', 'http://semanticscience.org/resource/MeasuredValue')
        extra_triples.append(f"  <{mv_iri}> a <{mv_type}>")
        if 'sio:has-value' in obs:
            extra_triples.append(f"  <{mv_iri}> sio:has-value \"{obs['sio:has-value']}\"^^xsd:double")
        if 'sio:has-unit' in obs:
            unit_iri = obs['sio:has-unit']
            extra_triples.append(f"  <{mv_iri}> sio:has-unit <{unit_iri}>")
            if 'sio:unit-label' in obs:
                extra_triples.append(f"  <{unit_iri}> rdfs:label \"{obs['sio:unit-label']}\"")
    if 'sio:is-about' in obs:
        about_iri = obs['sio:is-about']
        if 'sio:chem-type' in obs:
            extra_triples.append(f"  <{about_iri}> a <{obs['sio:chem-type']}>")
        if 'sio:chem-label' in obs:
            extra_triples.append(f"  <{about_iri}> rdfs:label \"{obs['sio:chem-label']}\"")

    extra_body = ""
    if extra_triples:
        extra_body = "\n" + " .\n".join(extra_triples) + " .\n"

    return (
        "PREFIX sosa: <http://www.w3.org/ns/sosa/>\n"
        "PREFIX sio:  <http://semanticscience.org/resource/>\n"
        "PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>\n"
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        f"INSERT DATA {{ GRAPH <{g}> {{\n{body}\n{extra_body}}} }}"
    )
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && pytest tests/pytest/unit/test_tbox_lift_harness.py -v`
Expected: ALL PASS (7 existing + 3 new = 10 tests)

**Step 5: Run full unit test suite to check no regressions**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && pytest tests/pytest/unit/ -v`
Expected: All unit tests pass

**Step 6: Commit**

```bash
git add experiments/fabric_navigation/run_experiment.py tests/pytest/unit/test_tbox_lift_harness.py
git commit -m "feat: extend _build_insert for SIO measurement chain + 3 TDD tests"
```

---

### Task 3: Add Phase 3 entries to `PHASE_FEATURES`

**Files:**
- Modify: `experiments/fabric_navigation/run_experiment.py:46-87` (`PHASE_FEATURES` dict)

**Step 1: Write a failing test**

Add to `tests/pytest/unit/test_tbox_lift_harness.py`:

```python
from experiments.fabric_navigation.run_experiment import PHASE_FEATURES

def test_phase3_features_exist():
    assert "phase3a-no-tbox-paths" in PHASE_FEATURES
    assert "phase3b-tbox-paths" in PHASE_FEATURES

def test_phase3b_has_tbox_graph_paths():
    assert "tbox-graph-paths" in PHASE_FEATURES["phase3b-tbox-paths"]
    assert "tbox-graph-paths" not in PHASE_FEATURES["phase3a-no-tbox-paths"]

def test_phase3_features_match_phase2():
    """Phase 3 should have same feature sets as Phase 2 (only task file differs)."""
    assert PHASE_FEATURES["phase3a-no-tbox-paths"] == PHASE_FEATURES["phase2a-no-tbox-paths"]
    assert PHASE_FEATURES["phase3b-tbox-paths"] == PHASE_FEATURES["phase2b-tbox-paths"]
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && pytest tests/pytest/unit/test_tbox_lift_harness.py -v -k "phase3"`
Expected: 3 FAILED (KeyError: 'phase3a-no-tbox-paths')

**Step 3: Add phase3 entries to PHASE_FEATURES**

In `experiments/fabric_navigation/run_experiment.py`, after the `phase2b-tbox-paths` entry (line 86), add:

```python
    "phase3a-no-tbox-paths": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
    ],
    "phase3b-tbox-paths": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths",
    ],
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && pytest tests/pytest/unit/test_tbox_lift_harness.py -v`
Expected: ALL PASS (13 tests)

**Step 5: Commit**

```bash
git add experiments/fabric_navigation/run_experiment.py tests/pytest/unit/test_tbox_lift_harness.py
git commit -m "feat: add phase3a/phase3b to PHASE_FEATURES + 3 TDD tests"
```

---

### Task 4: Run Phase 3a experiment (no TBox paths)

**Prerequisites:** Docker stack running (`docker compose up -d` from `/Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric`), Oxigraph bootstrapped with ontology graphs, `ANTHROPIC_API_KEY` set.

**Step 1: Verify Docker stack is healthy**

Run: `curl -s http://localhost:8080/.well-known/void | head -5`
Expected: Turtle output starting with `@prefix`

**Step 2: Run phase3a experiment**

Run:
```bash
cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && \
python experiments/fabric_navigation/run_experiment.py \
  --tasks experiments/fabric_navigation/tasks/phase3-sio-tbox.json \
  --phase phase3a-no-tbox-paths \
  --output experiments/fabric_navigation/results/ \
  --model anthropic/claude-sonnet-4-6 \
  --verbose
```
Expected: Results printed showing 6 tasks with scores (expect some < 1.0)

**Step 3: Commit results**

```bash
git add experiments/fabric_navigation/results/phase3a-*.json experiments/fabric_navigation/trajectories/phase3a-*.jsonl
git commit -m "data: Phase 3a experiment results (no TBox paths, SIO tasks)"
```

---

### Task 5: Run Phase 3b experiment (with TBox paths)

**Step 1: Run phase3b experiment**

Run:
```bash
cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && \
python experiments/fabric_navigation/run_experiment.py \
  --tasks experiments/fabric_navigation/tasks/phase3-sio-tbox.json \
  --phase phase3b-tbox-paths \
  --output experiments/fabric_navigation/results/ \
  --model anthropic/claude-sonnet-4-6 \
  --verbose
```
Expected: Results with potentially higher scores than phase3a

**Step 2: Compare results**

Manually compare:
- Phase 3a vs 3b mean score (primary metric)
- Phase 3a vs 3b per-task scores (which tasks did TBox paths help?)
- Per-task iteration delta

**Step 3: Commit results**

```bash
git add experiments/fabric_navigation/results/phase3b-*.json experiments/fabric_navigation/trajectories/phase3b-*.jsonl
git commit -m "data: Phase 3b experiment results (TBox paths, SIO tasks)"
```

---

### Task 6: Update Obsidian vault with Phase 3 results

**Files:**
- Modify: `~/Obsidian/obsidian/Daily/2026-02-23.md`
- Modify: `~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/KF-Prototype-PLAN.md`

**Step 1: Append Phase 3 results to daily note**

Add a new section after the Phase 2 TBox lift experiments section with:
- Results table (phase3a vs phase3b: score, iterations, SPARQL, cost)
- Per-task comparison table
- Key finding (did TBox path visibility improve SIO task scores?)

**Step 2: Update KF-Prototype-PLAN experiment track**

Add Phase 3 results to the Experiment Track section.

**Step 3: Commit vault changes**

```bash
cd ~/Obsidian/obsidian && \
git add "Daily/2026-02-23.md" "01 - Projects/Knowledge Fabric Prototyping/KF-Prototype-PLAN.md" && \
git commit -m "[Agent: Claude] docs: Phase 3 SIO TBox lift experiment results"
```
