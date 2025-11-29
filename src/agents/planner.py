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
        """load planner prompt template from markdown file"""
        prompt_path = Path("prompts/planner.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
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