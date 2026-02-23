"""
Fabric Navigation Evaluation Harness

Tracks how the RLM agent navigates a fabric endpoint over time as features are added.
Matches node-rlm metrics format for cross-experiment comparison.

Based on: experiments/structured_observation/dspy_eval_harness.py in ontology-agent-kr
Key addition: fabric_metrics — navigation-specific signals extracted from trajectory.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import dspy

logger = logging.getLogger(__name__)


@dataclass
class EvalTask:
    id: str
    query: str
    context: str          # endpoint base URL
    expected: str | list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CharCount:
    input: int = 0
    output: int = 0


@dataclass
class FabricMetrics:
    """Navigation signals extracted from the RLM trajectory.

    These are the fabric-specific metrics that let us measure how the
    four-layer KR (D9) changes agent behavior across phases.
    """
    read_routing_plan_iter: int | None    # iteration where agent read endpoint_sd
    first_sparql_iter: int | None         # iteration of first SPARQL tool call
    sparql_attempts: int                  # total SPARQL calls made
    empty_result_recoveries: int          # times agent got empty results and retried
    used_shacl_hint: bool                 # agent hint from ObservationShape in code/reasoning
    used_sparql_example: bool             # SPARQL example pattern used as template
    named_graphs_queried: list[str]       # named graph IRIs that appeared in queries
    final_named_graph: str | None         # graph used in the successful query


@dataclass
class EvalResult:
    taskId: str
    answer: str
    expected: str | list[str]
    score: float
    iterations: int
    converged: bool
    trace: list[dict[str, Any]]
    wallTimeMs: float
    charCount: CharCount
    fabric: FabricMetrics | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['charCount'] = {'input': self.charCount.input, 'output': self.charCount.output}
        return d


@dataclass
class AggregateStats:
    meanScore: float
    medianScore: float
    stdScore: float
    meanIterations: float
    medianIterations: float
    meanWallTimeMs: float
    totalWallTimeMs: float
    totalInputChars: int
    totalOutputChars: int
    costEstimateUsd: float
    convergenceRate: float    # fraction of tasks where agent converged
    meanSparqlAttempts: float
    meanEmptyRecoveries: float
    completedTasks: int
    failedTasks: int


@dataclass
class BenchmarkResult:
    benchmark: str
    model: str
    fabric_phase: str         # e.g. "phase1-baseline", "phase1+tbox", "phase2"
    fabric_features: list[str]  # active fabric features at time of run
    config: dict[str, Any]
    timestamp: str
    results: list[EvalResult]
    aggregate: AggregateStats

    def to_dict(self) -> dict[str, Any]:
        return {
            'benchmark': self.benchmark,
            'model': self.model,
            'fabric_phase': self.fabric_phase,
            'fabric_features': self.fabric_features,
            'config': self.config,
            'timestamp': self.timestamp,
            'results': [r.to_dict() for r in self.results],
            'aggregate': asdict(self.aggregate),
        }

    def save_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w') as f:
            json.dump(self.to_dict(), f, indent=2)


# --- Trajectory analysis ---------------------------------------------------

def _extract_fabric_metrics(trajectory: list[dict[str, Any]]) -> FabricMetrics:
    """Extract fabric navigation signals from RLM trajectory steps."""
    read_sd_iter = None
    first_sparql_iter = None
    sparql_attempts = 0
    empty_recoveries = 0
    used_hint = False
    used_example = False
    named_graphs: list[str] = []
    final_graph = None

    for i, step in enumerate(trajectory):
        code = step.get('code', '')
        output = step.get('output', '')
        reasoning = step.get('reasoning', '')
        combined = code + reasoning

        # Did agent read the routing plan?
        if read_sd_iter is None and 'endpoint_sd' in code:
            read_sd_iter = i + 1

        # Did agent call sparql_query?
        if 'sparql_query' in code or ('GRAPH' in code and 'SELECT' in code.upper()):
            sparql_attempts += 1
            if first_sparql_iter is None:
                first_sparql_iter = i + 1
            # Track named graphs from query
            import re
            graphs = re.findall(r'GRAPH\s*<([^>]+)>', code, re.IGNORECASE)
            for g in graphs:
                if g not in named_graphs:
                    named_graphs.append(g)
            if graphs:
                final_graph = graphs[-1]

        # Did agent get empty results and need to recover?
        if ('"bindings":[]' in output or '"bindings": []' in output) and sparql_attempts > 0:
            empty_recoveries += 1

        # Did agent reference the SHACL agent hint?
        if 'Agent hint' in combined or 'agentInstruction' in combined or '/graph/observations' in combined:
            used_hint = True

        # Did agent use the SPARQL example as a template?
        if 'List recent observations' in combined or 'Observations by sensor' in combined:
            used_example = True

    return FabricMetrics(
        read_routing_plan_iter=read_sd_iter,
        first_sparql_iter=first_sparql_iter,
        sparql_attempts=sparql_attempts,
        empty_result_recoveries=empty_recoveries,
        used_shacl_hint=used_hint,
        used_sparql_example=used_example,
        named_graphs_queried=named_graphs,
        final_named_graph=final_graph,
    )


# --- Tracking helpers -------------------------------------------------------

class CharacterCountTracker:
    def __init__(self, lm: dspy.LM):
        self.lm = lm
        self.initial_history_len = 0

    def __enter__(self):
        self.initial_history_len = len(self.lm.history) if hasattr(self.lm, 'history') else 0
        return self

    def __exit__(self, *_):
        pass

    def get_counts(self) -> CharCount:
        input_chars = output_chars = 0
        if not hasattr(self.lm, 'history') or not self.lm.history:
            return CharCount()
        for entry in self.lm.history[self.initial_history_len:]:
            if not isinstance(entry, dict):
                continue
            if 'prompt' in entry and entry['prompt']:
                input_chars += len(str(entry['prompt']))
            if 'messages' in entry and entry['messages']:
                for msg in entry['messages']:
                    input_chars += len(str(msg.get('content', '') if isinstance(msg, dict) else msg))
            if 'response' in entry and entry['response']:
                r = entry['response']
                if hasattr(r, 'choices'):
                    for c in r.choices:
                        if hasattr(c, 'message') and hasattr(c.message, 'content'):
                            output_chars += len(str(c.message.content))
            if 'outputs' in entry and entry['outputs']:
                for o in entry['outputs']:
                    output_chars += len(str(o))
        return CharCount(input=input_chars, output=output_chars)


def _estimate_cost(char_count: CharCount, model: str = "claude-sonnet-4-6") -> float:
    input_tokens = char_count.input / 4
    output_tokens = char_count.output / 4
    return (input_tokens / 1_000_000) * 3 + (output_tokens / 1_000_000) * 15


def compute_aggregate_stats(results: list[EvalResult]) -> AggregateStats:
    if not results:
        return AggregateStats(**{f: 0 for f in AggregateStats.__dataclass_fields__})

    scores = [r.score for r in results]
    iters = [r.iterations for r in results]
    times = [r.wallTimeMs for r in results]
    completed = [r for r in results if r.error is None]
    fabric_results = [r for r in completed if r.fabric]

    total_in = sum(r.charCount.input for r in results)
    total_out = sum(r.charCount.output for r in results)

    return AggregateStats(
        meanScore=statistics.mean(scores),
        medianScore=statistics.median(scores),
        stdScore=statistics.stdev(scores) if len(scores) > 1 else 0.0,
        meanIterations=statistics.mean(iters),
        medianIterations=statistics.median(iters),
        meanWallTimeMs=statistics.mean(times),
        totalWallTimeMs=sum(times),
        totalInputChars=total_in,
        totalOutputChars=total_out,
        costEstimateUsd=_estimate_cost(CharCount(total_in, total_out)),
        convergenceRate=sum(1 for r in completed if r.converged) / len(completed) if completed else 0.0,
        meanSparqlAttempts=statistics.mean([r.fabric.sparql_attempts for r in fabric_results]) if fabric_results else 0.0,
        meanEmptyRecoveries=statistics.mean([r.fabric.empty_result_recoveries for r in fabric_results]) if fabric_results else 0.0,
        completedTasks=len(completed),
        failedTasks=sum(1 for r in results if r.error is not None),
    )


# --- Harness ----------------------------------------------------------------

class FabricNavHarness:
    """Evaluation harness for fabric navigation experiments.

    Adapts DSPyRLMHarness from ontology-agent-kr for fabric-specific metrics.
    The kwarg_builder maps EvalTask → endpoint_sd + query for FabricQuery signature.
    """

    def __init__(
        self,
        rlm_factory: Callable[[], dspy.RLM],
        kwarg_builder: Callable[[EvalTask], dict[str, Any]],
        scoring_fn: Callable[[str, str | list[str], dict | None], float],
        verbose: bool = False,
    ):
        self.rlm_factory = rlm_factory
        self.kwarg_builder = kwarg_builder
        self.scoring_fn = scoring_fn
        self.verbose = verbose

    def run_task(self, task: EvalTask) -> EvalResult:
        start = time.time()
        rlm = self.rlm_factory()
        lm = dspy.settings.lm
        char_tracker = CharacterCountTracker(lm)

        try:
            with char_tracker:
                result = rlm(**self.kwarg_builder(task))

            wall_ms = (time.time() - start) * 1000
            trajectory = getattr(result, 'trajectory', [])
            final_reasoning = getattr(result, 'final_reasoning', None)
            converged = (final_reasoning is not None
                         and final_reasoning != "Extract forced final output")
            answer = str(getattr(result, 'answer', ''))
            score = self.scoring_fn(answer, task.expected, task.metadata)
            counts = char_tracker.get_counts()
            fabric = _extract_fabric_metrics(trajectory)

            if self.verbose:
                logger.info(
                    "[%s] score=%.2f iter=%d sparql=%d recoveries=%d time=%.0fms",
                    task.id, score, len(trajectory),
                    fabric.sparql_attempts, fabric.empty_result_recoveries, wall_ms
                )

            return EvalResult(
                taskId=task.id, answer=answer, expected=task.expected,
                score=score, iterations=len(trajectory), converged=converged,
                trace=trajectory, wallTimeMs=wall_ms, charCount=counts, fabric=fabric,
            )

        except Exception as exc:
            wall_ms = (time.time() - start) * 1000
            counts = char_tracker.get_counts()
            logger.error("[%s] Failed: %s", task.id, exc)
            return EvalResult(
                taskId=task.id, answer="", expected=task.expected,
                score=0.0, iterations=0, converged=False,
                trace=[], wallTimeMs=wall_ms, charCount=counts, error=str(exc),
            )

    def run_benchmark(
        self,
        tasks: list[EvalTask],
        benchmark: str,
        model: str,
        fabric_phase: str,
        fabric_features: list[str],
        max_iterations: int = 10,
        save_path: str | Path | None = None,
    ) -> BenchmarkResult:
        logger.info("Running '%s' (%s) on %d tasks", benchmark, fabric_phase, len(tasks))
        results = [self.run_task(t) for t in tasks]
        aggregate = compute_aggregate_stats(results)

        br = BenchmarkResult(
            benchmark=benchmark,
            model=model,
            fabric_phase=fabric_phase,
            fabric_features=fabric_features,
            config={'maxIterations': max_iterations},
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            results=results,
            aggregate=aggregate,
        )

        if save_path:
            br.save_json(save_path)
            logger.info("Saved to %s", save_path)

        logger.info(
            "Done: %d/%d completed, mean score=%.3f, mean iter=%.1f, convergence=%.0f%%",
            aggregate.completedTasks, len(tasks),
            aggregate.meanScore, aggregate.meanIterations,
            aggregate.convergenceRate * 100,
        )
        return br


# --- Scoring ----------------------------------------------------------------

def substring_match_scorer(predicted: str, expected: str | list[str], metadata=None) -> float:
    predicted = predicted.lower()
    if isinstance(expected, str):
        expected = [expected]
    return 1.0 if any(e.lower() in predicted for e in expected) else 0.0
