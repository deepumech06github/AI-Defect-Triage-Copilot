# AI-Defect-Triage-Copilot

An explainable, offline-first defect triage portfolio project for quality engineering leaders. It turns bug reports into suggested **severity**, **priority**, **owner team**, confidence, evidence signals, and recommended next actions. It also checks reproduction detail and surfaces possible duplicates from a sample incident set. Optional OpenAI mode is available; every result is advisory and requires human review.

## What it demonstrates

- Separating defect severity (impact) from priority (urgency)
- Explainable rules and confidence indicators for triage recommendations
- Reproduction completeness checks that improve defect intake quality
- Lightweight duplicate suggestions for backlog hygiene
- Single issue and CSV batch triage through a Streamlit dashboard
- JSON and CSV handoff, unit tests, and GitHub Actions CI

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
streamlit run app.py
```

The offline engine works without credentials or network calls. The prefilled example is a checkout timeout. Try changing the title, customer impact, or reproduction details to see how the triage changes.

## Optional OpenAI mode

Install the optional SDK and set `OPENAI_API_KEY` in your environment or Streamlit secrets. The LLM receives defect information, so use only content permitted by your organization's data policy.

```bash
pip install -e ".[llm]"
# macOS / Linux:
export OPENAI_API_KEY="your-key"
# Windows PowerShell:
$env:OPENAI_API_KEY = "your-key"
streamlit run app.py
```

You may set `OPENAI_MODEL` to a compatible chat-completions model. Never commit a real API key.

## Batch triage CSV

Upload a CSV with these required headers:

```csv
title,description,component,customer_impact,environment
Checkout timeout,Checkout fails after authorization,Payments,Multiple production customers,Production
```

`title` and `description` are required. Other columns are optional. Batch mode uses offline rules and exports all recommendations to CSV or JSON.

## Run unit tests

```bash
python -m pip install -e ".[dev]"
pytest
```

## Upload to GitHub

1. Extract the project ZIP.
2. Create a repository named `AI-Defect-Triage-Copilot`.
3. Upload the extracted folder contents, including `.github/workflows/ci.yml`.
4. Commit with a message such as `Add AI defect triage copilot`.

## Repository map

```text
app.py                              Streamlit dashboard
src/defect_triage/triage.py         Offline severity, priority, and duplicate logic
src/defect_triage/llm.py            Optional OpenAI recommendations
src/defect_triage/models.py         Input and result models
src/defect_triage/exports.py        JSON and CSV outputs
tests/                              Unit tests
examples/sample_defects.csv         Fictional demo incidents
docs/architecture.md               Architecture and production considerations
.github/workflows/ci.yml            GitHub Actions checks
```

## Important limitations

This is a portfolio demo, not an autonomous ticketing system. The offline rules are transparent heuristics and may not fit every product. Similarity uses simple text overlap on a small sample list. LLM results can be wrong or incomplete. Have the owning team validate severity, priority, security impact, and duplicate decisions before acting.

## License

MIT. See [LICENSE](LICENSE).

