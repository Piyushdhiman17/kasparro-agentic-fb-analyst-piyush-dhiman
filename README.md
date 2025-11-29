Folder highlights
Project documents detail an Agentic Facebook Performance Analyst assignment, including a synthetic ads CSV and a quick start guide for a system diagnosing ROAS fluctuation.

# Kasparro - Agentic Facebook Performance Analyst

A multi-agent system for analyzing Facebook Ads performance data, generating insights, validating hypotheses with statistical methods, and recommending creative improvements.

## Quick Start

```bash
python -V  # should be >= 3.9
python -m venv .venv && source .venv/bin/activate  # win: .venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen3:4b  # ensure model is available
python run.py "Analyze ROAS performance"
```

## Architecture

See [agent_graph.md](agent_graph.md) for detailed architecture documentation including:

- Agent roles and responsibilities
- Data flow diagrams
- Statistical methods used

### Agents

| Agent              | Role                                                         |
| ------------------ | ------------------------------------------------------------ |
| Planner            | Decomposes user queries into execution plans                 |
| Data Agent         | Loads and summarizes Facebook Ads dataset                    |
| Insight Agent      | Generates hypotheses from data patterns                      |
| Evaluator          | Validates hypotheses with statistical tests (ANOVA, T-tests) |
| Creative Generator | Recommends new ad copy for low performers                    |

## Data

- `data/dataset.csv` - Sample dataset (5 entries) for testing
- `data/dataset_full.csv` - Full dataset for production
- See `data/README.md` for CSV format specification

## Config

Edit `config/config.yaml`:

```yaml
llm:
  model: "qwen3:4b"
  base_url: "http://localhost:11434"
  temperature: 0.7

data:
  path: "data/dataset_full.csv"

thresholds:
  low_ctr: 0.015
  low_roas: 3.0
  confidence_threshold: 0.6
```

## Repo Structure

```
fb/
  run.py                    # main entry point
  agent_graph.md            # architecture documentation
  config/
    config.yaml             # configuration
  data/
    dataset.csv             # sample data (5 entries)
    dataset_full.csv        # full dataset
    README.md               # csv format spec
  src/
    agents/
      planner.py            # query decomposition
      data_agent.py         # data loading & summary
      insight_agent.py      # hypothesis generation
      evaluator.py          # statistical validation
      creative_generator.py # ad copy recommendations
    orchestrator/
      agent_graph.py        # workflow coordination
    utils/
      llm_client.py         # ollama api client
      data_loader.py        # csv processing
  prompts/
    planner.md              # planner prompt template
    insight.md              # insight prompt template
    evaluator.md            # evaluator prompt template
    creative.md             # creative prompt template
  reports/                  # generated outputs
    report.md
    insights.json
    creatives.json
  logs/                     # execution logs (json)
  tests/
    test_evaluator.py       # evaluator unit tests
```

## Run

```bash
# activate virtual environment
source .venv/bin/activate

# run analysis
python run.py "Analyze ROAS performance"
python run.py "Why did CTR drop? Generate new creatives"
python run.py "Compare video vs image creative performance"

# run tests
python -m pytest tests/ -v
```

## Outputs

After running, find results in `reports/`:

| File             | Description                                 |
| ---------------- | ------------------------------------------- |
| `report.md`      | Markdown analysis report                    |
| `insights.json`  | Validated hypotheses with confidence scores |
| `creatives.json` | Creative recommendations (if generated)     |

## Logging

Execution logs are saved to `logs/` as JSON files:

- Individual agent execution logs
- Complete execution summary with timing

## Requirements

- Python >= 3.9
- Ollama with qwen3:4b model
- Dependencies in requirements.txt (pandas, numpy, scipy, pyyaml, requests)
