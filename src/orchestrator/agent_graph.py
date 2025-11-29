"""
agent orchestrator - coordinates multi-agent workflow
"""
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import json

from src.utils.llm_client import OllamaClient
from src.utils.data_loader import DataLoader
from src.agents.planner import PlannerAgent
from src.agents.data_agent import DataAgent
from src.agents.insight_agent import InsightAgent
from src.agents.evaluator import EvaluatorAgent
from src.agents.creative_generator import CreativeGeneratorAgent


class AgentOrchestrator:
    """orchestrates the multi-agent workflow"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # initialize llm client
        print("Initializing Ollama client...")
        self.llm = OllamaClient(config)
        
        # health check
        if not self.llm.health_check():
            raise Exception(f"Ollama health check failed. Ensure model {self.llm.model} is available.")
        print(f"Ollama connected ({self.llm.model})")
        
        # initialize data loader
        self.data_loader = DataLoader(config)
        
        # initialize agents
        self.planner = PlannerAgent(self.llm, config)
        self.data_agent = DataAgent(self.data_loader, config)
        self.insight_agent = InsightAgent(self.llm, config)
        self.evaluator = EvaluatorAgent(self.llm, self.data_loader, config)
        self.creative_generator = CreativeGeneratorAgent(self.llm, self.data_loader, config)
        
        # execution log
        self.execution_log = []
        
        # logs directory
        self.logs_dir = Path(config['output'].get('logs_dir', 'logs'))
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
    def run(self, user_query: str) -> Dict[str, Any]:
        """
        execute the full agent workflow
        
        args:
            user_query: natural language query from user
            
        returns:
            complete results including insights, creatives, and report
        """
        start_time = datetime.now()
        
        # step 1: planning
        print("\nStep 1: Planning")
        plan = self._execute_with_logging("planner", lambda: self.planner.plan(user_query))
        print(f"   Intent: {plan['intent']}")
        print(f"   Tasks: {len(plan['tasks'])}")
        
        # step 2: data loading
        print("\nStep 2: Loading Data")
        data_context_raw = self._execute_with_logging("data_agent", lambda: self.data_agent.execute(plan))
        data_context_text = self.data_agent.get_context_for_llm()
        print(f"   Loaded: {data_context_raw['dataset_shape']['rows']} rows")
        print(f"   Campaigns: {data_context_raw['summary']['total_campaigns']}")
        
        # step 3: insight generation
        print("\nStep 3: Generating Insights")
        insights = self._execute_with_logging(
            "insight_agent", 
            lambda: self.insight_agent.generate(data_context_text, plan, user_query)
        )
        print(f"   Hypotheses: {len(insights['hypotheses'])}")
        
        # step 4: validation
        print("\nStep 4: Validating Hypotheses")
        validation_results = self._execute_with_logging(
            "evaluator",
            lambda: self.evaluator.validate(insights['hypotheses'])
        )
        print(f"   {validation_results['validation_summary']}")
        
        # step 5: creative generation (if needed)
        creatives = None
        if plan.get('requires_creative_generation', False):
            print("\nStep 5: Generating Creative Recommendations")
            creatives = self._execute_with_logging(
                "creative_generator",
                lambda: self.creative_generator.generate(plan)
            )
            if creatives['recommendations']:
                print(f"   Generated: {len(creatives['recommendations'])} recommendations")
        
        # step 6: generate report
        print("\nStep 6: Generating Report")
        report = self._generate_report(
            user_query,
            plan,
            data_context_raw,
            insights,
            validation_results,
            creatives
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\nTotal execution time: {duration:.2f}s")
        
        results = {
            "query": user_query,
            "plan": plan,
            "insights": {
                "hypotheses": insights['hypotheses'],
                "validated": validation_results['validated_hypotheses'],
                "summary": insights.get('analysis_summary', ''),
                "key_observations": insights.get('key_observations', [])
            },
            "creatives": creatives,
            "report": report,
            "logs": self.execution_log,
            "metadata": {
                "execution_time_seconds": duration,
                "timestamp": start_time.isoformat()
            }
        }
        
        # save execution summary log
        log_path = self._save_execution_summary(results)
        if log_path:
            print(f"Logs saved to {self.logs_dir}/")
        
        return results
    
    def _execute_with_logging(self, agent_name: str, func) -> Any:
        """execute agent function and log the execution"""
        start_time = datetime.now()
        
        try:
            result = func()
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
            print(f"   Error: {error}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        log_entry = {
            "agent": agent_name,
            "timestamp": start_time.isoformat(),
            "duration_seconds": duration,
            "success": success,
            "error": error,
            "result": result
        }
        
        self.execution_log.append(log_entry)
        
        # save individual agent log to json file
        self._save_agent_log(agent_name, log_entry)
        
        if not success:
            raise Exception(f"{agent_name} failed: {error}")
        
        return result
    
    def _save_agent_log(self, agent_name: str, log_entry: Dict[str, Any]) -> None:
        """save individual agent execution log to json file"""
        timestamp = log_entry['timestamp'].replace(':', '-')
        log_filename = f"{agent_name}_{timestamp}.json"
        log_path = self.logs_dir / log_filename
        
        try:
            with open(log_path, 'w') as f:
                json.dump(log_entry, f, indent=2, default=str)
        except Exception as e:
            print(f"   Warning: Failed to save log for {agent_name}: {e}")
    
    def _save_execution_summary(self, results: Dict[str, Any]) -> str:
        """save complete execution summary log"""
        timestamp = results['metadata']['timestamp'].replace(':', '-')
        summary_filename = f"execution_summary_{timestamp}.json"
        summary_path = self.logs_dir / summary_filename
        
        summary = {
            "query": results['query'],
            "timestamp": results['metadata']['timestamp'],
            "execution_time_seconds": results['metadata']['execution_time_seconds'],
            "agents_executed": [log['agent'] for log in self.execution_log],
            "execution_log": self.execution_log,
            "plan": results['plan'],
            "insights_count": len(results['insights'].get('hypotheses', [])),
            "validated_count": len(results['insights'].get('validated', [])),
            "creatives_generated": len(results['creatives'].get('recommendations', [])) if results['creatives'] else 0
        }
        
        try:
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            return str(summary_path)
        except Exception as e:
            print(f"   Warning: Failed to save execution summary: {e}")
            return None
        
        return result
    
    def _generate_report(
        self,
        user_query: str,
        plan: Dict[str, Any],
        data_context: Dict[str, Any],
        insights: Dict[str, Any],
        validation: Dict[str, Any],
        creatives: Dict[str, Any] = None
    ) -> str:
        """generate markdown report for marketers"""
        
        report = f"""# Facebook Ads Performance Analysis Report

## Query
{user_query}

## Executive Summary
**Analysis Period:** {data_context['summary']['date_range']['start']} to {data_context['summary']['date_range']['end']}  
**Total Spend:** ${data_context['summary']['overall_metrics']['total_spend']:.2f}  
**Total Revenue:** ${data_context['summary']['overall_metrics']['total_revenue']:.2f}  
**Overall ROAS:** {data_context['summary']['overall_metrics']['overall_roas']:.2f}  
**Average CTR:** {data_context['summary']['overall_metrics']['avg_ctr']:.4f}

---

## Key Findings

"""
        
        # add validated hypotheses
        high_conf_hypotheses = [h for h in validation['validated_hypotheses'] if h['confidence'] >= 0.7]
        
        if high_conf_hypotheses:
            report += "### High Confidence Insights\n\n"
            for i, hyp in enumerate(high_conf_hypotheses, 1):
                report += f"{i}. **{hyp['original_hypothesis']}**\n"
                report += f"   - Confidence: {hyp['confidence']:.0%}\n"
                report += f"   - Validation Method: {hyp['validation_method']}\n"
                
                # add key evidence
                if 'quantitative_evidence' in hyp and hyp['quantitative_evidence']:
                    report += f"   - Evidence: {self._format_evidence(hyp['quantitative_evidence'])}\n"
                report += "\n"
        
        # add medium confidence insights
        medium_conf = [h for h in validation['validated_hypotheses'] 
                       if 0.5 <= h['confidence'] < 0.7]
        
        if medium_conf:
            report += "### Medium Confidence Insights\n\n"
            for i, hyp in enumerate(medium_conf, 1):
                report += f"{i}. {hyp['original_hypothesis']} (Confidence: {hyp['confidence']:.0%})\n"
        
        report += "\n---\n\n"
        
        # campaign performance
        report += "## Campaign Performance Breakdown\n\n"
        for campaign, stats in data_context['campaign_performance'].items():
            report += f"### {campaign}\n"
            report += f"- **ROAS:** {stats['avg_roas']:.2f}\n"
            report += f"- **CTR:** {stats['avg_ctr']:.4f}\n"
            report += f"- **Spend:** ${stats['total_spend']:.2f}\n"
            report += f"- **Revenue:** ${stats['total_revenue']:.2f}\n"
            report += f"- **Purchases:** {stats['total_purchases']}\n\n"
        
        # creative recommendations
        if creatives and creatives.get('recommendations'):
            report += "\n---\n\n## Creative Recommendations\n\n"
            report += f"Identified {len(creatives['recommendations'])} opportunities for creative optimization.\n\n"
            
            for i, rec in enumerate(creatives['recommendations'], 1):
                report += f"### Opportunity {i}: {rec.get('campaign_name', 'Unknown Campaign')}\n"
                report += f"**Current CTR:** {rec['current_ctr']:.4f}\n\n"
                report += f"**Current Message:** {rec['original_message']}\n\n"
                report += "**Recommended New Creatives:**\n\n"
                
                for j, creative in enumerate(rec.get('new_creatives', []), 1):
                    report += f"{j}. **{creative.get('headline', 'N/A')}**\n"
                    report += f"   - Body: {creative.get('body', 'N/A')}\n"
                    report += f"   - CTA: {creative.get('cta', 'N/A')}\n"
                    report += f"   - Reasoning: {creative.get('reasoning', 'N/A')}\n\n"
        
        report += "\n---\n\n## Recommendations\n\n"
        report += "Based on the analysis, consider:\n\n"
        
        if high_conf_hypotheses:
            for hyp in high_conf_hypotheses[:3]:
                report += f"- Investigate: {hyp['original_hypothesis']}\n"
        
        if creatives and creatives.get('recommendations'):
            report += f"- Test new creative variations for low-CTR campaigns\n"
            report += f"- Focus on messaging patterns from high-performing ads\n"
        
        report += "\n---\n\n"
        report += f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return report
    
    def _format_evidence(self, evidence: Dict[str, Any]) -> str:
        """format evidence dictionary into readable text"""
        if not evidence:
            return "N/A"
        
        # handle different evidence structures
        if isinstance(evidence, dict):
            # for creative/audience comparisons
            if all(isinstance(v, dict) for v in evidence.values()):
                parts = []
                for key, stats in list(evidence.items())[:3]:  # show top 3
                    if 'avg_roas' in stats:
                        parts.append(f"{key}: ROAS {stats['avg_roas']:.2f}")
                return ", ".join(parts)
            # for generic stats
            elif 'overall_roas' in evidence:
                return f"ROAS range {evidence.get('roas_min', 0):.2f}-{evidence.get('roas_max', 0):.2f}"
        
        return "See detailed logs"