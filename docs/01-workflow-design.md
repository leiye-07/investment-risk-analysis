# Investment Risk Workflow

This implementation follows the supplied Stage 1 design:

Investment question -> evidence plan -> retrieval -> structured reasoning -> cited risk memo.

Stage 1 intentionally excludes benchmarking, failure scoring, threshold experiments, and human-review metrics.

## Execution Flow

1. Parse the user request into `InvestmentRequest`.
2. Create a bounded workflow plan.
3. Map workflow steps to required evidence sources.
4. Retrieve local `.txt` and `.md` documents from `data/documents`.
5. Build a deduplicated evidence pack.
6. Run the reasoning graph node by node.
7. Compose the markdown risk memo.
8. Verify that major claims cite valid evidence.

## Run

```bash
python -m app.main "Analyze NVIDIA's major downside risks over the next 12 months."
```

Add source documents to `data/documents` for company-specific analysis. Without documents, the workflow emits a retrieval-gap memo with low confidence rather than inventing evidence.
