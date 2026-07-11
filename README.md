# Investment Risk Analysis

Investment risk workflow for turning an investment question into a cited risk memo, then evaluating the run artifact.

The workflow follows a controlled, inspectable pipeline:

```text
Investment question
-> request parser
-> workflow planner
-> evidence planner
-> retrieval orchestrator
-> source adapters
-> evidence pack builder
-> reasoning graph
-> memo composer
-> citation verifier
```


## What It Does

- Parses a natural-language investment risk question.
- Retrieves evidence from local documents, trusted URLs, and provider-backed external adapters.
- Supports live URL fetching and provider-backed external search adapters.
- Normalizes all source outputs into `Evidence` objects.
- Builds a compact evidence pack for reasoning.
- Produces a markdown investment risk memo with citations.
- Runs a light citation verifier.
- Captures a serializable `WorkflowRun` artifact for evaluation, replay, and debugging.
- Evaluates completed workflow runs across offline, runtime, and optional online checks.

## Evidence Sources

The retrieval layer uses adapter interfaces so source logic stays out of the reasoning graph:

- `local_documents`: `.txt` and `.md` files under `data/documents/`
- `url_fetcher`: live trusted URL fetch and page/document text extraction
- `web_search`: live provider-backed web search interface; fixture fallback only in explicit fixture/hybrid mode
- `news`: live provider-backed financial news search interface; fixture fallback only in explicit fixture/hybrid mode
- `market_data`: live provider-backed market/macro data interface; fixture fallback only in explicit fixture/hybrid mode
- `sec_filings`: live provider-backed SEC/company filings interface; fixture fallback only in explicit fixture/hybrid mode
- `proprietary`: placeholder adapter for future customer-specific integrations

Fixtures are stored under `data/fixtures/external/` and are intended only for unit tests, offline smoke demos, and deterministic CI. Live search and market/filing adapters require provider implementations; without those providers, live mode returns explicit retrieval-error evidence instead of synthetic snippets.

## Run The CLI

```bash
python -m app.main "Analyze NVIDIA's major downside risks over the next 12 months."
```

Emit structured JSON:

```bash
python -m app.main "Analyze NVIDIA downside risks." --json
```

Use custom evidence directories:

```bash
python -m app.main "Analyze NVIDIA downside risks." \
  --documents-dir data/documents \
  --external-dir data/fixtures/external \
  --retrieval-mode fixture
```

Select retrieval mode with `--retrieval-mode` or `RETRIEVAL_MODE`:

```bash
RETRIEVAL_MODE=live python -m app.main "Analyze NVIDIA downside risks using https://www.sec.gov/"
RETRIEVAL_MODE=fixture python -m app.main "Analyze NVIDIA downside risks."
RETRIEVAL_MODE=hybrid python -m app.main "Analyze NVIDIA downside risks."
```

## Run The Live External Demo

```bash
python examples/live_external_risk_memo_demo.py
```

The demo prints planned external retrieval tasks, normalized source counts, URL/retrieved-at metadata, and then renders the final memo. If no live search providers are configured, the demo fails clearly through retrieval-error evidence unless explicit trusted URLs can be fetched.

## Run Evaluation

Run the evaluation demo:

```bash
python examples/evaluate_risk_workflow_demo.py
```

The demo:

- runs the existing investment risk workflow in explicit fixture mode
- converts the completed `WorkflowRun` into a canonical evaluation artifact
- loads `data/benchmarks/nvidia_risk_case.json`
- runs offline benchmark checks and runtime reliability checks
- skips online checks unless user actions are supplied
- saves a JSON report under `reports/evaluation_report_<run_id>.json`

`reports/` is ignored by git because evaluation reports are generated artifacts.

## Evaluation Layers

The `evaluation/` package is internal and modular; it does not control workflow execution.

- `offline`: benchmark citation coverage, source coverage, risk recall, recommendation match, optional LLM judge stub
- `runtime`: artifact health, retrieval threshold metadata, replay stub, drift stub
- `online`: human review, feedback capture, A/B test stub

All evaluators consume the existing `workflow.pipeline.WorkflowRun` via `to_evaluation_artifact()`.

## Add Local Evidence

Place `.txt` or `.md` files in `data/documents/`. Markdown headings are treated as sections during chunking.

Example:

```markdown
# Risk Factors
Revenue growth may decline if supply constraints or competition pressure demand.

# Liquidity
Strong cash balances may mitigate liquidity risk.
```

## Test

```bash
pytest -q
```

## Project Layout

```text
app/                  CLI entry point
workflow/             parser, planners, reasoning graph, memo composer, verifier
retrieval/            orchestrator, evidence pack builder, reranker
retrieval/adapters/   source adapter implementations
evaluation/           evaluation runners and evaluators
models/               dataclass schemas
tools/                deterministic financial helper functions
data/benchmarks/      offline benchmark cases
data/documents/       local source documents
data/fixtures/        deterministic fixture sources for tests and offline runs
examples/             runnable demos
tests/                smoke and workflow tests
docs/                 design notes
```

## Notes

The reasoning graph receives normalized evidence only. It does not know whether evidence came from local files, fetched URLs, provider-backed search, explicit fixture mode, or future proprietary systems.

Evaluation receives completed workflow artifacts only. It does not call planners, retrieval adapters, or reasoning nodes directly.
