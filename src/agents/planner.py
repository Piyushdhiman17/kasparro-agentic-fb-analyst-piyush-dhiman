"""
planner agent - decomposes user queries into executable subtasks
"""
from typing import Dict, Any
from pathlib import Path


class PlannerAgent:
    """decomposes user query into structured execution plan"""
    
    def __init__(self, llm_client, config: Dict[str, Any]):
        self.llm = llm_client
        self.config = config
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """load planner prompt template"""
        prompt_path = Path("prompts/planner_prompt.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        
        # default prompt if file doesn't exist
        return """You are the Planner Agent for a Facebook Ads analysis system.

Your task is to analyze the user's query and create a structured execution plan.

## Analysis Framework
Think through these questions:
1. What is the primary intent? (ROAS analysis, creative optimization, trend detection, etc.)
2. What time period is relevant? (specific dates, recent period, overall)
3. What metrics need to be examined? (ROAS, CTR, spend, purchases, etc.)
4. What breakdowns are needed? (by campaign, creative type, audience, date)
5. Should creative recommendations be generated?

## Output Format
Provide a JSON response with this structure:
{
  "intent": "brief description of what user wants",
  "analysis_scope": {
    "metrics": ["list", "of", "metrics"],
    "time_period": "date range or 'all'",
    "breakdowns": ["campaign", "creative_type", etc.],
    "focus_areas": ["specific aspects to investigate"]
  },
  "tasks": [
    "Task 1: Load and summarize data",
    "Task 2: Specific analysis task",
    "Task 3: Generate insights",
    "Task 4: Validate findings",
    "Task 5: Create recommendations (if applicable)"
  ],
  "requires_creative_generation": true/false,
  "reasoning": "explain your planning decisions"
}

## Guidelines
- Be specific about what data needs to be analyzed
- Order tasks logically (data → analysis → insights → validation → recommendations)
- Always include data loading and insight validation tasks
- Only include creative generation if user asks about improving ads or mentions low performance
- Keep tasks actionable and clear"""
    
    def plan(self, user_query: str) -> Dict[str, Any]:
        """
        decompose user query into execution plan
        
        args:
            user_query: natural language query from user
            
        returns:
            structured plan dictionary
        """
        prompt = f"""{self.prompt_template}

## User Query
{user_query}

Think step by step:
1. What is the user asking for?
2. What data and metrics are needed?
3. What analysis tasks are required?
4. Should creative recommendations be generated?

Now provide your execution plan in JSON format:"""
        
        try:
            plan = self.llm.generate_json(
                prompt=prompt,
                temperature=0.3  # lower temperature for more consistent planning
            )
            
            # validate plan structure
            required_keys = ['intent', 'tasks', 'analysis_scope']
            if not all(key in plan for key in required_keys):
                raise ValueError(f"Plan missing required keys: {required_keys}")
            
            # ensure tasks is a list
            if not isinstance(plan['tasks'], list) or len(plan['tasks']) == 0:
                raise ValueError("Plan must contain a non-empty list of tasks")
            
            return plan
            
        except Exception as e:
            # fallback plan if llm fails
            print(f"Warning: Planner LLM failed ({str(e)}), using fallback plan")
            return self._fallback_plan(user_query)
    
    def _fallback_plan(self, user_query: str) -> Dict[str, Any]:
        """create a basic fallback plan if llm fails"""
        return {
            "intent": f"Analyze: {user_query}",
            "analysis_scope": {
                "metrics": ["roas", "ctr", "spend"],
                "time_period": "all",
                "breakdowns": ["campaign", "date"],
                "focus_areas": ["performance_trends"]
            },
            "tasks": [
                "Load Facebook Ads dataset",
                "Compute summary statistics and trends",
                "Identify performance patterns",
                "Generate hypotheses about changes",
                "Validate hypotheses with data",
                "Create summary report"
            ],
            "requires_creative_generation": "low ctr" in user_query.lower() or "creative" in user_query.lower(),
            "reasoning": "Fallback plan due to LLM error"
        }