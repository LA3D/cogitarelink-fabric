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

import os

import dspy
import httpx

_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO))

from experiments.fabric_navigation.dspy_eval_harness import (
    EvalTask, EvalResult, FabricNavHarness, BenchmarkResult,
    compute_aggregate_stats, substring_match_scorer, write_trajectory_jsonl,
)

from agents.fabric_discovery import discover_endpoint, register_and_authenticate
from agents.fabric_agent import FabricQuery
from agents.fabric_query import make_fabric_query_tool
from agents.fabric_rdfs_routes import make_rdfs_routes_tool

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
log = logging.getLogger(__name__)

GATEWAY = "http://localhost:8080"
VP_TOKEN: str | None = None  # set in main() after authentication

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
    "phase5a-no-rdfs-routes": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths",
    ],
    "phase5b-rdfs-routes": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths", "rdfs-routes",
    ],
    "phase6a-no-rdfs-routes": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths",
        "no-entity-lookup", "no-unbounded-scan",
    ],
    "phase6b-rdfs-routes": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths", "rdfs-routes",
        "no-entity-lookup", "no-unbounded-scan",
    ],
}

def _strip_tbox_paths(routing_plan: str) -> str:
    """Remove '-> /ontology/X' suffixes — produces phase2a control routing plan."""
    return re.sub(r' -> /ontology/\S+', '', routing_plan)


def _strip_entity_lookup(routing_plan: str) -> str:
    """Remove the 'Entity lookup by IRI' example from SD text."""
    return re.sub(
        r'  "Entity lookup by IRI".*?(?=  "|$)',
        '',
        routing_plan,
        flags=re.DOTALL,
    )


# --- Test data setup -------------------------------------------------------

def _build_sensor_insert(rec: dict) -> str:
    """Build INSERT DATA for a sosa:Sensor entity in /graph/entities."""
    g = rec.get('graph', GATEWAY + '/graph/entities')
    subj = rec['subject']
    props = [f"  <{subj}> a sosa:Sensor"]
    if 'rdfs:label' in rec:
        props.append(f'    rdfs:label "{rec["rdfs:label"]}"')
    if 'sosa:observes' in rec:
        props.append(f"    sosa:observes <{rec['sosa:observes']}>")
    if 'sosa:isHostedBy' in rec:
        props.append(f"    sosa:isHostedBy <{rec['sosa:isHostedBy']}>")
    body = " ;\n".join(props) + " ."

    extra = []
    # ObservableProperty secondary node
    if 'sosa:observes' in rec:
        op = rec['sosa:observes']
        extra.append(f"  <{op}> a sosa:ObservableProperty .")
        if 'sosa:observes-label' in rec:
            extra.append(f'  <{op}> rdfs:label "{rec["sosa:observes-label"]}" .')
    # Platform secondary node
    if 'sosa:isHostedBy' in rec:
        plat = rec['sosa:isHostedBy']
        extra.append(f"  <{plat}> a sosa:Platform .")
        if 'sosa:isHostedBy-label' in rec:
            extra.append(f'  <{plat}> rdfs:label "{rec["sosa:isHostedBy-label"]}" .')

    # Noise predicates — plausible but irrelevant triples to defeat ?p ?o scanning
    for np in rec.get('noise_predicates', []):
        extra.append(f"  <{subj}> {np['p']} {np['o']} .")

    extra_body = "\n" + "\n".join(extra) + "\n" if extra else ""
    return (
        "PREFIX sosa: <http://www.w3.org/ns/sosa/>\n"
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        "PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>\n"
        "PREFIX dct:  <http://purl.org/dc/terms/>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
        "PREFIX schema: <https://schema.org/>\n"
        "PREFIX dcat: <http://www.w3.org/ns/dcat#>\n"
        "PREFIX ssn:  <http://www.w3.org/ns/ssn/>\n"
        "PREFIX owl:  <http://www.w3.org/2002/07/owl#>\n"
        f"INSERT DATA {{ GRAPH <{g}> {{\n{body}\n{extra_body}}} }}"
    )


def _build_insert(obs: dict) -> str:
    if obs.get('record_type') == 'sensor':
        return _build_sensor_insert(obs)
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


def _sparql_update_headers() -> dict[str, str]:
    h = {"Content-Type": "application/x-www-form-urlencoded"}
    if VP_TOKEN:
        h["Authorization"] = f"Bearer {VP_TOKEN}"
    return h


def setup_task_data(task: EvalTask) -> None:
    setup = task.metadata.get('setup', {})
    if setup.get('type') != 'sparql_insert':
        return
    for obs in setup.get('data', []):
        obs_with_graph = {**obs}
        if 'graph' not in obs_with_graph:
            obs_with_graph['graph'] = setup.get('graph', GATEWAY + '/graph/observations')
        q = _build_insert(obs_with_graph)
        httpx.post(
            f"{GATEWAY}/sparql/update",
            data={"update": q},
            headers=_sparql_update_headers(),
        ).raise_for_status()


def teardown_task_data(task: EvalTask) -> None:
    setup = task.metadata.get('setup', {})
    if setup.get('type') != 'sparql_insert':
        return
    graphs = [setup.get('graph', GATEWAY + '/graph/observations')]
    graphs.extend(setup.get('extra_graphs', []))
    for graph in graphs:
        httpx.post(
            f"{GATEWAY}/sparql/update",
            data={"update": f"DROP SILENT GRAPH <{graph}>"},
            headers=_sparql_update_headers(),
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
    parser.add_argument('--temperature', type=float, default=None,
                        help='LM temperature. Use >0 (e.g. 0.7) for ensemble replications to defeat prompt caching.')
    parser.add_argument('--no-cache', action='store_true',
                        help='Disable dspy local cache. Use with --temperature for genuine independent samples.')
    args = parser.parse_args()

    tasks_raw = json.loads(Path(args.tasks).read_text())
    tasks = [EvalTask(**t) for t in tasks_raw]

    lm_kwargs: dict = {}
    if args.temperature is not None:
        lm_kwargs['temperature'] = args.temperature
    if args.no_cache:
        lm_kwargs['cache'] = False
    dspy.configure(lm=dspy.LM(args.model, **lm_kwargs))

    # Authenticate before discovery — SPARQL endpoint is VP-gated (D13)
    vp_token = None
    if os.environ.get("FABRIC_AUTH_ENABLED", "true").lower() == "true":
        r = httpx.post(
            f"{GATEWAY}/test/create-vp",
            json={"agentRole": "DevelopmentAgentRole",
                  "authorizedGraphs": ["*"],
                  "authorizedOperations": ["read", "write"]},
            timeout=15.0, verify=False,
        )
        r.raise_for_status()
        vp_token = r.json()["token"]
        log.info("Authenticated: VP token obtained")
        global VP_TOKEN
        VP_TOKEN = vp_token

    ep = discover_endpoint(GATEWAY, vp_token=vp_token)

    def rlm_factory() -> dspy.RLM:
        features = PHASE_FEATURES[args.phase]
        reject_unbounded = 'no-unbounded-scan' in features
        tools = [make_fabric_query_tool(ep, reject_unbounded=reject_unbounded)]
        if "rdfs-routes" in features:
            tools.append(make_rdfs_routes_tool(ep))
        return dspy.RLM(
            FabricQuery,
            tools=tools,
            max_iterations=args.max_iterations,
            verbose=args.verbose,
        )

    _RDFS_TOOL_HINT = (
        "\n\nANALYSIS TOOLS (call from REPL code):\n"
        "  analyze_rdfs_routes(information_need: str) -> str\n"
        "    Consults the endpoint's loaded ontology axioms (domain/range,\n"
        "    inverse properties, class hierarchies, OWL restrictions) that\n"
        "    are NOT available via SPARQL queries against the data graphs.\n"
        "\n"
        "    Returns: property traversal directions (forward/backward),\n"
        "    inverse property pairs, and SPARQL triple patterns.\n"
        "\n"
        "    USE WHEN:\n"
        "    - A SPARQL query returns empty and you suspect a property\n"
        "      direction or graph placement issue\n"
        "    - You need to know which property connects two classes but\n"
        "      have no instance data to explore\n"
        "    - You see two similar property names (e.g., observes vs\n"
        "      observedProperty) and need to know which applies to which class\n"
        "\n"
        "    NOT NEEDED WHEN:\n"
        "    - Instance data is available and you can discover predicates\n"
        "      via SELECT ?p ?o exploration\n"
        "\n"
        "    Example:\n"
        "      # Schema question: which direction does sio:has-attribute go?\n"
        "      routes = analyze_rdfs_routes('What is the domain and range of sio:has-attribute?')\n"
        "      print(routes)  # Shows: domain=Entity, range=Attribute, FORWARD traversal\n"
        "\n"
        "      # Property confusion: two similar names, which applies here?\n"
        "      routes = analyze_rdfs_routes('What is the difference between sosa:observes and sosa:observedProperty?')\n"
        "      print(routes)  # Shows: observes domain=Sensor, observedProperty domain=Observation\n"
    )

    def kwarg_builder(task: EvalTask) -> dict:
        sd = ep.routing_plan
        features = PHASE_FEATURES[args.phase]
        if 'tbox-graph-paths' not in features:
            sd = _strip_tbox_paths(sd)
        if 'no-entity-lookup' in features:
            sd = _strip_entity_lookup(sd)
        if 'rdfs-routes' in features:
            sd = sd + _RDFS_TOOL_HINT
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
