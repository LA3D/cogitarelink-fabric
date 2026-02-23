"""Unit tests for TrajectoryLogger (TDD — written before implementation)."""
import json
from pathlib import Path
import pytest

from experiments.fabric_navigation.dspy_eval_harness import write_trajectory_jsonl


TRAJECTORY = [
    {"reasoning": "Let me read the endpoint.", "code": "print(endpoint_sd)", "output": "Endpoint: http://localhost:8080\n..."},
    {"reasoning": "I'll query for the sensor.", "code": "result = sparql_query(sparql)\nprint(result)", "output": '{"head":{},"results":{"bindings":[]}}'},
    {"reasoning": "Empty. Discover sensors.", "code": "result = sparql_query(discover)\nprint(result)", "output": '{"results":{"bindings":[{"sensor":{"value":"http://localhost:8080/entity/sensor-1"}}]}}'},
]

META = dict(phase="phase1-baseline", task_id="sensor-temp-by-name", model="claude-sonnet-4-6", timestamp="2026-02-23T09:00:00Z")


def test_write_trajectory_jsonl_creates_file(tmp_path):
    path = tmp_path / "run.jsonl"
    write_trajectory_jsonl(TRAJECTORY, path, **META)
    assert path.exists()


def test_write_trajectory_jsonl_one_line_per_step(tmp_path):
    path = tmp_path / "run.jsonl"
    write_trajectory_jsonl(TRAJECTORY, path, **META)
    lines = path.read_text().strip().splitlines()
    assert len(lines) == len(TRAJECTORY)


def test_write_trajectory_jsonl_each_line_is_valid_json(tmp_path):
    path = tmp_path / "run.jsonl"
    write_trajectory_jsonl(TRAJECTORY, path, **META)
    for line in path.read_text().strip().splitlines():
        json.loads(line)  # must not raise


def test_write_trajectory_jsonl_step_fields(tmp_path):
    path = tmp_path / "run.jsonl"
    write_trajectory_jsonl(TRAJECTORY, path, **META)
    steps = [json.loads(l) for l in path.read_text().strip().splitlines()]

    assert steps[0]["step"] == 1
    assert steps[1]["step"] == 2
    assert steps[2]["step"] == 3

    for i, step in enumerate(steps):
        assert step["phase"] == META["phase"]
        assert step["task_id"] == META["task_id"]
        assert step["model"] == META["model"]
        assert step["reasoning"] == TRAJECTORY[i]["reasoning"]
        assert step["code"] == TRAJECTORY[i]["code"]
        assert step["output"] == TRAJECTORY[i]["output"]


def test_write_trajectory_jsonl_empty_does_not_create_file(tmp_path):
    path = tmp_path / "run.jsonl"
    write_trajectory_jsonl([], path, **META)
    assert not path.exists()


def test_write_trajectory_jsonl_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "deep" / "run.jsonl"
    write_trajectory_jsonl(TRAJECTORY, path, **META)
    assert path.exists()
