"""
insight agent - generates hypotheses explaining patterns in the data
"""
from typing import Dict, Any, List
from pathlib import Path


class InsightAgent:
    """generates hypotheses and insights from data analysis"""
    
    def __init__(self, llm_client, config: Dict[str, Any]):
        self.llm = llm_client
        self.config = config
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """load insight generation prompt template"""
        prompt_path = Path("prompts/insight_prompt.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        
        # default prompt if file doesn't exist
        return """You are the Insight Agent for a Facebook Ads analysis system.

Your task is to analyze the provided data context and generate hypotheses that explain the observed patterns.

## Analysis Framework
1. Identify notable patterns in the data (trends, outliers, correlations)
2. Generate hypotheses that could explain these patterns
3. Consider multiple factors: creative type, audience, timing, spend levels
4. Prioritize hypotheses by potential business impact

## Hypothesis Categories
- **Performance Drivers**: What factors correlate with high ROAS/CTR?
- **Underperformance Causes**: Why might certain campaigns underperform?
- **Timing Effects**: Are there patterns related to dates or days?
- **Audience Insights**: How do different audiences respond?
- **Creative Effectiveness**: Which creative types/messages work best?

## Output Format
Provide a JSON response with this structure:
{
  "analysis_summary": "Brief overview of the data and key observations",
  "key_observations": [
    "Observation 1 about the data",
    "Observation 2 about the data"
  ],
  "hypotheses": [
    {
      "id": "H1",
      "hypothesis": "Clear statement of the hypothesis",
      "category": "performance_drivers|underperformance|timing|audience|creative",
      "supporting_evidence": "What data points support this hypothesis",
      "testable": true,
      "business_impact": "high|medium|low",
      "recommended_action": "What to do if hypothesis is validated"
    }
  ],
  "data_gaps": ["Any missing data that would improve analysis"]
}

## Guidelines
- Generate 3-7 hypotheses based on the data
- Each hypothesis should be specific and testable
- Focus on actionable insights for marketers
- Consider both positive patterns (what works) and negative patterns (what doesn't)
- Prioritize hypotheses that could lead to meaningful optimizations"""
    
    def generate(
        self, 
        data_context: str, 
        plan: Dict[str, Any],
        user_query: str
    ) -> Dict[str, Any]:
        """
        generate hypotheses and insights from data
        
        args:
            data_context: text summary of dataset from data agent
            plan: execution plan from planner
            user_query: original user query
            
        returns:
            dictionary with hypotheses and insights
        """
        # build the prompt
        prompt = f"""{self.prompt_template}

## User Query
{user_query}

## Analysis Plan
Intent: {plan.get('intent', 'General analysis')}
Focus Areas: {', '.join(plan.get('analysis_scope', {}).get('focus_areas', ['overall performance']))}
Metrics of Interest: {', '.join(plan.get('analysis_scope', {}).get('metrics', ['roas', 'ctr']))}

## Data Context
{data_context}

## Task
Based on the data context above, generate hypotheses that:
1. Explain the observed patterns
2. Address the user's query
3. Provide actionable insights

Think step by step:
1. What are the key patterns in the data?
2. What could explain high-performing vs low-performing segments?
3. What hypotheses can be tested with the available data?
4. What would be the business impact of each hypothesis?

Now provide your analysis in JSON format:"""
        
        try:
            insights = self.llm.generate_json(
                prompt=prompt,
                temperature=0.5  # balanced temperature for creative but coherent insights
            )
            
            # validate response structure
            insights = self._validate_and_enhance(insights)
            
            return insights
            
        except Exception as e:
            print(f"Warning: Insight generation failed ({str(e)}), using fallback")
            return self._fallback_insights(data_context, plan)
    
    def _validate_and_enhance(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """validate and enhance the insights structure"""
        # ensure required keys exist
        if 'hypotheses' not in insights:
            insights['hypotheses'] = []
        
        if 'analysis_summary' not in insights:
            insights['analysis_summary'] = "Analysis completed"
        
        if 'key_observations' not in insights:
            insights['key_observations'] = []
        
        # validate each hypothesis
        for i, hyp in enumerate(insights['hypotheses']):
            if 'id' not in hyp:
                hyp['id'] = f"H{i+1}"
            if 'hypothesis' not in hyp:
                hyp['hypothesis'] = "Unspecified hypothesis"
            if 'category' not in hyp:
                hyp['category'] = "general"
            if 'testable' not in hyp:
                hyp['testable'] = True
            if 'business_impact' not in hyp:
                hyp['business_impact'] = "medium"
        
        return insights
    
    def _fallback_insights(
        self, 
        data_context: str, 
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """generate basic fallback insights if llm fails"""
        return {
            "analysis_summary": "Basic analysis of Facebook Ads performance data",
            "key_observations": [
                "Data loaded successfully for analysis",
                "Multiple campaigns with varying performance levels detected",
                "Different creative types show varied effectiveness"
            ],
            "hypotheses": [
                {
                    "id": "H1",
                    "hypothesis": "Video and UGC creative types may outperform static images in terms of engagement",
                    "category": "creative",
                    "supporting_evidence": "Different creative types show varied CTR and ROAS",
                    "testable": True,
                    "business_impact": "high",
                    "recommended_action": "Compare ROAS and CTR across creative types"
                },
                {
                    "id": "H2", 
                    "hypothesis": "Retargeting audiences likely show higher conversion rates than broad audiences",
                    "category": "audience",
                    "supporting_evidence": "Audience segmentation affects purchase behavior",
                    "testable": True,
                    "business_impact": "high",
                    "recommended_action": "Analyze ROAS by audience type"
                },
                {
                    "id": "H3",
                    "hypothesis": "Campaigns with specific value propositions (discounts, guarantees) may have higher CTR",
                    "category": "creative",
                    "supporting_evidence": "Creative messages vary in their value proposition clarity",
                    "testable": True,
                    "business_impact": "medium",
                    "recommended_action": "Analyze CTR by message type"
                },
                {
                    "id": "H4",
                    "hypothesis": "Weekend performance may differ from weekday performance",
                    "category": "timing",
                    "supporting_evidence": "Time series data available for analysis",
                    "testable": True,
                    "business_impact": "medium",
                    "recommended_action": "Compare weekend vs weekday metrics"
                }
            ],
            "data_gaps": [
                "Frequency/reach data for ad fatigue analysis",
                "A/B test assignment information",
                "Landing page performance data"
            ]
        }
    
    def generate_follow_up_hypotheses(
        self,
        validated_hypotheses: List[Dict[str, Any]],
        data_context: str
    ) -> Dict[str, Any]:
        """
        generate follow-up hypotheses based on validated findings
        
        args:
            validated_hypotheses: list of validated hypotheses from evaluator
            data_context: current data context
            
        returns:
            dictionary with follow-up hypotheses
        """
        high_confidence = [h for h in validated_hypotheses if h.get('confidence', 0) >= 0.7]
        
        if not high_confidence:
            return {"follow_up_hypotheses": [], "message": "No high-confidence findings to build upon"}
        
        prompt = f"""Based on the following validated insights, generate follow-up hypotheses for deeper analysis:

## Validated Findings
{self._format_hypotheses(high_confidence)}

## Available Data
{data_context[:2000]}  # truncate for token efficiency

Generate 2-3 follow-up hypotheses that:
1. Build on the validated findings
2. Explore related patterns
3. Could lead to additional optimization opportunities

Respond in JSON format:
{{
  "follow_up_hypotheses": [
    {{
      "id": "F1",
      "builds_on": "original hypothesis ID",
      "hypothesis": "follow-up hypothesis statement",
      "rationale": "why this follow-up is valuable"
    }}
  ]
}}"""
        
        try:
            return self.llm.generate_json(prompt=prompt, temperature=0.6)
        except Exception:
            return {"follow_up_hypotheses": [], "message": "Follow-up generation skipped"}
    
    def _format_hypotheses(self, hypotheses: List[Dict[str, Any]]) -> str:
        """format hypotheses list for prompt"""
        formatted = []
        for h in hypotheses:
            formatted.append(f"- {h.get('id', 'H?')}: {h.get('hypothesis', h.get('original_hypothesis', 'Unknown'))}")
            if 'confidence' in h:
                formatted.append(f"  Confidence: {h['confidence']:.0%}")
        return "\n".join(formatted)
