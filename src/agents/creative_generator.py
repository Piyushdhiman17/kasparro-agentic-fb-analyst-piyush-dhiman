"""
creative generator agent - produces new creative recommendations
"""
from typing import Dict, Any, List
import pandas as pd
from pathlib import Path


class CreativeGeneratorAgent:
    """generates creative recommendations for low-performing campaigns"""
    
    def __init__(self, llm_client, data_loader, config: Dict[str, Any]):
        self.llm = llm_client
        self.loader = data_loader
        self.config = config
        self.low_ctr_threshold = config['thresholds']['low_ctr']
        self.df = None  # will be loaded lazily
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """load creative generator prompt template from markdown file"""
        prompt_path = Path("prompts/creative.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    def generate(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        generate creative recommendations for low-ctr campaigns
        
        args:
            plan: execution plan (checks if creative generation needed)
            
        returns:
            dictionary of creative recommendations
        """
        # check if creative generation is required
        if not plan.get('requires_creative_generation', False):
            return {
                "message": "Creative generation not required for this query",
                "recommendations": []
            }
        
        # ensure data is loaded
        if self.df is None:
            self.df = self.loader.load_data()
        
        # identify low-ctr campaigns
        low_ctr_data = self.loader.get_low_ctr_campaigns(self.low_ctr_threshold)
        
        if len(low_ctr_data) == 0:
            return {
                "message": f"No campaigns found with CTR below {self.low_ctr_threshold}",
                "recommendations": []
            }
        
        # analyze high-performing creative messages
        high_performing = self.df[self.df['ctr'] >= self.low_ctr_threshold * 1.5]
        
        # extract creative messages
        high_perf_messages = high_performing['creative_message'].tolist()
        low_perf_messages = low_ctr_data['creative_message'].tolist()
        
        # generate recommendations using llm
        recommendations = self._generate_recommendations_llm(
            low_ctr_data,
            high_perf_messages,
            low_perf_messages
        )
        
        return {
            "message": f"Generated creative recommendations for {len(low_ctr_data)} low-CTR ads",
            "low_ctr_threshold": self.low_ctr_threshold,
            "recommendations": recommendations
        }
    
    def _generate_recommendations_llm(
        self, 
        low_ctr_data: pd.DataFrame,
        high_perf_messages: List[str],
        low_perf_messages: List[str]
    ) -> List[Dict[str, Any]]:
        """use llm to generate creative recommendations"""
        
        # prepare context for llm
        high_perf_sample = high_perf_messages[:5]  # sample to avoid token limits
        low_perf_sample = low_perf_messages[:5]
        
        prompt = f"""{self.prompt_template}

## High-Performing Ad Messages (CTR > {self.low_ctr_threshold * 1.5:.4f})
{chr(10).join(f"{i+1}. {msg}" for i, msg in enumerate(high_perf_sample))}

## Low-Performing Ad Messages (CTR < {self.low_ctr_threshold:.4f})
{chr(10).join(f"{i+1}. {msg}" for i, msg in enumerate(low_perf_sample))}

Generate 2-3 creative variations for each low-performing message. Be specific and actionable.
"""
        
        try:
            result = self.llm.generate_json(
                prompt=prompt,
                temperature=0.8  # higher temperature for creative diversity
            )
            
            # validate and enhance recommendations
            recommendations = result.get('recommendations', [])
            
            # add current campaign info
            for i, rec in enumerate(recommendations):
                if i < len(low_ctr_data):
                    row = low_ctr_data.iloc[i]
                    rec['campaign_name'] = row['campaign_name']
                    rec['date'] = row['date'].strftime('%Y-%m-%d')
                    rec['creative_type'] = row['creative_type']
            
            return recommendations
            
        except Exception as e:
            print(f"Warning: Creative generation failed ({str(e)}), using fallback")
            return self._fallback_recommendations(low_ctr_data)
    
    def _fallback_recommendations(self, low_ctr_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """generate basic recommendations if llm fails"""
        recommendations = []
        
        for _, row in low_ctr_data.iterrows():
            recommendations.append({
                "campaign_name": row['campaign_name'],
                "date": row['date'].strftime('%Y-%m-%d'),
                "original_message": row['creative_message'],
                "current_ctr": float(row['ctr']),
                "creative_type": row['creative_type'],
                "new_creatives": [
                    {
                        "headline": "Limited Time: Premium Comfort at 30% Off",
                        "body": "Experience the difference with breathable, high-performance fabric",
                        "cta": "Shop Now & Save",
                        "reasoning": "Add urgency and discount to improve CTR",
                        "pattern_applied": "Scarcity + Value"
                    },
                    {
                        "headline": "100% Satisfaction Guaranteed",
                        "body": "Join thousands who've made the switch to superior comfort",
                        "cta": "Try Risk-Free",
                        "reasoning": "Reduce purchase anxiety with guarantee",
                        "pattern_applied": "Social Proof + Risk Reversal"
                    }
                ]
            })
        
        return recommendations