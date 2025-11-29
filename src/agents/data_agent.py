"""
data agent - loads dataset and provides summarized context
"""
from typing import Dict, Any
from pathlib import Path
import json


class DataAgent:
    """loads and summarizes facebook ads dataset"""
    
    def __init__(self, data_loader, config: Dict[str, Any]):
        self.loader = data_loader
        self.config = config
        self.data_context: Dict[str, Any] = {}
    
    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        load data and create comprehensive summary
        
        args:
            plan: execution plan from planner
            
        returns:
            data context dictionary with summaries
        """
        # load the dataset
        df = self.loader.load_data()
        
        # generate comprehensive summary
        summary = self.loader.get_summary_stats()
        
        # get time series for key metrics
        metrics = plan.get('analysis_scope', {}).get('metrics', ['roas', 'ctr'])
        time_series = {}
        for metric in metrics:
            if metric in ['roas', 'ctr', 'spend', 'purchases']:
                time_series[metric] = self.loader.get_time_series_metrics(metric)
        
        # get campaign-level performance
        campaign_performance = self.loader.get_campaign_performance()
        
        # get creative and audience breakdown
        creative_performance = self.loader.get_creative_performance()
        audience_performance = self.loader.get_audience_performance()
        
        # detect anomalies in roas
        anomalies = self.loader.detect_anomalies(metric='roas', threshold=1.5)
        
        # build context
        self.data_context = {
            "summary": summary,
            "time_series": time_series,
            "campaign_performance": campaign_performance,
            "creative_performance": creative_performance,
            "audience_performance": audience_performance,
            "anomalies": anomalies,
            "dataset_shape": {
                "rows": len(df),
                "columns": len(df.columns)
            }
        }
        
        return self.data_context
    
    def get_context_for_llm(self) -> str:
        """
        format data context as readable text for llm consumption
        avoids sending full csv - only summarized insights
        """
        context = f"""# Facebook Ads Dataset Summary

## Overall Performance
- Date Range: {self.data_context['summary']['date_range']['start']} to {self.data_context['summary']['date_range']['end']}
- Total Campaigns: {self.data_context['summary']['total_campaigns']}
- Total Spend: ${self.data_context['summary']['overall_metrics']['total_spend']:.2f}
- Total Revenue: ${self.data_context['summary']['overall_metrics']['total_revenue']:.2f}
- Overall ROAS: {self.data_context['summary']['overall_metrics']['overall_roas']:.2f}
- Average CTR: {self.data_context['summary']['overall_metrics']['avg_ctr']:.4f}

## Campaign Performance
"""
        for campaign, stats in self.data_context['campaign_performance'].items():
            context += f"\n### {campaign}\n"
            context += f"- Spend: ${stats['total_spend']:.2f}\n"
            context += f"- Revenue: ${stats['total_revenue']:.2f}\n"
            context += f"- ROAS: {stats['avg_roas']:.2f}\n"
            context += f"- CTR: {stats['avg_ctr']:.4f}\n"
            context += f"- Purchases: {stats['total_purchases']}\n"
            context += f"- Creative Types: {', '.join(stats['creative_types'])}\n"
            context += f"- Audience Types: {', '.join(stats['audience_types'])}\n"
        
        context += "\n## ROAS by Date\n"
        for date, roas in self.data_context['time_series']['roas'].items():
            context += f"- {date}: {roas:.2f}\n"
        
        context += "\n## Creative Type Performance\n"
        for creative_type, stats in self.data_context['creative_performance'].items():
            context += f"\n### {creative_type}\n"
            context += f"- Avg ROAS: {stats['avg_roas']:.2f}\n"
            context += f"- Avg CTR: {stats['avg_ctr']:.4f}\n"
            context += f"- Count: {stats['count']} ads\n"
        
        context += "\n## Audience Type Performance\n"
        for audience_type, stats in self.data_context['audience_performance'].items():
            context += f"\n### {audience_type}\n"
            context += f"- Avg ROAS: {stats['avg_roas']:.2f}\n"
            context += f"- Avg CTR: {stats['avg_ctr']:.4f}\n"
            context += f"- Count: {stats['count']} ads\n"
        
        if self.data_context['anomalies']['anomaly_count'] > 0:
            context += f"\n## Anomalies Detected\n"
            context += f"Found {self.data_context['anomalies']['anomaly_count']} anomalous ROAS values:\n"
            for anomaly in self.data_context['anomalies']['anomalies'][:5]:  # show first 5
                context += f"- {anomaly['date']}: {anomaly['campaign_name']} (ROAS: {anomaly['roas']:.2f})\n"
        
        return context