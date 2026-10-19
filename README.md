# RAG: Baseline Retrieval vs. Cross-Encoder Re-Ranking

Two-stage RAG over the GDPR: bi-encoder retrieval (BGE) vs. cross-encoder re-ranking, with failure-mode tests, rank shifts, latency profiling and every LLM prompt and response logged.

- **Pipeline 1:** `BAAI/bge-base-en-v1.5` retrieves the top 10 chunks by cosine similarity; the top 3 go to the LLM.
- **Pipeline 2:** `BAAI/bge-reranker-base` re-scores those 10 chunks; the new top 3 go to the LLM with the same prompt.
- **LLM:** `google/gemini-2.5-flash-lite` via OpenRouter, temperature 0.

## Files

| File | What it is |
|---|---|
| `rag_baseline_vs_reranking.ipynb` | The full experiment, with outputs from the final run |
| `EVALUATION_REPORT.md` | The report (architecture, rank shifts, answer comparison, latency, scaling) |
| `llm_prompts_and_responses.md` / `.json` | Exact prompt and raw response of every LLM call |
| `rank_shift_table.csv`, `latency_table.csv`, `evaluation_results.json` | Raw results |
| `GDPR.pdf` | The document used |
| `setup_api_key.py` | Stores the OpenRouter API key in encrypted form |

## Running it

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python setup_api_key.py        # paste your OpenRouter key (hidden input)
jupyter notebook rag_baseline_vs_reranking.ipynb
```

Runs on CPU; a GPU is optional. The models are downloaded from Hugging Face on the first run.
