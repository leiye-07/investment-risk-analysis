# Stage 2 Evaluation Framework

Stage 2 evaluates completed investment risk workflow runs. It does not execute or control the workflow.

The workflow remains responsible for:

1. Parsing the investment question.
2. Planning evidence needs.
3. Retrieving and normalizing evidence.
4. Building an evidence pack.
5. Running the reasoning graph.
6. Composing the memo.
7. Verifying citations.

Evaluation observes the resulting `workflow.pipeline.WorkflowRun` and produces an `EvaluationReport`.

## Design Principle

Workflow execution and evaluation are intentionally separated:

```text
InvestmentRequest
-> Stage 1 workflow execution
-> WorkflowRun
-> Stage 2 EvaluationRunner
-> EvaluationReport
```

The evaluation package never calls retrieval adapters, evidence planners, or reasoning nodes directly. This keeps evaluation useful for replay, diffing, debugging, benchmark runs, and future threshold experiments without coupling it to workflow execution.

## WorkflowRun Artifact

The existing `workflow.pipeline.WorkflowRun` is the canonical run object. Stage 2 support is added by refactoring that object, not by creating a parallel run model.

`WorkflowRun.to_evaluation_artifact()` returns a JSON-serializable structure:

```text
run_id
request
workflow_plan
retrieval_trace
evidence_pack
reasoning_nodes
final_memo
metadata
```

The artifact is designed for later replay, diff, and debugging workflows. It captures enough information for evaluators to inspect the run without re-running the workflow.

## Package Layout

```text
evaluation/
  runner.py
  models.py
  report.py
  failure_classifier.py

  offline/
    benchmark.py
    citation.py
    coverage.py
    recommendation.py
    llm_judge.py

  runtime/
    health.py
    thresholds.py
    drift.py
    replay.py

  online/
    feedback.py
    human_review.py
    ab_test.py
```

## EvaluationRunner

`EvaluationRunner.evaluate(...)` accepts:

```python
run: WorkflowRun
benchmark: BenchmarkCase | None = None
user_actions: dict | None = None
```

Runtime checks always run.

Offline checks run only when a benchmark case is provided.

Online checks run only when user actions are provided.

After all checks finish, the failure classifier maps failed checks into normalized failure categories.

## Offline Evaluation

Offline evaluation answers:

```text
Does this workflow solve known benchmark cases correctly?
```

Current benchmark cases live in `data/benchmarks/`.

The initial benchmark format is JSON:

```json
{
  "case_id": "nvidia_risk_001",
  "investment_question": "Identify major downside risks for NVIDIA over the next 12 months.",
  "expected_findings": [],
  "expected_sources": [],
  "expected_recommendation": "watch",
  "expected_confidence": "medium",
  "metadata": {}
}
```

Implemented offline evaluators:

- `CitationEvaluator`: checks that major memo claims cite evidence and that referenced evidence IDs exist.
- `EvidenceCoverageEvaluator`: checks that expected source categories appear in the evidence pack.
- `RiskRecallEvaluator`: uses simple keyword matching to compare benchmark findings against memo risk findings.
- `RecommendationEvaluator`: compares expected recommendation and confidence with the memo recommendation.
- `LLMJudgeEvaluator`: explicit stub; skipped unless a future LLM judge client is configured.

## Runtime Reliability

Runtime evaluation answers:

```text
Did the workflow execute correctly?
```

Runtime checks require no benchmark.

Implemented runtime evaluators:

- `RuntimeHealthEvaluator`: checks request, workflow plan, evidence pack, reasoning nodes, and final memo exist.
- `ThresholdEvaluator`: reports retrieval threshold metadata, evidence count, source count, and low-evidence warnings.
- `ReplayEvaluator`: explicit stub for future replay checks.
- `DriftEvaluator`: explicit stub for future baseline comparisons.

Threshold optimization is not implemented in Stage 2. That is reserved for the Stage 3 threshold experiment.

## Online Evaluation

Online evaluation answers:

```text
Did the output create value for users?
```

Online checks are optional and run only when user actions are supplied.

Supported input shape:

```python
{
    "approved": True,
    "edited": False,
    "rejected": False,
    "copied": True,
    "regenerated": False,
    "feedback": "Useful but missed supply chain detail.",
}
```

Implemented online evaluators:

- `HumanReviewEvaluator`: scores approval/edit/rejection signals.
- `FeedbackEvaluator`: captures free-text feedback without NLP.
- `ABTestEvaluator`: explicit stub for future workflow comparison.

## Failure Classification

`evaluation/failure_classifier.py` maps failed checks into simple categories:

```text
retrieval_failure
reasoning_failure
citation_failure
recommendation_failure
execution_failure
online_value_failure
```

The classifier is rule-based. It does not perform ML classification.

## Reports

Evaluation reports are JSON-serializable dataclasses:

```text
EvaluationReport
  run_id
  offline
  runtime
  online
  failures
  summary
```

Reports can be saved with:

```python
from evaluation.report import save_report

path = save_report(report)
```

Generated reports are written to `reports/evaluation_report_<run_id>.json`. The `reports/` directory is ignored by git.

## Demo

Run:

```bash
python examples/evaluate_risk_workflow_demo.py
```

The demo runs the Stage 1 workflow in explicit fixture mode, loads the NVIDIA benchmark, evaluates the completed `WorkflowRun`, prints the report, and saves it under `reports/`.

## Non-Goals

Stage 2 does not:

- rewrite the workflow
- call retrieval or reasoning nodes directly
- implement threshold experiments
- perform semantic LLM judging by default
- introduce a separate evaluation service
