# Agent Graph Documentation

This document describes the multi-agent architecture, agent roles, and data flow of the Kasparro Agentic Facebook Performance Analyst.

## Architecture Diagram

```
                                    +-------------------+
                                    |   User Query      |
                                    +--------+----------+
                                             |
                                             v
+--------------------------------------------------------------------------------+
|                              AGENT ORCHESTRATOR                                 |
|                                                                                 |
|   +-------------------+                                                         |
|   |  1. PLANNER       |  Decomposes query into tasks                           |
|   |     AGENT         |  Determines analysis scope & metrics                   |
|   +--------+----------+                                                         |
|            |                                                                    |
|            v                                                                    |
|   +-------------------+     +-------------------+                               |
|   |  2. DATA          |---->|   DataLoader      |                               |
|   |     AGENT         |     |   (Utility)       |                               |
|   +--------+----------+     +-------------------+                               |
|            |                                                                    |
|            v                                                                    |
|   +-------------------+                                                         |
|   |  3. INSIGHT       |  Generates hypotheses from data patterns               |
|   |     AGENT         |  Uses LLM for pattern recognition                      |
|   +--------+----------+                                                         |
|            |                                                                    |
|            v                                                                    |
|   +-------------------+                                                         |
|   |  4. EVALUATOR     |  Validates hypotheses with statistical tests           |
|   |     AGENT         |  ANOVA, T-tests, correlation analysis                  |
|   +--------+----------+                                                         |
|            |                                                                    |
|            v (conditional)                                                      |
|   +-------------------+                                                         |
|   |  5. CREATIVE      |  Generates new ad copy recommendations                 |
|   |     GENERATOR     |  Only runs if required by plan                         |
|   +--------+----------+                                                         |
|            |                                                                    |
|            v                                                                    |
|   +-------------------+                                                         |
|   |  REPORT           |  Compiles findings into markdown report                |
|   |  GENERATOR        |                                                         |
|   +-------------------+                                                         |
|                                                                                 |
+--------------------------------------------------------------------------------+
                                             |
                                             v
                              +-----------------------------+
                              |   OUTPUTS                   |
                              |   - reports/report.md       |
                              |   - reports/insights.json   |
                              |   - reports/creatives.json  |
                              |   - logs/*.json             |
                              +-----------------------------+
```

## Agent Roles

### 1. Planner Agent (`src/agents/planner.py`)

**Purpose:** Decomposes user queries into structured execution plans.

**Input:**

- User query (natural language)

**Output:**

- Execution plan with intent, analysis scope, tasks, and flags

**Responsibilities:**

- Parse user intent (ROAS analysis, creative optimization, trend detection)
- Determine relevant metrics (ROAS, CTR, spend, purchases)
- Identify required breakdowns (by campaign, creative type, audience)
- Decide if creative generation is needed
- Create ordered task list for other agents

**Prompt:** `prompts/planner.md`

---

### 2. Data Agent (`src/agents/data_agent.py`)

**Purpose:** Loads and summarizes the Facebook Ads dataset.

**Input:**

- Execution plan from Planner

**Output:**

- Dataset summary, campaign performance, metrics by breakdown

**Responsibilities:**

- Load CSV data via DataLoader utility
- Compute summary statistics (total spend, revenue, ROAS, CTR)
- Generate performance breakdowns by campaign, creative type, audience
- Prepare context string for LLM consumption
- Detect anomalies in metrics

**Dependencies:** `src/utils/data_loader.py`

---

### 3. Insight Agent (`src/agents/insight_agent.py`)

**Purpose:** Generates hypotheses explaining patterns in the data.

**Input:**

- Data context (text summary)
- Execution plan
- Original user query

**Output:**

- List of hypotheses with categories, evidence, and business impact

**Responsibilities:**

- Identify patterns (trends, outliers, correlations)
- Generate testable hypotheses
- Categorize insights (creative, audience, timing, performance)
- Prioritize by business impact
- Suggest recommended actions

**Prompt:** `prompts/insight.md`

---

### 4. Evaluator Agent (`src/agents/evaluator.py`)

**Purpose:** Validates hypotheses with quantitative statistical evidence.

**Input:**

- List of hypotheses from Insight Agent

**Output:**

- Validated hypotheses with confidence scores and statistical evidence

**Responsibilities:**

- Route hypotheses to appropriate validation methods
- Perform ANOVA tests for creative/audience comparisons
- Conduct T-tests for timing analysis (weekend vs weekday)
- Calculate correlation analysis for performance drivers
- Assign confidence scores based on statistical significance
- Generate conclusions and recommendations

**Statistical Methods:**

- ANOVA (Analysis of Variance)
- Independent T-tests
- Pearson correlation
- IQR-based anomaly detection

**Prompt:** `prompts/evaluator.md`

---

### 5. Creative Generator Agent (`src/agents/creative_generator.py`)

**Purpose:** Generates new creative recommendations for low-performing ads.

**Input:**

- Execution plan (checks `requires_creative_generation` flag)

**Output:**

- Creative recommendations with new headlines, body copy, and CTAs

**Responsibilities:**

- Identify low-CTR campaigns below threshold
- Analyze high-performing creative messages for patterns
- Generate 2-3 creative variations per low performer
- Apply success patterns from top performers
- Provide reasoning for each recommendation

**Prompt:** `prompts/creative.md`

**Conditional Execution:** Only runs when plan indicates creative generation is needed.

---

## Data Flow

### Step-by-Step Flow

1. **User Input** -> User provides natural language query
2. **Planning** -> Planner Agent creates execution plan
3. **Data Loading** -> Data Agent loads and summarizes dataset
4. **Insight Generation** -> Insight Agent generates hypotheses from data
5. **Validation** -> Evaluator Agent validates hypotheses statistically
6. **Creative Generation** -> (Optional) Creative Generator creates ad recommendations
7. **Report Generation** -> Orchestrator compiles final markdown report
8. **Output** -> Results saved to reports/ and logs/ directories

### Data Transformations

```
User Query (string)
       |
       v
Execution Plan (dict)
  - intent
  - analysis_scope
  - tasks[]
  - requires_creative_generation
       |
       v
Data Context (dict + string)
  - summary stats
  - campaign performance
  - breakdowns
       |
       v
Hypotheses (list[dict])
  - id, hypothesis, category
  - supporting_evidence
  - business_impact
       |
       v
Validated Hypotheses (list[dict])
  - confidence score
  - statistical_tests
  - quantitative_evidence
  - conclusion
       |
       v
Creative Recommendations (dict)
  - success_patterns
  - recommendations[]
       |
       v
Final Report (markdown string)
```

## Utility Components

### LLM Client (`src/utils/llm_client.py`)

- Handles communication with Ollama API
- Supports text and JSON generation modes
- Health check for model availability

### Data Loader (`src/utils/data_loader.py`)

- CSV loading and preprocessing
- Date parsing and normalization
- Campaign name standardization
- Performance aggregations by dimensions
- Anomaly detection

## Logging

Each agent execution is logged to `logs/` as JSON files:

- Individual agent logs: `{agent_name}_{timestamp}.json`
- Execution summary: `execution_summary_{timestamp}.json`

Log contents include:

- Agent name
- Timestamp
- Duration
- Success/failure status
- Full result data

## Configuration

Agent behavior is controlled via `config/config.yaml`:

- LLM settings (model, temperature, max_tokens)
- Data path
- Thresholds (low_ctr, low_roas, confidence)
- Output directories
