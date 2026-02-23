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
import sys
import time
from pathlib import Path

import dspy
import httpx

_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO))

from experiments.fabric_navigation.dspy_eval_harness import (
    EvalTask, EvalResult, FabricNavHarness, BenchmarkResult,
    compute_aggregate_stats, substring_match_scorer,
)

from agents.fabric_discovery import discover_endpoint
from agents.fabric_agent import FabricQuery
from agents.fabric_query import make_fabric_query_tool

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
log = logging.getLogger(__name__)

GATEWAY = "http://localhost:8080"

# --- Fabric phase → active features mapping --------------------------------

PHASE_FEATURES = {
    "phase1-baseline": [
        "void-sd", "shacl-agent-hints", "sparql-examples",
    ],
    "phase1+tbox": [
        "void-sd", "shacl-agent-hints", "sparql-examples", "tbox-graph",
    ],
    "phase1+validate": [
        "void-sd", "shacl-agent-hints", "sparql-examples", "tbox-graph", "validate-tool",
    ],
}

# --- Test data setup -------------------------------------------------------

def _build_insert(obs: dict) -> str:
    lines = [
        "PREFIX sosa: <http://www.w3.org/ns/sosa/>",
        "PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>",
        f"INSERT DATA {{ GRAPH <{obs.get('graph', GATEWAY + '/graph/observations')}> {{",
        f"  <{obs['subject']}> a sosa:Observation ;",
        f"    sosa:madeBySensor <{obs['sosa:madeBySensor']}> ;",
        f"    sosa:hasSimpleResult \"{obs['sosa:hasSimpleResult']}\"^^xsd:double ;",
        f"    sosa:resultTime \"{obs['sosa:resultTime']}\"^^xsd:dateTime .",
        "} }",
    ]
    return "\n".join(lines)


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
        return dspy.RLM(
            FabricQuery,
            tools=[make_fabric_query_tool(ep)],
            max_iterations=args.max_iterations,
            verbose=args.verbose,
        )

    def kwarg_builder(task: EvalTask) -> dict:
        return {'endpoint_sd': ep.routing_plan, 'query': task.query}

    harness = FabricNavHarness(
        rlm_factory=rlm_factory,
        kwarg_builder=kwarg_builder,
        scoring_fn=substring_match_scorer,
        verbose=args.verbose,
    )

    results: list[EvalResult] = []
    for task in tasks:
        log.info("Task: %s", task.id)
        try:
            setup_task_data(task)
            result = harness.run_task(task)
            results.append(result)
        finally:
            teardown_task_data(task)

    aggregate = compute_aggregate_stats(results)
    timestamp = time.strftime('%Y%m%d-%H%M%S', time.localtime())
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
