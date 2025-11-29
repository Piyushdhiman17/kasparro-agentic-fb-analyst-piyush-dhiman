"""
evaluator agent - validates hypotheses quantitatively using statistical analysis
"""
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path


class EvaluatorAgent:
    """validates hypotheses with quantitative evidence"""
    
    def __init__(self, llm_client, data_loader, config: Dict[str, Any]):
        self.llm = llm_client
        self.loader = data_loader
        self.config = config
        self.confidence_threshold = config['thresholds'].get('confidence_threshold', 0.6)
        self.df = None
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """load evaluator prompt template from markdown file"""
        prompt_path = Path("prompts/evaluator.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    def validate(self, hypotheses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        validate hypotheses with quantitative evidence
        
        args:
            hypotheses: list of hypotheses from insight agent
            
        returns:
            dictionary with validation results
        """
        # ensure data is loaded
        if self.df is None:
            self.df = self.loader.load_data()
        
        validated_hypotheses = []
        
        for hypothesis in hypotheses:
            validation_result = self._validate_single_hypothesis(hypothesis)
            validated_hypotheses.append(validation_result)
        
        # calculate validation summary
        high_confidence = sum(1 for h in validated_hypotheses if h['confidence'] >= 0.7)
        medium_confidence = sum(1 for h in validated_hypotheses if 0.5 <= h['confidence'] < 0.7)
        low_confidence = sum(1 for h in validated_hypotheses if h['confidence'] < 0.5)
        
        return {
            "validated_hypotheses": validated_hypotheses,
            "validation_summary": f"{high_confidence} high, {medium_confidence} medium, {low_confidence} low confidence",
            "total_validated": len(validated_hypotheses),
            "high_confidence_count": high_confidence,
            "medium_confidence_count": medium_confidence,
            "low_confidence_count": low_confidence
        }
    
    def _validate_single_hypothesis(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """
        validate a single hypothesis
        
        args:
            hypothesis: hypothesis dictionary from insight agent
            
        returns:
            validation result dictionary
        """
        category = hypothesis.get('category', 'general').lower()
        hypothesis_text = hypothesis.get('hypothesis', '')
        
        # route to appropriate validation method based on category
        if category == 'creative':
            validation = self._validate_creative_hypothesis(hypothesis_text)
        elif category == 'audience':
            validation = self._validate_audience_hypothesis(hypothesis_text)
        elif category == 'timing':
            validation = self._validate_timing_hypothesis(hypothesis_text)
        elif category == 'performance_drivers' or category == 'underperformance':
            validation = self._validate_performance_hypothesis(hypothesis_text)
        else:
            validation = self._validate_general_hypothesis(hypothesis_text)
        
        return {
            "original_hypothesis": hypothesis_text,
            "hypothesis_id": hypothesis.get('id', 'H?'),
            "category": category,
            "confidence": validation['confidence'],
            "validation_method": validation['method'],
            "quantitative_evidence": validation['evidence'],
            "statistical_tests": validation.get('statistical_tests', {}),
            "conclusion": validation['conclusion'],
            "recommendation": validation.get('recommendation', '')
        }
    
    def _validate_creative_hypothesis(self, hypothesis: str) -> Dict[str, Any]:
        """validate hypotheses about creative performance"""
        creative_perf = self.loader.get_creative_performance()
        
        # calculate statistics by creative type
        creative_stats = {}
        for creative_type, perf_stats in creative_perf.items():
            creative_stats[creative_type] = {
                'avg_roas': perf_stats['avg_roas'],
                'avg_ctr': perf_stats['avg_ctr'],
                'count': perf_stats['count']
            }
        
        # perform statistical comparison
        roas_values = {ct: self.df[self.df['creative_type'] == ct]['roas'].values 
                      for ct in self.df['creative_type'].unique()}
        
        # anova test if we have multiple groups
        groups = [v for v in roas_values.values() if len(v) > 1]
        
        if len(groups) >= 2:
            try:
                f_stat, p_value = stats.f_oneway(*groups)
                statistical_significance = p_value < 0.05
            except Exception:
                f_stat, p_value = 0, 1
                statistical_significance = False
        else:
            f_stat, p_value = 0, 1
            statistical_significance = False
        
        # find best and worst performers
        sorted_by_roas = sorted(creative_stats.items(), key=lambda x: x[1]['avg_roas'], reverse=True)
        best_creative = sorted_by_roas[0] if sorted_by_roas else (None, {})
        worst_creative = sorted_by_roas[-1] if sorted_by_roas else (None, {})
        
        # calculate confidence based on statistical evidence
        confidence = 0.5
        if statistical_significance:
            confidence += 0.2
        
        # check if specific creative types mentioned in hypothesis are validated
        hypothesis_lower = hypothesis.lower()
        if 'video' in hypothesis_lower or 'ugc' in hypothesis_lower:
            video_roas = creative_stats.get('Video', {}).get('avg_roas', 0)
            ugc_roas = creative_stats.get('UGC', {}).get('avg_roas', 0)
            image_roas = creative_stats.get('Image', {}).get('avg_roas', 0)
            
            if video_roas > image_roas or ugc_roas > image_roas:
                confidence += 0.2
        
        # additional confidence from effect size
        if best_creative[1] and worst_creative[1]:
            roas_diff = best_creative[1].get('avg_roas', 0) - worst_creative[1].get('avg_roas', 0)
            if roas_diff > 2:  # meaningful difference
                confidence += 0.1
        
        confidence = min(confidence, 0.95)
        
        return {
            'confidence': confidence,
            'method': 'Creative type ANOVA comparison',
            'evidence': creative_stats,
            'statistical_tests': {
                'anova_f_statistic': float(f_stat) if not np.isnan(f_stat) else 0,
                'p_value': float(p_value) if not np.isnan(p_value) else 1,
                'significant': statistical_significance
            },
            'conclusion': f"Best: {best_creative[0]} (ROAS: {best_creative[1].get('avg_roas', 0):.2f}), "
                         f"Worst: {worst_creative[0]} (ROAS: {worst_creative[1].get('avg_roas', 0):.2f})",
            'recommendation': f"Consider increasing budget allocation to {best_creative[0]} creative type"
        }
    
    def _validate_audience_hypothesis(self, hypothesis: str) -> Dict[str, Any]:
        """validate hypotheses about audience performance"""
        audience_perf = self.loader.get_audience_performance()
        
        audience_stats = {}
        for audience_type, perf_stats in audience_perf.items():
            audience_stats[audience_type] = {
                'avg_roas': perf_stats['avg_roas'],
                'avg_ctr': perf_stats['avg_ctr'],
                'count': perf_stats['count']
            }
        
        # statistical comparison
        roas_values = {at: self.df[self.df['audience_type'] == at]['roas'].values 
                      for at in self.df['audience_type'].unique()}
        
        groups = [v for v in roas_values.values() if len(v) > 1]
        
        if len(groups) >= 2:
            try:
                f_stat, p_value = stats.f_oneway(*groups)
                statistical_significance = p_value < 0.05
            except Exception:
                f_stat, p_value = 0, 1
                statistical_significance = False
        else:
            f_stat, p_value = 0, 1
            statistical_significance = False
        
        # find best audience
        sorted_by_roas = sorted(audience_stats.items(), key=lambda x: x[1]['avg_roas'], reverse=True)
        best_audience = sorted_by_roas[0] if sorted_by_roas else (None, {})
        
        # calculate confidence
        confidence = 0.5
        if statistical_significance:
            confidence += 0.25
        
        # check retargeting performance
        hypothesis_lower = hypothesis.lower()
        if 'retarget' in hypothesis_lower:
            retarget_roas = audience_stats.get('Retargeting', {}).get('avg_roas', 0)
            broad_roas = audience_stats.get('Broad', {}).get('avg_roas', 0)
            if retarget_roas > broad_roas:
                confidence += 0.15
        
        confidence = min(confidence, 0.95)
        
        return {
            'confidence': confidence,
            'method': 'Audience type ANOVA comparison',
            'evidence': audience_stats,
            'statistical_tests': {
                'anova_f_statistic': float(f_stat) if not np.isnan(f_stat) else 0,
                'p_value': float(p_value) if not np.isnan(p_value) else 1,
                'significant': statistical_significance
            },
            'conclusion': f"Best performing audience: {best_audience[0]} "
                         f"(ROAS: {best_audience[1].get('avg_roas', 0):.2f})",
            'recommendation': f"Focus more budget on {best_audience[0]} audience segments"
        }
    
    def _validate_timing_hypothesis(self, hypothesis: str) -> Dict[str, Any]:
        """validate hypotheses about timing patterns"""
        # add day of week analysis
        df = self.df.copy()
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6])
        
        # compare weekend vs weekday
        weekend_roas = df[df['is_weekend']]['roas'].mean()
        weekday_roas = df[~df['is_weekend']]['roas'].mean()
        
        weekend_ctr = df[df['is_weekend']]['ctr'].mean()
        weekday_ctr = df[~df['is_weekend']]['ctr'].mean()
        
        # t-test for weekend vs weekday
        weekend_values = df[df['is_weekend']]['roas'].values
        weekday_values = df[~df['is_weekend']]['roas'].values
        
        try:
            t_stat, p_value = stats.ttest_ind(weekend_values, weekday_values)
            statistical_significance = p_value < 0.05
        except Exception:
            t_stat, p_value = 0, 1
            statistical_significance = False
        
        # daily performance
        daily_roas = df.groupby('day_of_week')['roas'].mean().to_dict()
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        daily_roas_named = {days[k]: v for k, v in daily_roas.items()}
        
        best_day = max(daily_roas_named.items(), key=lambda x: x[1])
        
        confidence = 0.45
        if statistical_significance:
            confidence += 0.25
        
        if abs(weekend_roas - weekday_roas) / max(weekday_roas, 0.01) > 0.1:
            confidence += 0.15
        
        confidence = min(confidence, 0.95)
        
        return {
            'confidence': confidence,
            'method': 'Weekend vs Weekday T-test comparison',
            'evidence': {
                'weekend_avg_roas': float(weekend_roas),
                'weekday_avg_roas': float(weekday_roas),
                'weekend_avg_ctr': float(weekend_ctr),
                'weekday_avg_ctr': float(weekday_ctr),
                'daily_roas': daily_roas_named
            },
            'statistical_tests': {
                't_statistic': float(t_stat) if not np.isnan(t_stat) else 0,
                'p_value': float(p_value) if not np.isnan(p_value) else 1,
                'significant': statistical_significance
            },
            'conclusion': f"Weekend ROAS: {weekend_roas:.2f} vs Weekday ROAS: {weekday_roas:.2f}. "
                         f"Best day: {best_day[0]} (ROAS: {best_day[1]:.2f})",
            'recommendation': f"Consider adjusting bid strategies for {best_day[0]}"
        }
    
    def _validate_performance_hypothesis(self, hypothesis: str) -> Dict[str, Any]:
        """validate hypotheses about overall performance drivers"""
        # correlation analysis
        correlations = self.loader.get_correlation_matrix()
        
        # key correlations with roas
        roas_correlations = correlations.get('roas', {})
        
        # spend efficiency analysis
        df = self.df
        spend_quartiles = df.groupby(pd.qcut(df['spend'], 4, labels=['Low', 'Medium-Low', 'Medium-High', 'High']))['roas'].mean()
        
        # ctr impact on conversions
        ctr_correlation = roas_correlations.get('ctr', 0)
        spend_correlation = roas_correlations.get('spend', 0)
        
        # find high performers
        high_roas = df[df['roas'] > df['roas'].quantile(0.75)]
        high_roas_characteristics = {
            'avg_spend': float(high_roas['spend'].mean()),
            'avg_ctr': float(high_roas['ctr'].mean()),
            'top_creative': high_roas['creative_type'].mode().iloc[0] if len(high_roas) > 0 else 'N/A',
            'top_audience': high_roas['audience_type'].mode().iloc[0] if len(high_roas) > 0 else 'N/A'
        }
        
        confidence = 0.55
        
        # higher confidence if correlations are strong
        if abs(ctr_correlation) > 0.3:
            confidence += 0.15
        if abs(spend_correlation) > 0.2:
            confidence += 0.1
        
        confidence = min(confidence, 0.95)
        
        return {
            'confidence': confidence,
            'method': 'Correlation and quartile analysis',
            'evidence': {
                'roas_correlations': {k: float(v) for k, v in roas_correlations.items()},
                'high_performer_profile': high_roas_characteristics,
                'spend_quartile_roas': spend_quartiles.to_dict() if hasattr(spend_quartiles, 'to_dict') else {}
            },
            'statistical_tests': {
                'ctr_roas_correlation': float(ctr_correlation),
                'spend_roas_correlation': float(spend_correlation)
            },
            'conclusion': f"High performers typically use {high_roas_characteristics['top_creative']} creative "
                         f"with {high_roas_characteristics['top_audience']} audience",
            'recommendation': "Focus on the profile of high-performing ads"
        }
    
    def _validate_general_hypothesis(self, hypothesis: str) -> Dict[str, Any]:
        """fallback validation for general hypotheses"""
        # use llm to help interpret and validate
        summary = self.loader.get_summary_stats()
        
        prompt = f"""{self.prompt_template}

## Hypothesis to Evaluate
{hypothesis}

## Data Summary
- Total Spend: ${summary['overall_metrics']['total_spend']:.2f}
- Total Revenue: ${summary['overall_metrics']['total_revenue']:.2f}
- Overall ROAS: {summary['overall_metrics']['overall_roas']:.2f}
- Average CTR: {summary['overall_metrics']['avg_ctr']:.4f}
- Creative Types: {', '.join(summary['breakdowns']['creative_types'])}
- Audience Types: {', '.join(summary['breakdowns']['audience_types'])}

Respond in JSON format."""
        
        try:
            result = self.llm.generate_json(prompt=prompt, temperature=0.3)
            
            return {
                'confidence': float(result.get('confidence', 0.5)),
                'method': 'LLM-assisted evaluation',
                'evidence': {
                    'reasoning': result.get('reasoning', ''),
                    'evidence_summary': result.get('evidence_summary', '')
                },
                'statistical_tests': {},
                'conclusion': result.get('evidence_summary', 'Evaluation completed'),
                'recommendation': result.get('recommendation', '')
            }
        except Exception:
            return {
                'confidence': 0.5,
                'method': 'Default evaluation',
                'evidence': {},
                'statistical_tests': {},
                'conclusion': 'Unable to fully validate - requires manual review',
                'recommendation': 'Review hypothesis manually with domain expertise'
            }
    
    def get_statistical_summary(self) -> Dict[str, Any]:
        """
        get comprehensive statistical summary of the dataset
        
        returns:
            dictionary with statistical measures
        """
        if self.df is None:
            self.df = self.loader.load_data()
        
        df = self.df
        
        return {
            'roas': {
                'mean': float(df['roas'].mean()),
                'median': float(df['roas'].median()),
                'std': float(df['roas'].std()),
                'min': float(df['roas'].min()),
                'max': float(df['roas'].max()),
                'q25': float(df['roas'].quantile(0.25)),
                'q75': float(df['roas'].quantile(0.75))
            },
            'ctr': {
                'mean': float(df['ctr'].mean()),
                'median': float(df['ctr'].median()),
                'std': float(df['ctr'].std()),
                'min': float(df['ctr'].min()),
                'max': float(df['ctr'].max())
            },
            'spend': {
                'mean': float(df['spend'].mean()),
                'median': float(df['spend'].median()),
                'total': float(df['spend'].sum())
            }
        }
