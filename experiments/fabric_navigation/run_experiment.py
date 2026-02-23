"""Run fabric navigation experiment.

Usage:
    python experiments/fabric-navigation/run_experiment.py \
        --tasks experiments/fabric-navigation/tasks/baseline.json \
        --phase phase1-baseline \
        --output experiments/fabric-navigation/results/ \
        --model anthropic/claude-sonnet-4-6 \
        --verbose

Results are saved as: results/<phase>-<timestamp>.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

import dspy
import httpx

_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO))

from experiments.fabric_navigation.dspy_eval_harness import (
    EvalTask, EvalResult, FabricNavHarness, BenchmarkResult,
    compute_aggregate_stats, substring_match_scorer, write_trajectory_jsonl,
)

from agents.fabric_discovery import discover_endpoint
from agents.fabric_agent import FabricQuery
from agents.fabric_query import make_fabric_query_tool
from agents.fabric_rdfs_routes import make_rdfs_routes_tool

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
log = logging.getLogger(__name__)

GATEWAY = "http://localhost:8080"

# --- Fabric phase → active features mapping --------------------------------

PHASE_FEATURES = {
    "phase1-baseline": [
        "void-sd", "shacl-agent-hints", "sparql-examples",
    ],
    "phase1.5a-urispace": [
        "void-sd", "void-urispace", "shacl-prefixes",
        "shacl-class-pattern", "shacl-agent-hints", "sparql-examples",
    ],
    "phase1.5b-graphinv": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples",
    ],
    "phase1.5c-examples": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended",
    ],
    "phase1.5d-routing": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended",
        "enhanced-routing-plan",
    ],
    "phase1+tbox": [
        "void-sd", "shacl-agent-hints", "sparql-examples", "tbox-graph",
    ],
    "phase1+validate": [
        "void-sd", "shacl-agent-hints", "sparql-examples", "tbox-graph", "validate-tool",
    ],
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
    "phase4a-no-rdfs-routes": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths",
    ],
    "phase4b-rdfs-routes": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths", "rdfs-routes",
    ],
}

def _strip_tbox_paths(routing_plan: str) -> str:
    """Remove '-> /ontology/X' suffixes — produces phase2a control routing plan."""
    return re.sub(r' -> /ontology/\S+', '', routing_plan)


# --- Test data setup -------------------------------------------------------

def _build_insert(obs: dict) -> str:
    SIO_NS = "http://semanticscience.org/resource/"
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
    if 'sio:has-attribute' in obs:
        props.append(f"    sio:has-attribute <{obs['sio:has-attribute']}>")
    if 'sio:is-about' in obs:
        props.append(f"    sio:is-about <{obs['sio:is-about']}>")
    body = " ;\n".join(props) + " ."

    # SIO secondary nodes (MeasuredValue, unit, ChemicalEntity)
    extra = []
    if 'sio:has-attribute' in obs:
        mv = obs['sio:has-attribute']
        mv_type = obs.get('sio:mv-type', SIO_NS + 'MeasuredValue')
        local = mv_type.removeprefix(SIO_NS)
        extra.append(f"  <{mv}> a sio:{local} .")
        if 'sio:has-value' in obs:
            extra.append(f"  <{mv}> sio:has-value \"{obs['sio:has-value']}\"^^xsd:double .")
        if 'sio:has-unit' in obs:
            unit = obs['sio:has-unit']
            extra.append(f"  <{mv}> sio:has-unit <{unit}> .")
            if 'sio:unit-label' in obs:
                extra.append(f"  <{unit}> rdfs:label \"{obs['sio:unit-label']}\" .")
    if 'sio:is-about' in obs:
        about = obs['sio:is-about']
        if 'sio:chem-type' in obs:
            local = obs['sio:chem-type'].removeprefix(SIO_NS)
            extra.append(f"  <{about}> a sio:{local} .")
        if 'sio:chem-label' in obs:
            extra.append(f"  <{about}> rdfs:label \"{obs['sio:chem-label']}\" .")

    extra_body = "\n" + "\n".join(extra) + "\n" if extra else ""
    return (
        "PREFIX sosa: <http://www.w3.org/ns/sosa/>\n"
        "PREFIX sio:  <http://semanticscience.org/resource/>\n"
        "PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>\n"
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        f"INSERT DATA {{ GRAPH <{g}> {{\n{body}\n{extra_body}}} }}"
    )


def setup_task_data(task: EvalTask) -> None:
    setup = task.metadata.get('setup', {})
    if setup.get('type') != 'sparql_insert':
        return
    for obs in setup.get('data', []):
        obs_with_graph = {**obs, 'graph': setup.get('graph', GATEWAY + '/graph/observations')}
        q = _build_insert(obs_with_graph)
        httpx.post(
            f"{GATEWAY}/sparql/update",
            data={"update": q},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).raise_for_status()


def teardown_task_data(task: EvalTask) -> None:
    setup = task.metadata.get('setup', {})
    if setup.get('type') != 'sparql_insert':
        return
    graph = setup.get('graph', GATEWAY + '/graph/observations')
    httpx.post(
        f"{GATEWAY}/sparql/update",
        data={"update": f"DROP SILENT GRAPH <{graph}>"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


# --- Main ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Fabric navigation experiment runner")
    parser.add_argument('--tasks', default='experiments/fabric-navigation/tasks/baseline.json')
    parser.add_argument('--phase', default='phase1-baseline',
                        choices=list(PHASE_FEATURES.keys()))
    parser.add_argument('--output', default='experiments/fabric-navigation/results/')
    parser.add_argument('--model', default='anthropic/claude-sonnet-4-6')
    parser.add_argument('--max-iterations', type=int, default=10)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    tasks_raw = json.loads(Path(args.tasks).read_text())
    tasks = [EvalTask(**t) for t in tasks_raw]

    dspy.configure(lm=dspy.LM(args.model))
    ep = discover_endpoint(GATEWAY)

    def rlm_factory() -> dspy.RLM:
        features = PHASE_FEATURES[args.phase]
        tools = [make_fabric_query_tool(ep)]
        if "rdfs-routes" in features:
            tools.append(make_rdfs_routes_tool(ep))
        return dspy.RLM(
            FabricQuery,
            tools=tools,
            max_iterations=args.max_iterations,
            verbose=args.verbose,
        )

    def kwarg_builder(task: EvalTask) -> dict:
        sd = ep.routing_plan
        if 'tbox-graph-paths' not in PHASE_FEATURES[args.phase]:
            sd = _strip_tbox_paths(sd)
        return {'endpoint_sd': sd, 'query': task.query}

    harness = FabricNavHarness(
        rlm_factory=rlm_factory,
        kwarg_builder=kwarg_builder,
        scoring_fn=substring_match_scorer,
        verbose=args.verbose,
    )

    timestamp = time.strftime('%Y%m%d-%H%M%S', time.localtime())
    traj_dir = Path(args.output).parent / "trajectories"

    results: list[EvalResult] = []
    for task in tasks:
        log.info("Task: %s", task.id)
        try:
            setup_task_data(task)
            result = harness.run_task(task)
            results.append(result)
            write_trajectory_jsonl(
                result.trace,
                traj_dir / f"{args.phase}-{task.id}-{timestamp}.jsonl",
                phase=args.phase,
                task_id=task.id,
                model=args.model,
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            )
        finally:
            teardown_task_data(task)

    aggregate = compute_aggregate_stats(results)
    br = BenchmarkResult(
        benchmark="fabric-navigation",
        model=args.model,
        fabric_phase=args.phase,
        fabric_features=PHASE_FEATURES[args.phase],
        config={'maxIterations': args.max_iterations},
        timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        results=results,
        aggregate=aggregate,
    )

    out_path = Path(args.output) / f"{args.phase}-{timestamp}.json"
    br.save_json(out_path)
    print(f"\nResults saved to: {out_path}")
    print(f"  Tasks: {aggregate.completedTasks}/{len(tasks)} completed")
    print(f"  Mean score: {aggregate.meanScore:.3f}")
    print(f"  Mean iterations: {aggregate.meanIterations:.1f}")
    print(f"  Convergence: {aggregate.convergenceRate:.0%}")
    print(f"  Mean SPARQL attempts: {aggregate.meanSparqlAttempts:.1f}")
    print(f"  Mean empty recoveries: {aggregate.meanEmptyRecoveries:.1f}")
    print(f"  Cost estimate: ${aggregate.costEstimateUsd:.4f}")


if __name__ == '__main__':
    main()
