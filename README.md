Folder highlights
Project documents detail an Agentic Facebook Performance Analyst assignment, including a synthetic ads CSV and a quick start guide for a system diagnosing ROAS fluctuation.

# Kasparro — Agentic Facebook Performance Analyst

## Quick Start

```bash
python -V  # should be >= 3.10
python -m venv .venv && source .venv/bin/activate  # win: .venv\Scripts\activate
pip install -r requirements.txt
python src/run.py "Analyze ROAS drop in last 7 days"
```

## Data

- Place the full CSV locally and set `DATA_CSV=/path/to/synthetic_fb_ads_undergarments.csv`
- Or copy a small sample to `data/sample_fb_ads.csv`.
- See `data/README.md` for details.

## Config

Edit `config/config.yaml`:

```yaml
python: "3.10"
random_seed: 42
confidence_min: 0.6
use_sample_data: true
```

## Repo Map

- `src/agents/` — planner.py, data_agent.py, insight_agent.py, evaluator.py, creative_generator.py
- `prompts/` — \*.md prompt files with variable placeholders
- `reports/` — report.md, insights.json, creatives.json
- `logs/` — json traces
- `tests/` — test_evaluator.py

## Run

```bash
make run  # or: python src/run.py "Analyze ROAS drop"
```

## Outputs

- `reports/report.md`
- `reports/insights.json`
- `reports/creatives.json`

## Observability

- Include Langfuse screenshots or JSON logs in `reports/observability/`.

## Release

- Tag: `v1.0` and paste link here.

## Self-Review

- Link to PR describing design choices & tradeoffs.
